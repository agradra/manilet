from textual import on
from textual.app import ComposeResult
from textual.widgets import Input

from nexus_app.core.module.base import Pane, NxRunButton
from nexus_app.core.service.agent import AgentManager
from nexus_app.core.service.log import SystemLogger, LogLevel


class DefaultVenvPathPane(Pane):
    DEFAULT_CSS = """
        DefaultVenvPathPane {
            layout: horizontal;
            height: 3;
            max-height: 3;
            
            & > Input {
                width: 1fr;
            }
        }

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.border_title = "Default venv"

        self.sys_logger = SystemLogger()
        self.agent_mng = AgentManager()
        self.default_venv_path_input = Input(self.agent_mng.default_venv_path, placeholder="Venv directory path", id="default_venv_path_input")

    def compose(self) -> ComposeResult:
        yield NxRunButton("Apply all", action=self.apply_all_btn)
        yield self.default_venv_path_input

    def apply_all_btn(self) -> None:
        self.agent_mng.apply_venv_agents(False)

    # 엔터 눌렀을 때 실행
    @on(Input.Submitted, "#default_venv_path_input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_path = event.value.strip()
        old_path = self.agent_mng.default_venv_path

        if new_path == old_path:
            return

        # 비었으면 리턴
        if not new_path:
            self.sys_logger.emit(LogLevel.FAIL, f"가상환경 폴더 경로를 입력해 주세요.\n( 현 가상환경 경로 - {old_path} )")
            event.input.value = old_path
            self.default_venv_path_input.action_end()
            return

        self.agent_mng.set_default_venv(new_path)
        changed_path = self.agent_mng.default_venv_path
        if changed_path != old_path: # 변경 완료
            self.screen.set_focus(None)
            self.focus()
        else: # 변경 실패
            self.default_venv_path_input.action_end()
        event.input.value = changed_path
