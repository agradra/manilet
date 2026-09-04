import asyncio
import os
import socket

import psutil
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Label

from nexus_app.config import TITLE, VERSION
from nexus_app.core.module.home import PerformancePane
from nexus_app.core.service.discord import Discord
from nexus_app.core.service.log import LogLevel, SystemLogger
from nexus_app.core.service.time import NtpTimer, TimeZone


def _is_internet_connected(host="8.8.8.8", port=53, timeout=3) -> bool:
    """
    인터넷 연결 상태를 확인합니다.
    :param host: 연결을 테스트할 호스트 IP (기본값: 구글 DNS)
    :param port: 포트 번호 (기본값: 53 - DNS 서비스 포트)
    :param timeout: 타임아웃 대기 시간 (초)
    :return: 인터넷 연결 여부 (True/False)
    """
    try:
        # IPv4(AF_INET) 및 TCP(SOCK_STREAM) 소켓 객체 생성
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))  # 연결 시도
        return True
    except socket.error:
        # 연결 실패(네트워크 단절, 타임아웃 등)
        return False


class NxHeader(Horizontal):
    DEFAULT_CSS = """
        NxHeader {
            height: 3;
            padding: 1 2 0 2;
        }
        
        #app-name {
            text-style: bold;
            color: $accent-lighten-1;
            margin-right: 1;
        }

        #app-version {
            text-style: dim;
            color: $accent-lighten-1 60%;
            margin-right: 2;
        }

        #header-status {
            dock: right; /* 오른쪽 고정 라벨 */
            color: $primary-background-lighten-3;
            width: auto;
        }
        """

    SIGNAL_LEVEL_COLOR = ["bright_red", "bright_yellow", "bright_green", "bright_cyan"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.discord = Discord()
        self.sys_logger = SystemLogger()

        self.name_label = Label(f"↪ {TITLE}", id="app-name")
        self.version_label = Label(VERSION, id="app-version")
        self.children_horizon = Horizontal(id="header-children")

        self._init_status = "○"
        self._good_status = "[$success]◉[/]"
        self._bad_status = "[$error]◎[/]"
        self._status_change: bool = True
        self.status_label = Label(self._init_status)

    def compose(self) -> ComposeResult:
        yield self.children_horizon
        with Horizontal(id="header-status"):
            yield Label("internet ")
            yield self.status_label

    def on_mount(self):
        if self.children:
            self.children_horizon.mount(self.name_label, self.version_label, before=self.children[0])
        else:
            self.children_horizon.mount(self.name_label, self.version_label)

        self.tick()
        self.set_interval(2, self.tick)

    async def tick(self) -> None:
        self.status_label.update(self._init_status)
        await asyncio.sleep(1)

        if _is_internet_connected():
            self.status_label.update(self._good_status)
            if not self._status_change:
                self.sys_logger.emit(LogLevel.DEBUG, "인터넷이 연결되었습니다.")
                self._status_change = True
        else:
            self.status_label.update(self._bad_status)
            if self._status_change:
                self.sys_logger.emit(LogLevel.WARN, "인터넷을 확인해주세요.")
                self._status_change = False

        """
        if self.discord.is_connect:
            self.dc_connect_i = min(4, self.dc_connect_i + 1)
        else:
            self.dc_connect_i = max(0, self.dc_connect_i - 2)
        
        text.append(" / Discord ")
        for i in range(4):
            if i < self.dc_connect_i:
                text.append("■", style=self.SIGNAL_LEVEL_COLOR[i])
            else:
                text.append("□")"""


class NxFooter(Widget):
    DEFAULT_CSS = """
    NxFooter {
        color: $footer-description-foreground;
        dock: bottom;
        width: 100%;
        height: 1;
        layout: horizontal;
        background: $footer-background;
        scrollbar-size: 0 0;
    }

    #footer-performance {
        width: auto;
        dock: right;
        padding-right: 1;
        border-left: vkey $footer-description-foreground 20%;
    }

    #footer-time {
        padding-left: 1;
    }
    """

    # Footer 색상값 모방
    K_TAG = "$footer-key-foreground"
    D_TAG = "$footer-description-foreground"
    DD_TAG = "$footer-description-foreground 50%"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ntp_time = NtpTimer()

        self.sys_process = psutil.Process(os.getpid())
        self.old_second = None

        self.stats_label = Label(id="footer-performance")
        self.time_label = Label(id="footer-time")

        self.ntp_str = ""
        self.time_offset = 0.0

    def compose(self) -> ComposeResult:
        yield self.stats_label
        yield self.time_label

    def on_mount(self):
        self.watch(self.app.query_one(PerformancePane), "cpu_ram_share", self._performance_label_update)

        self.tick()
        self.set_interval(0.1, self.tick)

    def tick(self) -> None:
        new_second = int(self.ntp_time.now())
        if self.old_second != new_second or self.old_second is None:
            self._time_label_update()
            self.old_second = new_second

    def _performance_label_update(self, cpu_ram_share: tuple[str, str]):
        cpu, ram = cpu_ram_share

        self.stats_label.update(
            f"[{self.K_TAG}]cpu[/] [{self.D_TAG}]{cpu[:-3]}%[/]  "
            f"[{self.K_TAG}]ram[/] [{self.D_TAG}]{ram[:-5] + ram[-3:] if ram.endswith('B') else ram[:-3] + '%'}[/]"
        )

    def _time_label_update(self):
        try:
            real_timestamp = self.ntp_time.now()

            now_utc = self.ntp_time.float_to_str(real_timestamp, tz=TimeZone.UTC)
            now_seoul = self.ntp_time.float_to_str(real_timestamp, tz=TimeZone.SEOUL)
            now_ny = self.ntp_time.float_to_str(real_timestamp, tz=TimeZone.NEW_YORK)

            ny_offset = self.ntp_time.get_utc_offset_hours(real_timestamp, tz=TimeZone.NEW_YORK)

            # NTP 문제 발생 시 에러 태그 추가
            ntp_str = "[$text-error]NTP 🅧[/]   " if self.ntp_time.is_problem else ""

            self.time_label.update(
                f"{ntp_str}"
                f"[{self.K_TAG}]UTC[/] {now_utc}  "
                f"[{self.K_TAG}]NewYork[/] {now_ny} [{self.DD_TAG}]({ny_offset:+}h)[/]  "
                f"[{self.K_TAG}]Seoul[/] {now_seoul} [{self.DD_TAG}](+9h)[/]"
            )
        except Exception:
            self.time_label.update("[$text-error]TIME ERROR[/]")
