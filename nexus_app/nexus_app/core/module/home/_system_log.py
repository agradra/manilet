from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Rule

from nexus_app.core.module.base import NxLog, NxRunButton, Pane
from nexus_app.core.service.log import Log, LogLevel, SystemLogger
from nexus_app.core.service.time import NtpTimer


class SystemLogPane(Pane):
    DEFAULT_CSS = """
    SystemLogPane {
        Horizontal {
            height: 1;
        }
    }

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.border_title = "System log"
        self.border_subtitle = "log: 0"
        self.log_n = 0
        self.sys_logger = SystemLogger()
        self.nx_log = NxLog()
        self.last_log: str = ""  # 마지막 로그 저장용

        # 로그 알람 처리
        def on_log_alerted(log: Log):
            if log.level > LogLevel.WARN:
                svt = "information"
            elif log.level == LogLevel.WARN:
                svt = "warning"
            else:
                svt = "error"

            if svt:
                self.app.notify(log.msg, title=f"{log.level}", severity=svt)

        self.sys_logger.set_alert_function(on_log_alerted)

        # 로그 일반 처리
        def on_log_emitted(log: Log):
            self.last_log = self.nx_log.write_log(log)
            self.log_n += 1
            self.border_subtitle = f"log: {self.log_n}"

        self.sys_logger.set_emit_function(on_log_emitted)

    def compose(self) -> ComposeResult:
        yield self.nx_log
        yield Rule()
        with Horizontal():
            yield NxRunButton("Clear", action=self.btn_clear)
            yield NxRunButton("Save logs", action=self.btn_save)
            yield NxRunButton("Copy Latest", action=self.btn_copy)
            yield NxRunButton("Jump to End", action=self.btn_jump_end)

    def btn_clear(self):
        self.nx_log.clear()
        self.last_log = ""
        self.log_n = 0
        self.border_subtitle = "log: 0"

    def btn_save(self):
        try:
            dir_path = Path(self.app.log_save_dir_path)
            if not dir_path.exists():
                raise FileNotFoundError(f"'{self.app.log_save_dir_path}'폴더를 찾을 수 없음.")
        except Exception as e:
            self.sys_logger.emit(
                LogLevel.ERROR,
                f" 로그 파일 저장중 폴더 경로 관련 에러가 발생하였습니다. ({self.app.log_save_dir_path})\n→ {e}",
                is_alert=True,
            )
            return

        log_content = "\n".join(str(line) for line in self.nx_log.lines)
        if not log_content.strip():
            self.app.notify("저장할 시스템 로그가 없습니다.", title="Save logs", severity="error")
            return
        timestamp = NtpTimer().now_str("%Y-%m-%d_%p_%I-%M-%S")
        file_name = f"Nexus_system_log_{timestamp}.txt"
        file_path = dir_path / file_name

        try:
            file_path.write_text(log_content, encoding="utf-8")
            self.sys_logger.emit(
                LogLevel.PASS, f" 로그 파일({file_name})이 저장되었습니다.\n→ {file_path}", is_alert=True
            )
        except Exception as e:
            self.sys_logger.emit(
                LogLevel.ERROR, f"'{file_name}' 저장중 에러가 발생하였습니다. ({file_path})\n→ {e}", is_alert=True
            )

    def btn_copy(self):
        if hasattr(self.nx_log, "lines") and self.nx_log.lines:
            self.app.copy_to_clipboard(self.last_log)
            self.app.notify("마지막 로그를 클립보드에 복사했습니다.", title="Copy Latest")
        else:
            self.app.notify("복사할 로그가 없습니다.", title="Copy Latest", severity="error")

    def btn_jump_end(self):
        self.nx_log.scroll_end(animate=False)
