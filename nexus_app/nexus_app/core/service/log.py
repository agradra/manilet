import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from queue import Queue, Empty
from typing import Callable, Any

from ._singleton import Singleton
from .time import NtpTimer

__all__ = ["LogLevel", "Log", "SystemLogger"]



class LogLevel(IntEnum):
    PRINT = -5
    FATAL = -4
    ERROR = -3
    FAIL = -2
    WARN = -1
    INFO = 0
    PASS = 1
    DEBUG = 2

    def __str__(self):
        return self.name


_LOG_NTP_TIMER = NtpTimer()
@dataclass
class Log:
    """
        level: LogLevel
        msg: str
        time: float = UNIX time
    """
    level: LogLevel
    msg: str
    time: float = field(default_factory=_LOG_NTP_TIMER.now)


class SystemLogger(metaclass=Singleton):
    """
    시스템 전역에서 발생하는 로그를 수집하여 등록된 처리 함수로 전달하는 싱글톤 로거 클래스

    Note:
        * emit_function과 alert_function이 등록되지 않은 초기 상태에서 로그가 들어오면 임시 큐에 보관 후 감시 스레드를 시작합니다.
        * 감시 스레드는 0.5초 간격으로 두 함수 등록 여부를 확인하며, 등록 완료 시 누적된 로그를 전부 전송하고 종료됩니다.
        * 스레드가 종료된 후 또는 이미 정상 등록된 이후에 콜백 함수가 누락되면 RuntimeError가 발생합니다.
    """

    def __init__(self):

        self._emit_fn: Callable[[Log], Any] | None = None
        self._alert_fn: Callable[[Log], Any] | None = None

        self._lock = threading.Lock()
        self._init_queue: Queue[tuple[Log, bool | None]] = Queue() # 로그, is_alert
        self._is_init: bool = True  # 초기 버퍼링 가능 여부 플래그
        self._init_thread = threading.Thread(target=self._init_queue_check_and_emit, daemon=True)
        self._init_thread.start()

    def emit(self, level: LogLevel, message: str, is_alert: bool | None = None) -> None:
        """시스템에 로그를 발생시키고 등록된 콜백 함수를 통해 처리합니다.

        Args:
            level (LogLevel): 로그 심각도
            message (str): 로그 내용
            is_alert (bool | None): 알림 여부
        """
        self._emit_logic_1(Log(level=level, msg=message), is_alert)

    def _emit_logic_1(self, log_obj: Log, is_alert: bool | None = None) -> None:
        if self._is_init:
            with self._lock:
                if self._is_init:
                    self._init_queue.put((log_obj, is_alert))
                    return

        self._emit_logic_2(log_obj, is_alert)

    def _emit_logic_2(self, log_obj: Log, is_alert: bool | None = None):
        if self._emit_fn is None or self._alert_fn is None:
            raise RuntimeError("로그 처리용 콜백 함수(emit_fn, alert_fn)가 등록되지 않았습니다.")

        self._emit_fn(log_obj)

        match is_alert:
            case None:
                if log_obj.level in (LogLevel.PASS, LogLevel.FAIL):
                    self._alert_fn(log_obj)
            case True:
                self._alert_fn(log_obj)
            case False:
                return
            case _:
                raise TypeError(f"is_alert 값이 올바르지 않습니다: {type(is_alert)}")

    def _init_queue_check_and_emit(self):
        while True:
            if self._emit_fn is not None and self._alert_fn is not None:
                while not self._init_queue.empty():
                    try:
                        log, is_alert = self._init_queue.get_nowait()
                        self._emit_logic_2(log, is_alert)
                    except Empty:
                        break

                self._is_init = False
                break

            time.sleep(0.5)

    def set_emit_function(self, fn: Callable[[Log], Any]) -> None:
        """기본 로그를 처리할 콜백 함수를 등록합니다.

        Args:
            fn (Callable[[Log], Any]): 로그 발생 시 호출될 함수 또는 메서드입니다. 반드시 단일 `Log` 객체를 인자로 받아야 합니다.

        Raises:
            TypeError: 전달받은 'fn'이 호출 가능한(Callable) 객체가 아닌 경우 발생합니다.
        """
        if not callable(fn):
            raise TypeError("emit_function은 호출 가능한(Callable) 메서드여야 합니다.")

        with self._lock:
            if self._emit_fn is not None:
                raise RuntimeError("emit_function은 한 번만 등록할 수 있습니다. 이미 등록되어 있습니다.")
            self._emit_fn = fn

    def set_alert_function(self, fn: Callable[[Log], Any]) -> None:
        """로그를 알릴 콜백 함수를 등록합니다.

        Args:
            fn (Callable[[Log], Any]): 알람 로그 발생 시 호출될 함수 또는 메서드입니다. 반드시 단일 `Log` 객체를 인자로 받아야 합니다.

        Raises:
            TypeError: 전달받은 'fn'이 호출 가능한(Callable) 객체가 아닌 경우 발생합니다.
        """
        if not callable(fn):
            raise TypeError("alert_function은 호출 가능한(Callable) 메서드여야 합니다.")

        with self._lock:
            if self._alert_fn is not None:
                raise RuntimeError("alert_function은 한 번만 등록할 수 있습니다. 이미 등록되어 있습니다.")
            self._alert_fn = fn