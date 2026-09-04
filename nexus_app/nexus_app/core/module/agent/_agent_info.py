from datetime import datetime

import psutil
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Input, Label, Rule

from nexus_app.core.module.base import EmptyWidget
from nexus_app.core.service.agent import Agent, AgentManager, AgentSendMode, AgentStatus
from nexus_app.core.service.log import SystemLogger

from ._base import AgPane

_NO_INFO = "[$foreground 70%]-[/]"


def _format_timestamp(ts: float | None) -> str:
    """Unix 타임스탬프를 읽기 쉬운 문자열로 변환"""
    if ts is None:
        return _NO_INFO
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(seconds: float | None) -> str:
    """실행 시간을 HH:MM:SS 형태로 포맷팅"""
    if seconds is None:
        return _NO_INFO
    total_sec = int(seconds)
    hours, remainder = divmod(total_sec, 3600)
    minutes, sec = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def _get_child_pids(parent_pid: int | None) -> list[int]:
    """부모 PID로부터 활성 자식 프로세스 PID 목록 조회"""
    if parent_pid is None:
        return []
    try:
        parent_proc = psutil.Process(parent_pid)
        return [child.pid for child in parent_proc.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return []


class AgentInfoPane(AgPane):
    DEFAULT_CSS = """
    AgentInfoPane {
        height: 7;
        
        & > Container{
            min-width: 60;
            
            #info_left {
                margin-right: 1;
            }
            
            #info_right {
                margin-left: 1;
            }
        }
        
        .info_set {
            height: 1;
        }
        
        .venv_row {
            height: auto;
        }
        
        .info_key {
            width: 14;
            color: $text-muted;
        }
    
        .info_val {
            width: 1fr;
        }
    }

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.now_agent: Agent | None = None
        self.agent_mng = AgentManager()
        self.logger = SystemLogger()

        # widget var
        self.empty_widget = EmptyWidget()
        self.agent_info_ctn = Container()

        self.name_lb = Label(_NO_INFO, classes="info_val")
        self.status_lb = Label(_NO_INFO, classes="info_val")
        self.pid_lb = Label(_NO_INFO, classes="info_val")
        self.child_pid_lb = Label(_NO_INFO, classes="info_val")
        self.file_exist_lb = Label(_NO_INFO, classes="info_val")
        self.send_mode_lb = Label(_NO_INFO, classes="info_val")
        self.run_time_lb = Label(_NO_INFO, classes="info_val")
        self.start_time_lb = Label(_NO_INFO, classes="info_val")
        self.end_time_lb = Label(_NO_INFO, classes="info_val")

        # Input 위젯 변수
        self.venv_input = Input(id="venv_input", placeholder="Venv directory path")

    # VIEW =============================================================================================================

    def compose(self) -> ComposeResult:
        self.border_title = "Info"

        yield self.empty_widget

        with self.agent_info_ctn:
            with Horizontal():
                with Container(id="info_left"):
                    with Horizontal(classes="info_row"):
                        yield Label("Name:", classes="info_key")
                        yield self.name_lb

                    with Horizontal(classes="info_row"):
                        yield Label("Status:", classes="info_key")
                        yield self.status_lb

                    with Horizontal(classes="info_row"):
                        yield Label("PID:", classes="info_key")
                        yield self.pid_lb

                    with Horizontal(classes="info_row"):
                        yield Label("File exist:", classes="info_key")
                        yield self.file_exist_lb

                yield Rule(orientation="vertical")

                with Container(id="info_right"):
                    with Horizontal(classes="info_row"):
                        yield Label("Send mode:", classes="info_key")
                        yield self.send_mode_lb

                    with Horizontal(classes="info_row"):
                        yield Label("Run time:", classes="info_key")
                        yield self.run_time_lb

                    with Horizontal(classes="info_row"):
                        yield Label("Start time:", classes="info_key")
                        yield self.start_time_lb

                    with Horizontal(classes="info_row"):
                        yield Label("End time:", classes="info_key")
                        yield self.end_time_lb

            with Horizontal(classes="venv_row"):
                yield Label("Venv path:", classes="info_key")
                yield self.venv_input

    def on_mount(self):
        self.update_agent_info()
        self.set_interval(0.5, self.update_agent_info)

    # EVENT ============================================================================================================

    @on(Input.Submitted, "#venv_input")
    def enter_venv_input(self, event: Input.Submitted) -> None:
        if self.now_agent is None:
            return

        new_path: str = event.value.strip()
        old_path: str = str(self.now_agent.venv_path or "")

        if new_path == old_path or not new_path:
            event.input.value = old_path
            self.venv_input.action_end()
            return

        changed_path = str(self.now_agent.set_venv_path(new_path) or "")
        event.input.value = changed_path
        event.input.action_end()

        if changed_path != old_path:
            self.screen.set_focus(None)
            self.focus()
        self.update_agent_info()

    # LOGIC ============================================================================================================

    def watch_now_agent_name(self, new_name: str | None) -> None:
        """선택된 에이전트가 바뀔 때마다 작동"""
        if new_name is None:
            self.now_agent = None
        else:
            self.now_agent = self.agent_mng.search_agent(new_name)

        if self.now_agent is None:
            self.agent_info_ctn.display = False
            self.empty_widget.display = True
        else:
            self.empty_widget.display = False
            self.agent_info_ctn.display = True
            self.venv_input.value = str(self.now_agent.venv_path or "")

        self.update_agent_info()

    def update_agent_info(self) -> None:
        """에이전트 정보 UI 업데이트"""
        if self.now_agent is None:
            return

        agent = self.now_agent

        # name
        self.name_lb.update(agent.name)

        # file exist
        if agent.is_file_exist:
            self.file_exist_lb.update("[$success-lighten-1]YES[/]")
        else:
            self.file_exist_lb.update("[$error-lighten-1]NO[/]")

        # status
        match agent.status:
            case AgentStatus.SLEEPING:
                self.status_lb.update(f"[$foreground 80%]{agent.status.name}[/]")
            case AgentStatus.RUNNING:
                self.status_lb.update(f"[$success-lighten-2]{agent.status.name}[/]")
            case AgentStatus.STOPPING:
                self.status_lb.update(f"[$warning-lighten-2]{agent.status.name}[/]")
            case AgentStatus.STOPPED:
                self.status_lb.update(f"[$error-lighten-2]{agent.status.name}[/]")

        # send mode
        send_mode_val = agent.send_mode
        match agent.send_mode:
            case AgentSendMode.NoSend:
                self.send_mode_lb.update("[$error-lighten-1]No Send[/]")
            case AgentSendMode.Send:
                self.send_mode_lb.update("[$success-lighten-1]Send[/]")
            case AgentSendMode.SendTest:
                self.send_mode_lb.update("[$primary-lighten-1]Send test[/]")

        # PID, 자식 프로세스
        pid = agent.pid
        if pid is not None:
            child_pids = _get_child_pids(pid)
            if child_pids:
                pids_str = ", ".join(str(cp) for cp in child_pids)
                self.pid_lb.update(f"{pid} › {pids_str}")
            else:
                self.pid_lb.update(f"{pid}")
        else:
            self.pid_lb.update(_NO_INFO)

        # 시간
        self.run_time_lb.update(_format_duration(agent.run_time))
        self.start_time_lb.update(_format_timestamp(agent.start_time))
        self.end_time_lb.update(_format_timestamp(agent.end_time))

        # 5. Venv 경로
        if not self.venv_input.has_focus:
            self.venv_input.value = str(agent.venv_path or "")
