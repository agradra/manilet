import atexit
import json
import math
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, ROUND_DOWN

import websocket
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

from nexuspy import alert
from common._const import HYPERLIQUID_API_SECRET_KEY, HYPERLIQUID_API_ADDRESS_KEY, RABBY_WALLET_ADDRESS_KEY

_ORDER_TRY = 5  # 주문 시도 횟수
_WS_URL = "wss://api.hyperliquid.xyz/ws"
_SLIPPAGE = 0.01

def _ut_price(price: float, round_mode: str = None) -> float:
    """
    실수형 가격 숫자를 하이퍼리퀴드 api규칙에 맞게 소수점 단위 수정

    :param price: 변환할 가격($)
    :param round_mode: '^' (올림), 'v' (버림), None (반올림 - 기본값)
    :return: 소수점 수정 완료된 가격($)
    """
    if price == 0:
        return 0

    if round_mode == "^":
        rm = ROUND_CEILING  # 올림
    elif round_mode == "v":
        rm = ROUND_FLOOR  # 버림
    else:
        rm = ROUND_HALF_UP  # 반올림

    decimal_n = min(6, max(0, 4 - math.floor(math.log10(abs(price)))))

    if decimal_n == 0:
        quantize_exp = Decimal('1')
    else:
        quantize_exp = Decimal('10') ** -decimal_n

    return float(Decimal(str(price)).quantize(quantize_exp, rounding=rm).normalize())


def _ut_size(size: float, decimal_n: int) -> float:
    """
        코인 크기값을 하이퍼리퀴드 api규칙에 맞게 소수점 단위 수정

        :param size: 코인 크기값
        :param decimal_n: 해당 코인의 사이즈 소수점 단위 meta
        :return: 소수점 수정 완료된 코인 크기값
        """
    dec_size = Decimal(str(size))
    quantize_format = Decimal('10') ** -decimal_n
    result = dec_size.quantize(quantize_format, rounding=ROUND_DOWN)

    return float(result)

class HyperLiquid:

    def __init__(self, coin_name: str, leverage: int, balance: float):
        """
        :param coin_name: 코인 이름 (ex. "BTC", "ETH")
        :param leverage: 초기 레버러지 설정값
        :param balance: 할당 자본금 (주문 비율 계산에 사용)

        """
        self._coin_name = coin_name.upper().strip()
        self._leverage = leverage
        self._balance = balance

        self._is_pending = False
        self._is_position = False
        self._position = None

        self._alo_long_entry_price = None
        self._alo_short_entry_price = None

        self._max_lev = 0
        self._size_decimals = 0


        # 지갑 설정 & 초기화
        self._account = Account.from_key(HYPERLIQUID_API_SECRET_KEY)
        self._address = self._account.address
        self._exchange = Exchange(self._account, constants.MAINNET_API_URL)
        self._info = Info(constants.MAINNET_API_URL, skip_ws=True)
        if self._address.lower() != HYPERLIQUID_API_ADDRESS_KEY.lower():
            raise ValueError(f"HyperLiquid 초기화 실패 - .env의 api 주소 키가 api 비밀 키와 연결된 주소와 일치하지 않음 ( api: {self._address.lower()} / .env: {HYPERLIQUID_API_ADDRESS_KEY.lower()} )")


        # 코인 메타데이터 설정
        for meta in self._info.post("/info", {"type": "meta"})["universe"]:
            if coin_name == meta["name"]:
                self._max_lev = int(meta["maxLeverage"])
                self._size_decimals = int(meta['szDecimals'])
                break


        # 포지션, 주문 이미 잡힘 여부 확인
        for position in self._info.user_state(RABBY_WALLET_ADDRESS_KEY)['assetPositions']:
            if position['position']['coin'] == self._coin_name:
                raise RuntimeError(f"HyperLiquid 초기화 실패 - 이미 '{self._coin_name}' 포지션이 잡혀있습니다.")

        for order in self._info.open_orders(RABBY_WALLET_ADDRESS_KEY):
            if order['coin'] == self._coin_name:
                raise RuntimeError(f"HyperLiquid 초기화 실패 - 이미 '{self._coin_name}' 주문이 들어가있습니다.")

        # 지갑 유효성 검증
        usdc_info = self._info.spot_user_state(RABBY_WALLET_ADDRESS_KEY)['balances'][0]
        if self._balance >= float(usdc_info["total"] - usdc_info["hold"]):
            raise ValueError(
                f"HyperLiquid 초기화 실패 - 할당된 자금이 사용 가능 자금보다 더 많습니다. ( {self._balance} > {float(usdc_info["total"] - usdc_info["hold"])} )")


        # 레버리지 & Isolated 모드 설정
        try:
            res = self._exchange.update_leverage(self._leverage, self._coin_name, is_cross=False)
        except Exception as e:
            raise ValueError(f"HyperLiquid 초기화 실패 - api 호출 에러 ( lev: {leverage} / coin: {coin_name} / e: {e} )")
        if not res:
            raise ConnectionError(f"HyperLiquid 초기화 실패 - response 응답 없음 ( lev: {leverage} / coin: {coin_name} )")
        if res.get('status') != 'ok':
            raise ValueError(f"HyperLiquid 초기화 실패 - 비정상 상태값 ( lev: {leverage} / coin: {coin_name} / res: {res} )")


        # 웹소켓 관리
        self._wm = WsMaster(_WS_URL, self._wm_callback)
        self._wm.subscribe({"type": "bbo", "coin": coin_name})
        #self._wm.subscribe({"type": "orderUpdates", "user": RABBY_WALLET_ADDRESS_KEY})
        self._wm.subscribe({"type": "userEvents", "user": RABBY_WALLET_ADDRESS_KEY })

        # 안전 종료
        self._executor = ThreadPoolExecutor(max_workers=1)
        atexit.register(self._finish)
        alert.debug(f"HyperLiquid 초기화 완료 - {self._coin_name} {self._leverage}x - ${self._balance} ( 프로토타입 / 비동기 / 지정가 매매 (꼬리물기) )")

    # init
    # =======================================================================================================================
    # method

    def open_long(self, ratio: float) -> None:
        if ratio > 1.0 or ratio < 0.0:
            alert.warn(f"HyperLiquid 롱 진입 중 투자비율 설정 문제 발생 - 무효 처리 ( ratio: {ratio} )")
            return

        self._tracking_exchange

        def open_long_core():
            pass

        self._executor.submit(open_long_core)
        future = self._executor.submit(open_long_core)
        future.add_done_callback()



    def open_short(self, ratio: float) -> None:
        if ratio > 1.0 or ratio < 0.0:
            alert.warn(f"HyperLiquid 숏 진입 중 투자비율 설정 문제 발생 - 무효 처리 ( ratio: {ratio} )")
            return

        def open_short_core():
            self._exchange.order(
                name=self._coin_name,
                is_buy=False,
                sz=_ut_size(sz, self._size_decimals),
                limit_px=_ut_price(limit_px, "v"),
                order_type={"limit": {"tif": "Alo"}},
                reduce_only=False
            )

        self._executor.submit(open_short_core)
        future = self._executor.submit(open_short_core)
        future.add_done_callback()


    def close(self) -> None:

        self._exchange.order(
            name="ETH",
            is_buy=True,
            sz=_ut_size(sz, self._size_decimals),
            limit_px=_ut_price(limit_px, "v"),
            order_type={"limit": {"tif": "Alo"}},
            reduce_only=True
        )


    def set_sl(self, price: float, ratio: float = 1.0):
        return
        future = self._executor.submit(self._fast_order, coin, price, size)
        future.add_done_callback(self._on_order_done)

    def set_tp(self, price: float, ratio: float = 1.0):
        self._exchange.order(
            name="ETH",
            is_buy=True,
            sz=0.03,
            limit_px=1243.2,
            order_type={"limit": {"tif": "Alo"}},
            reduce_only=True
        )


    # public
    #=======================================================================================================================
    # private

    def _set_position(self, direction: str, size: float, entry_price: float, margin: float):
        self.is_position = True
        self._position = {
            "direction": direction,  # ex) "LONG", "SHORT"
            "size": size,  # float 해당 코인 크기
            "entry_price": entry_price,  # float 진입가
            "margin": margin  # float 묶인 달러 자본
        }

    def _clear_position(self):
        self.is_position = False


    def _ratio_to_size(self, is_buy: bool, ratio: float) -> float:
        margin = self._balance * 0.95 * ratio
        now_price = self._alo_long_entry_price if is_buy else self._alo_short_entry_price
        size = margin / now_price
        return size

    def _tracking_exchange(self, is_buy: bool, ratio: float):
        oid = None
        try:
            for i in range(_ORDER_TRY):
                result = self._exchange.order(
                    name=self._coin_name,
                    is_buy=is_buy,
                    sz=_ut_size(self._ratio_to_size(is_buy, ratio), self._size_decimals),
                    limit_px=_ut_price(self._alo_long_entry_price if is_buy else self._alo_short_entry_price),
                    order_type={"limit": {"tif": "Alo"}},
                    reduce_only=False
                )
                oid = result['response']['data']['statuses'][0].get('resting', {}).get('oid')
                if oid is not None:



        except Exception:
            err_msg = traceback.format_exc()
            return err_msg




    def _ex_order(self, is_buy: bool, sz: float, limit_px: float, order_type: dict, reduce_only: bool):
        return self._exchange.order(
            name=self._coin_name,
            is_buy=is_buy,
            sz=_ut_size(sz, self._size_decimals),
            limit_px=_ut_price(limit_px),
            order_type=order_type,
            reduce_only=reduce_only
        )


    def _wm_callback(self, ws_data):
        channel = ws_data.get("channel")
        if channel == "bbo":
            try:
                self._alo_long_entry_price = float(ws_data["data"]["bbo"][0]["px"])
                self._alo_short_entry_price = float(ws_data["data"]["bbo"][1]["px"])
            except Exception as e:
                alert.warn(f"HyperLiquid 'BBO' 파싱 에러 - {ws_data}")

        elif channel == "orderUpdates":
            pass

        elif channel == "user":
            data = ws_data["data"]
            if data is None:
                alert.warn(f"HyperLiquid 웹소켓 - user채널의 data값이 None임 ({ws_data})")
                return

            elif "fills" in data:
                for fill in data["fills"]:
                    if fill.get("coin") == self._coin_name:
                        print(f"✅ [{self._coin_name}] 체결 영수증 도착!", fill)

            elif "liquidation" in data:
                self.is_position = False
                self.position = []
                alert.info(f"포지션 강제 청산 - {data["liquidation"]}")

            elif "funding" in data:
                pass

    def _finish(self):
        self._wm.die()
        alert.debug("HyperLiquid 정상 종료 완료")




class WsMaster:

    def __init__(self, ws_url: str, callback_func):

        self._ws_app = websocket.WebSocketApp(
            ws_url,
            on_open = self._on_open, # (ws) 서버와 연결이 성공한 직후 실행
            on_message = self._on_message, # (ws, message) 서버에서 텍스트 데이터(JSON 등)가 날아올 때마다 실행
            on_error = self._on_error, # (ws, error) 통신 중 에러가 발생했을 때 실행
            on_close = self._on_close, # (ws, status_code, msg) 연결이 종료될 때 실행
            on_reconnect = self._on_reconnect, # (ws) 연결이 끊어졌다가 다시 붙었을 때 실행
        )

        self._callback_func = callback_func
        self._subscribe_list = []
        self._is_life = True
        self._is_connect = False
        self._last_recv_time = time.time()
        self._executor = ThreadPoolExecutor(max_workers=1)

        def _run_ws():
            self._ws_app.run_forever(
                reconnect=3
            )
        threading.Thread(target=_run_ws, daemon=True).start()

        init_n = 0
        while not self._is_connect:
            init_n += 1
            time.sleep(0.1)
            if init_n > 100:
                self.die()
                raise TimeoutError("웹소켓 서버 초기 연결 실패 (10초 초과)")

        def _th_watchdog():
            while self._is_life:
                time_minus = time.time() - self._last_recv_time
                if time_minus > 5:
                    if self._is_connect:
                        self._is_connect = False
                        if self._ws_app.sock:
                            self._ws_app.sock.close()
                        self._my_error(f"{time_minus:.2f} 초간 수신 없음")

                else:
                    self._is_connect = True
                time.sleep(1)

        def _th_ping():
            while self._is_life:
                try:
                    self._ws_app.send(json.dumps({"method": "ping"}))
                    #print("ping")
                except Exception as e:
                    pass
                time.sleep(3)

        threading.Thread(target=_th_watchdog, daemon=True).start()
        threading.Thread(target=_th_ping, daemon=True).start()

    def subscribe(self, subscription: dict):
        msg = {
            "method": "subscribe",
            "subscription": subscription
        }
        self._subscribe_list.append(msg)
        self._ws_app.send(json.dumps(msg))

    def die(self):
        self._is_life = False
        self._executor.shutdown(wait=False)  # 쓰레드 풀 종료
        self._ws_app.close()

    #===========================================================

    def _my_error(self, error):
        alert.error(f"웹소켓 에러 발생 - {error}")

    def _on_open(self, ws):
        self._is_connect = True

    def _on_reconnect(self, ws):
        self._last_recv_time = time.time()
        if not self._is_connect:
            self._is_connect = True
            alert.info(f"웹소켓 재연결 성공")
            for msg in self._subscribe_list:
                self._ws_app.send(json.dumps(msg))

    def _on_message(self, ws, msg):
        data = json.loads(msg)
        if data.get("channel") == "pong":
            self._last_recv_time = time.time()
            #print("pong")
        elif self._callback_func:
            future = self._executor.submit(self._callback_func, data)
            future.result()
        else:
            raise NotImplementedError("callback 함수가 등록되지 않음")

    def _on_error(self, ws, error):
        self._my_error(error)

    def _on_close(self, ws, close_status_code, close_msg):
        alert.debug(f"웹소켓 연결 종료 ({close_status_code} - {close_msg})")
