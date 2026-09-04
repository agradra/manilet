from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.widgets import Input

from nexus_app.config import DEFAULT_LOG_PATH
from nexus_app.core.module.base import Pane
from nexus_app.core.service.db import CryptoDB
from nexus_app.core.service.log import SystemLogger, LogLevel


class LogSaveDirPathPane(Pane):
    DEFAULT_CSS = """
        LogSaveDirPathPane {
            max-height: 3;
        }

    """

    DB_KEY = "log_save_dir_path"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.border_title = "Log directory path"

        self.sys_logger = SystemLogger()
        self.db = CryptoDB("LogSaveDirPathPane")
        self.app.log_save_dir_path = self.db.create(self.DB_KEY, str(DEFAULT_LOG_PATH), exist_ok=True, encrypt=True)
        self.path_input = Input(self.app.log_save_dir_path, placeholder="Log directory path", id="log-dir-input")

    def compose(self) -> ComposeResult:
        yield self.path_input

    # 엔터 눌렀을 때 실행
    @on(Input.Submitted, "#log-dir-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_path = event.value.strip()
        old_path = self.app.log_save_dir_path

        if new_path == old_path:
            return

        # 비었으면 리턴
        if not new_path:
            self.sys_logger.emit(LogLevel.FAIL, f"로그 저장 폴더 경로를 입력해 주세요.\n( 현 저장 경로 - {old_path} )", is_alert=True)
            event.input.value = old_path
            self.path_input.action_end()
            return

        # 실제 생성 가능 폴더인지 확인
        try:
            path_obj = Path(new_path)
            if not path_obj.is_absolute():
                raise FileExistsError()
            if not path_obj.exists():
                raise FileExistsError()
        except Exception:
            self.sys_logger.emit(LogLevel.WARN,
                                 f"로그 저장 폴더 경로 설정을 실패하였습니다. 존재하지 않거나 잘못된 경로 입니다.\n( 현 저장 경로 - {old_path} )",
                                 is_alert=True)
            event.input.value = old_path
            self.path_input.action_end()
            return

        event.input.value = new_path
        self.screen.set_focus(None)
        self.focus()
        self.app.log_save_dir_path = new_path
        self.db.update(self.DB_KEY, new_path)
        self.sys_logger.emit(LogLevel.PASS, f"로그 저장 폴더 경로를 저장하였습니다.\n( 새 저장 경로 - {new_path} )", is_alert=True)
