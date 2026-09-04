import datetime
import threading
import time
from enum import Enum
from zoneinfo import ZoneInfo

import ntplib

from ._singleton import Singleton

__all__ = ["TimeZone", "NtpTimer"]


class TimeZone(Enum):
    """지원하는 주요 지역별 타임존(ZoneInfo) 옵션

    Attributes:
        UTC
        SEOUL
        NEW_YORK
    """

    UTC = ZoneInfo("UTC")
    SEOUL = ZoneInfo("Asia/Seoul")
    NEW_YORK = ZoneInfo("America/New_York")


class NtpTimer(metaclass=Singleton):
    """NTP 서버와 주기적으로 시각을 동기화하여 정확한 타임스탬프를 제공하는 싱글톤 클래스입니다.

    Notes:
        NTP 서버 동기화 에러가 발생한 경우 1분마다 업데이트를 시도하며 정상적인 상황에 경우 4시간마다 실행
    """

    def __init__(self):
        self._is_problem: bool = False
        self._time_offset: float = 0.0
        self._lock = threading.Lock()

        # 백그라운드 NTP 동기화 스레드 시작
        threading.Thread(target=self._ntp_time_sync, daemon=True).start()

    @property
    def is_problem(self) -> bool:
        """NTP 서버 동기화 실패 등 문제 발생 여부를 반환합니다.

        Returns:
            bool: 동기화에 문제가 발생한 경우 True, 정상 작동 중인 경우 False.
        """
        with self._lock:
            return self._is_problem

    def fix_time(self, wrong_time: float) -> float:
        """잘못된 타임스탬프를 NTP 오프셋으로 보정하여 반환합니다.

        Args:
            wrong_time: NTP 보정되지 않은 시간값
        Returns:
            float: NTP 서버 오차가 반영된 현재 유닉스 타임스탬프 (Epoch 초).
        """
        return wrong_time + self._time_offset

    def now(self) -> float:
        """NTP 오프셋이 보정된 현재 UTC 타임스탬프를 반환합니다.

        Returns:
            float: NTP 서버 오차가 반영된 현재 유닉스 타임스탬프 (Epoch 초).
        """
        return time.time() + self._time_offset

    def now_str(self, str_format: str = "%Y-%m-%d %p %I:%M:%S", tz: TimeZone = TimeZone.SEOUL) -> str:
        """NTP 오프셋이 보정된 현재 시각을 지정된 포맷과 타임존의 문자열로 반환합니다.

        Args:
            str_format (str, optional): datetime 날짜/시간 서식 문자열.
                기본값은 '%Y-%m-%d %p %I:%M:%S'.
            tz (TimeZone, optional): 적용할 타임존 (TimeZone Enum).
                기본값은 TimeZone.SEOUL.

        Returns:
            str: 지정된 타임존 및 서식으로 포맷팅된 현재 시각 문자열.
        """
        return self.float_to_str(self.now(), str_format=str_format, tz=tz)

    @staticmethod
    def float_to_str(time_value: float, str_format: str = "%Y-%m-%d %p %I:%M:%S", tz: TimeZone = TimeZone.SEOUL) -> str:
        """유닉스 타임스탬프(float)를 지정된 포맷과 타임존의 문자열로 변환합니다.

        Args:
            time_value (float): 변환할 유닉스 타임스탬프 (Epoch 초).
            str_format (str, optional): datetime 날짜/시간 서식 문자열.
                기본값은 '%Y-%m-%d %p %I:%M:%S'.
            tz (TimeZone, optional): 적용할 타임존 (TimeZone Enum).
                기본값은 TimeZone.SEOUL.

        Returns:
            str: 지정된 타임존 및 서식으로 포맷팅된 시각 문자열.
        """
        return datetime.datetime.fromtimestamp(time_value, tz=tz.value).strftime(str_format)

    @staticmethod
    def get_utc_offset_hours(time_value: float, tz: TimeZone = TimeZone.NEW_YORK) -> int:
        """유닉스 타임스탬프(float)와 타임존을 기반으로 UTC 오프셋(시간 단위 정수)을 반환합니다.

        Args:
            time_value (float): 유닉스 타임스탬프 (Epoch 초).
            tz (TimeZone, optional): 대상 타임존 (TimeZone Enum).
                기본값은 TimeZone.NEW_YORK.

        Returns:
            int: UTC 대비 시간 차이 (예: 뉴욕 서머타임 -4, 표준시 -5, 서울 +9)
        """
        dt = datetime.datetime.fromtimestamp(time_value, tz=tz.value)
        offset = dt.utcoffset()
        return int(offset.total_seconds() // 3600) if offset is not None else 0

    def _ntp_time_sync(self):
        # ntp요청, 동기화
        while True:
            try:
                response = ntplib.NTPClient().request("time.google.com", version=3, timeout=5.0)
                with self._lock:
                    self._time_offset = response.offset
                    self._is_problem = False
                time.sleep(60 * 60 * 4)  # 4시간 주기
            except Exception:
                with self._lock:
                    self._is_problem = True
                time.sleep(60)  # 실패 시 1분 후 재시도
