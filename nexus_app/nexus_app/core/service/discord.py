"""
Discord Logging & Monitoring Module

디스코드 웹훅을 이용한 비동기 로깅 및 서버 상태 모니터링 시스템입니다.
메인 시스템의 성능 저하(OOM, I/O 블로킹)를 막기 위해 버킷 스왑 패턴과 독립된 스레드를 사용합니다.

[Architecture]
1. Main Thread:
   - `send_log()`를 통해 버퍼(_log_buffer, _test_buffer)에 로그 적재
2. Background Threads:
   - _log_loop: 3.5초 주기로 일반 로그 전송
   - _test_loop: 3.5초 주기로 테스트 로그 전송
   - _status_loop: 3.7초 주기로 서버 상태(Status) 메시지 갱신

[Policy]
- OOM 방지: 전송 1회 실패 시 5초 후 재시도, 2차 실패 시 해당 로그는 메모리 확보를 위해 영구 폐기.
"""
import atexit
import threading
import time
from collections import defaultdict
from enum import StrEnum, IntEnum
from typing import Callable

import requests

from ._singleton import Singleton
from .db import CryptoDB
from .log import SystemLogger, Log, LogLevel
from .time import NtpTimer

__all__ = ["DMode", "DChannel","Discord"]

_COLOR = 0x27272f
_LOG_ICON: dict[LogLevel, str] = {
    LogLevel.PRINT: ":interrobang:",
    LogLevel.FATAL: ":boom:",
    LogLevel.ERROR: ":rotating_light:",
    LogLevel.FAIL: ":x:",
    LogLevel.WARN: ":warning:",
    LogLevel.INFO: ":information_source:",
    LogLevel.PASS: ":white_check_mark:",
    LogLevel.DEBUG: ":beetle:",
}

def _build_discord_payload(data: dict[str, list[Log]]) -> dict:
    embeds = []
    sender_n = len(data.keys())
    content = None if sender_n <= 10 else f"로그 전송자가 너무 많습니다 ({sender_n}/10)" # embed 10 초과시 서버 안받음
    color = _COLOR if content is None else 0xd75555
    for sender, logs in list(data.items())[:10]:
        total_logs = len(logs)

        if total_logs > 25: # field 25 초과시 서버 안받음
            description = f"## {sender}\n> 로그 갯수 초과 `{total_logs}/25`"
        else:
            description = f"## {sender}\n`{total_logs}/25`"

        embed = {
            "color": color,
            "description": description,
            "fields": []
        }

        for log in logs[:25]:
            icon = _LOG_ICON.get(log.level, "")
            level_name = str(log.level)
            safe_msg = log.msg.replace("_", "\\_").replace("*", "\\*") # 마크다운 문법 떄문에 형식 깨지는거 방지
            if len(safe_msg) > 1000: safe_msg = safe_msg[:995] + "..." # value 1024 초과시 서버 안받음

            field = {
                "name": f"{icon}  {level_name} `[{log.time}]`",
                "value": safe_msg,
                "inline": False
            }
            embed["fields"].append(field)

        embeds.append(embed)

    return {"content": content, "embeds": embeds}

"""
_STATUS_ICON: dict[AgentStatus, str] = {
    AgentStatus.SLEEPING: "☐",
    AgentStatus.RUNNING: "☑︎",
    AgentStatus.STOPPING: "☑︎",
    AgentStatus.STOPPED: "☒"
}"""

# ==================================================================================================================
# public class

class DMode(IntEnum):
    """
    Attributes:
        NONE: 모든 채널 미전송.
        STATUS: 상태 모니터링만 작동.
        LOG: 로그만 전송.
        ALL: 모두 전송.
    """
    NONE  = 0
    STATUS = 1
    LOG = 2
    ALL = 3


class DChannel(StrEnum):
    """
    Attributes:
        STATUS: 상태 모니터링용 채널.
        LOG: Log 전송용 채널
        TEST: Log 전송 테스트용 채널.
    """
    STATUS = "stat"
    LOG = "log"
    TEST = "test"


class Discord(metaclass=Singleton):
    """디스코드로 로그 전송 및 서버 상태 모니터링을 관리하는 싱글톤 클래스

    Attributes:
        is_connect (bool): 디스코드 웹훅 서버와의 정상 연결 및 통신 가능 여부
        mode (DMode): 현재 설정된 디스코드 알림 전송 모드 (NONE, STATUS, LOG, ALL)
    """


    def __init__(self):
        self.is_connect: bool = False
        self.mode: DMode = DMode.NONE

        # public var
        # ========================================================================
        # private var

        self._sys_logger = SystemLogger()
        self._ntp_timer = NtpTimer()
        self._lock = threading.Lock()

        self._db = CryptoDB("Discord")
        self.mode        = self._db.create("mode", DMode.NONE, exist_ok=True)
        self._status_url = self._db.create(DChannel.STATUS, "", encrypt=True, exist_ok=True)
        self._log_url    = self._db.create(DChannel.LOG, "", encrypt=True, exist_ok=True)
        self._test_url   = self._db.create(DChannel.TEST, "", encrypt=True, exist_ok=True)

        self._is_dead = False
        self._status_tick = False
        self._status_msg_id: str | None = None
        self._status_md_fn: Callable[[], str]|None = None

        self._log_buffer: defaultdict[str, list[Log]]  = defaultdict(list)
        self._test_buffer: defaultdict[str, list[Log]] = defaultdict(list)

        threading.Thread(target=self._status_loop, daemon=True).start()
        threading.Thread(target=self._log_loop, daemon=True).start()
        threading.Thread(target=self._test_loop, daemon=True).start()

        atexit.register(self.kill)

    def kill(self):
        """모든 백그라운드 스레드의 실행을 중지하고 디스코드 상태 메시지를 삭제합니다"""
        self._is_dead = True
        self._www_remove_status()

    def send_log(self, sender: str, log: Log, is_test: bool = False):
        """발생한 로그를 내부 버퍼에 적재합니다.

        (실제 웹훅 전송은 백그라운드 루프가 주기적으로 처리)

        Args:
            sender (str): 로그를 발생시킨 주체 또는 모듈의 이름.
            log (Log): 전송할 로그 데이터 객체.
            is_test (bool): True일 경우 실 서비스 채널이 아닌 테스트 채널 버퍼에 적재합니다. 기본값은 False.
        """
        with self._lock:
            if is_test:
                self._test_buffer[sender].append(log)
            else:
                self._log_buffer[sender].append(log)

    def set_status_md(self, return_markdown_function: Callable[[], str]):
        """서버 상태 모니터링 메시지를 생성할 콜백 함수를 등록합니다.

        상태 루프(_status_loop)가 디스코드에 메시지를 업데이트할 때마다 이 함수를 호출하여 최신 마크다운 텍스트를 받아옵니다.

        Args:
            return_markdown_function (Callable[[], str]): 호출 시 디스코드 마크다운 형식의 문자열을 반환하는 콜백 함수.

        Raises:
            TypeError: 인자로 전달된 값이 호출 가능한(Callable) 함수가 아닐 경우 발생합니다.
        """
        if not callable(return_markdown_function):
            raise TypeError("return_markdown_function은 호출 가능한(Callable) 메서드여야 합니다.")
        with self._lock:
            self._status_md_fn = return_markdown_function

    def get_url(self, channel: DChannel) -> str:
        """특정 대상 디스코드 웹훅 채널의 URL을 반환합니다.

                Args:
                    channel (DChannel): URL을 반환할 대상 채널 상수 (STATUS, LOG, TEST 중 하나).

                Raises:
                    ValueError: 유효하지 않은 DChannel 타입이 입력되었을 경우 발생합니다.

                Returns:
                    str: 해당 채널 url 문자열.
                """
        with self._lock:
            match channel:
                case DChannel.STATUS:
                    return self._status_url

                case DChannel.LOG:
                    return self._log_url

                case DChannel.TEST:
                    return self._test_url

                case _:
                    raise ValueError(f"'{channel}'은(는) 올바른 디스코드 채널이 아닙니다.")

    def update_url(self, channel: DChannel, url: str) -> None:
        """특정 대상 디스코드 웹훅 채널의 URL을 갱신하고 로컬 DB에 암호화하여 저장합니다.

        Args:
            channel (DChannel): URL을 변경할 대상 채널 상수 (STATUS, LOG, TEST 중 하나).
            url (str): 새로 설정할 디스코드 웹훅 URL 문자열.

        Raises:
            ValueError: 유효하지 않은 DChannel 타입이 입력되었을 경우 발생합니다.
        """
        if isinstance(channel, DChannel):
            with self._lock:
                match channel:
                    case DChannel.STATUS:
                        self._status_url = url

                    case DChannel.LOG:
                        self._log_url = url

                    case DChannel.TEST:
                        self._test_url = url

                    case _:
                        raise ValueError(f"'{channel}'은(는) 올바른 디스코드 채널이 아닙니다.")

            self._db.update(channel, url)
            self._sys_logger.emit(LogLevel.PASS, f"디스코드 '{channel.name}'채널이 변경되었습니다.", is_alert=True)

        else:
            raise ValueError(f"'{channel}'은(는) 올바른 디스코드 채널이 아닙니다.")


    def change_mode(self, mode: DMode) -> None:
        """전체 디스코드 전송 모드를 변경하고 로컬 DB에 상태를 저장합니다.

        Args:
            mode (DMode): 변경할 동작 모드 (OFF, STATUS, LOG, ON 중 하나).

        Raises:
            ValueError: 유효하지 않은 DMode 타입이 입력되었을 경우 발생합니다.
        """
        if isinstance(mode, DMode):
            with self._lock:
                self.mode = mode
            self._db.update("mode", mode)
            self._sys_logger.emit(LogLevel.PASS, f"디스코드 모드가 '{mode.name}'로 변경되었습니다.", is_alert=True)
        else:
            raise ValueError(f"'{mode}'은(는) 올바른 디스코드 모드가 아닙니다.")

    # public
    #--------------------------------------------------------------------------------------------
    # private
    # ~loop 메소드는 쓰레드용, _www_~ 는 서버 요청용

    def _log_loop(self):
        while True:
            try:
                time.sleep(3.5)
                self._www_send_log()

            except Exception as e:
                with self._lock:
                    self.is_connect = False
                self._sys_logger.emit(LogLevel.ERROR, f"디스코드 로그 전송 중 에러 발생 (10초간 일시정지) - {e}")
                time.sleep(10)

    def _test_loop(self):
        while True:
            try:
                time.sleep(3.5)
                self._www_send_log(is_test=True)

            except Exception as e:
                with self._lock:
                    self.is_connect = False
                self._sys_logger.emit(LogLevel.WARN, f"디스코드 test 로그 전송 중 에러 발생 (10초간 일시정지) - {e}")
                time.sleep(10)

    def _status_loop(self):
        fail_n = 0
        old_status_url = self._status_url
        while True:
            try:
                time.sleep(3.7)
                if self._is_dead:
                    break

                if self.mode in (DMode.LOG, DMode.NONE):
                    if self._status_msg_id is not None:
                        self._www_remove_status()
                    continue

                if old_status_url is not self._status_url:
                    self._www_remove_status(old_status_url)
                    old_status_url = self._status_url

                self._www_update_status()
                fail_n = 0

            except Exception as e:
                fail_n += 1
                with self._lock:
                    self.is_connect = False

                if fail_n >= 3:
                    if fail_n < 10:
                        self._sys_logger.emit(LogLevel.WARN, f"디스코드 서버 상태 모니터링 요청 실패 ({fail_n}번째 요청 실패, 30초간 일시정지) - {e}")
                        time.sleep(30)

                    else:
                        old_mode = self.mode
                        new_mode = DMode.NONE if self.mode in (DMode.STATUS, DMode.NONE) else DMode.LOG
                        self.change_mode(new_mode)
                        self._sys_logger.emit(LogLevel.ERROR, f"디스코드 서버 상태 모니터링 10번째 요청 실패, 모드 변경( {old_mode} → {new_mode} )")

    #--------------------------------------------------------------------------------------------

    def _www_send_log(self, is_test: bool = False):
        if self.mode in (DMode.NONE, DMode.STATUS):
            return

        with self._lock:
            if is_test:
                if not self._test_buffer: return
                pending_logs = self._test_buffer
                self._test_buffer = defaultdict(list)
            else:
                if not self._log_buffer: return
                pending_logs = self._log_buffer
                self._log_buffer = defaultdict(list)

        data = _build_discord_payload(pending_logs)
        target_url = self._test_url if is_test else self._log_url

        try:
            res = requests.post(target_url, json=data, timeout=5)
            res.raise_for_status()  # 200번대 응답 아니면 에러 발생
            with self._lock:
                self.is_connect = True

        except Exception:
            with self._lock:
                self.is_connect = False
            self._sys_logger.emit(LogLevel.WARN, f"디스코드 로그 전송 실패 (5초 후 실패 로그 재전송 시도)")
            time.sleep(5)
            res = requests.post(target_url, json=data, timeout=5)
            res.raise_for_status()  # 200번대 응답 아니면 에러 발생
            with self._lock:
                self.is_connect = True


    def _www_update_status(self) -> None:
        if self._is_dead: return
        if self._status_md_fn is None:
            raise RuntimeError("서버 상태 모니터링 업데이트용 Markdown 생성 함수가 설정되지 않았습니다 - ( _status_md_fn = None )")

        color = _COLOR if self._status_tick else 0x55d755
        self._status_tick = not self._status_tick

        data = {
            "username": "서버 상태 모니터링",
            "embeds": [
                {
                    "color": color,
                    "title": f"🕓  {self._ntp_timer.now_str()}",
                    "description": f"{self._status_md_fn()}".replace("_", "\\_")
                }
            ]
        }

        if self._status_msg_id is None: # 최초 POST
            res = requests.post(self._status_url, json=data, params={"wait": "true"}, timeout=5)
            if res.status_code in (200, 204):
                with self._lock:
                    self.is_connect = True
                    self._status_msg_id = res.json()["id"]

            else:
                with self._lock:
                    self.is_connect = False
                raise ConnectionError(f"디스코드 서버 상태 모니터링 생성 중 문제 발생 ({res.status_code}-{res.text})")

        else: # 기존 메시지 PATCH
            res = requests.patch(f"{self._status_url}/messages/{self._status_msg_id}", json=data, timeout=5)
            if res.status_code in (200, 204):
                with self._lock:
                    self.is_connect = True

            elif res.status_code == 404: # 임의로 지웠을 때 자동 대처
                with self._lock:
                    self._status_msg_id = None
                self._sys_logger.emit(LogLevel.WARN, "디스코드 서버 상태 모니터링 삭제 감지 - 재생성 시도 및 진행 (404)")

            else:
                self.is_connect = False
                raise ConnectionError(f"디스코드 서버 상태 모니터링 수정 중 문제 발생 ({res.status_code}-{res.text})")


    def _www_remove_status(self, status_url: str = None) -> None:
        if self._status_msg_id:
            if status_url is None:
                status_url = self._status_url
            requests.delete(f"{status_url}/messages/{self._status_msg_id}")
            with self._lock:
                self._status_msg_id = None