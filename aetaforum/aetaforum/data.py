from enum import StrEnum

import requests

class _EXCHANGE(StrEnum):
    Binance = "binance"
    Bybit = "bybit"
    GateIo = "gateio"
    OKX = "okex"

def check_symbol_exists(symbol: str) -> bool:
    """바이낸스 선물 시장에 해당 심볼이 존재하는지 확인합니다."""
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 'symbols' 리스트 안에서 'symbol' 이름만 쫙 뽑아냅니다
        valid_symbols = [item["symbol"] for item in data.get("symbols", [])]

        return symbol in valid_symbols
    except Exception as e:
        return True


