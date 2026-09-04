from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import Rule, ContentSwitcher, LoadingIndicator

from nexus_app.core.module.base import NxLog, NxRunButton
from nexus_app.core.service.agent import AgentManager, Agent
from nexus_app.core.service.log import SystemLogger, LogLevel
from nexus_app.core.service.time import NtpTimer
from ._base import AgPane
from ...service.discord import Discord

_NTP_TIMER = NtpTimer()
_DISCORD = Discord()

def _make_safe_id(name: str) -> str:
    """Textual ID로 사용할 수 있도록 에이전트 이름을 안전하게 변환"""
    return f"agent_log_{name.encode('utf-8').hex()}"

class _AgentLogContainer(Container):
    DEFAULT_CSS = """
    _AgentLogContainer {
        

    }
    """
    def __init__(self, agent, **kwargs):
        super().__init__(id= _make_safe_id(agent.name),**kwargs)
        self.agent: Agent = agent
        self.nx_log = NxLog()
        self.log_n: int = 0
        self.last_log: str = ""

        self._keep_running = True # 스레드 종료용 플래그

    def compose(self) -> ComposeResult:
        yield self.nx_log

    def on_mount(self) -> None:
        self.get_logs_in_background()

    def on_unmount(self) -> None:
        self._keep_running = False

    @work(thread=True)
    def get_logs_in_background(self) -> None:
        while self._keep_running:
            log_obj = self.agent.get_log(block=True, timeout=0.5)
            if log_obj is not None:
                self.last_log: str = self.app.call_from_thread(self.nx_log.write_log, log_obj)
                self.log_n += 1


class AgentLogPane(AgPane):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_mng = AgentManager()
        self.logger = SystemLogger()

        # widget var
        self.log_switcher = ContentSwitcher(initial=None)

        self.agent_log_ctn_dict: dict[str, _AgentLogContainer] = {} # 에이전트 이름 : _AgentLogContainer
        self.now_agent_name: str | None = None

    def on_mount(self):
        self._ensure_all_widgets()
        self.set_interval(0.2, self._change_border_subtitle)
        self.set_interval(0.7, self._ensure_all_widgets)

    # VIEW =============================================================================================================
    DEFAULT_CSS = """
        AgentLogPane {
            ContentSwitcher {
                height: 1fr;
            }
            
            & > Horizontal {
                height: 1;
            }
        }
    """

    def compose(self) -> ComposeResult:
        self.border_title = "Log"
        self.border_subtitle = "0"
        with self.log_switcher:
            yield LoadingIndicator(id="loading")
        yield Rule()
        with Horizontal():
            yield NxRunButton("Clear", action=self.btn_clear)
            yield NxRunButton("Save logs", action=self.btn_save)
            yield NxRunButton("Copy Latest", action=self.btn_copy)
            yield NxRunButton("Jump to End", action=self.btn_jump_end)

    # EVENT ============================================================================================================

    def btn_clear(self):
        now_log_ctn = self._get_now_log_ctn()
        if now_log_ctn is not None:
            now_log_ctn.nx_log.clear()
            now_log_ctn.last_log = ""
            now_log_ctn.log_n = 0

    def btn_save(self):
        now_log_ctn = self._get_now_log_ctn()
        if now_log_ctn is not None:
            try:
                dir_path = Path(self.app.log_save_dir_path)
                if not dir_path.exists():
                    raise FileNotFoundError(f"'{self.app.log_save_dir_path}'폴더를 찾을 수 없음.")
            except Exception as e:
                self.logger.emit(LogLevel.ERROR, f" 로그 파일 저장중 폴더 경로 관련 에러가 발생하였습니다. ({self.app.log_save_dir_path})\n→ {e}", is_alert=True)
                return

            log_content = "\n".join(str(line) for line in now_log_ctn.nx_log.lines)
            if not log_content.strip():
                self.app.notify("저장할 에이전트 로그가 없습니다.", title="Save logs", severity="error")

                return
            timestamp = _NTP_TIMER.now_str("%Y-%m-%d_%p_%I-%M-%S")
            safe_agent_name = now_log_ctn.agent.name.replace(" ", "_")
            file_name = f"{safe_agent_name}_log_{timestamp}.txt"
            file_path = dir_path / file_name

            try:
                file_path.write_text(log_content, encoding="utf-8")
                self.logger.emit(LogLevel.PASS, f" 로그 파일({file_name})이 저장되었습니다.\n→ {file_path}", is_alert=True)
            except Exception as e:
                self.logger.emit(LogLevel.ERROR, f"'{file_name}' 저장중 에러가 발생하였습니다. ({file_path})\n→ {e}", is_alert=True)

    def btn_copy(self):
        now_log_ctn = self._get_now_log_ctn()
        if now_log_ctn is not None:
            if now_log_ctn.nx_log.lines:
                self.app.copy_to_clipboard(now_log_ctn.last_log)
                self.app.notify("마지막 로그를 클립보드에 복사했습니다.", title="Copy Latest")
            else:
                self.app.notify("복사할 로그가 없습니다.", title="Copy Latest", severity="error")

    def btn_jump_end(self):
        now_log_ctn = self._get_now_log_ctn()
        if now_log_ctn is not None:
            now_log_ctn.nx_log.scroll_end(animate=False)

    # PRIVATE ==========================================================================================================

    def watch_now_agent_name(self, new_name: str | None) -> None:
        """선택된 에이전트가 바뀔 때마다 스위치의 채널 변경"""
        self.now_agent_name = new_name
        if not new_name:
            self.log_switcher.current = None
            for child in self.children:
                child.disabled = True
        else:
            try:
                self.log_switcher.current = _make_safe_id(new_name)
                for child in self.children:
                    child.disabled = False
            except Exception:
                self.log_switcher.current = "loading"

    def _get_now_log_ctn(self) -> _AgentLogContainer | None:
        """현재 switcher에 띄워진 로그 위젯 객체 반환"""
        if not self.now_agent_name:
            return None
        return self.agent_log_ctn_dict.get(self.now_agent_name, None)

    def _change_border_subtitle(self) -> None:
        now_log_ctn = self._get_now_log_ctn()
        if now_log_ctn is None:
            self.border_subtitle = None
        else:
            self.border_subtitle = f"dict n: {len(self.agent_log_ctn_dict)} / switcher n: {len(self.log_switcher.query(_AgentLogContainer))}/ log n: {now_log_ctn.log_n}"

    def _ensure_all_widgets(self) -> None:
        """새 에이전트 확인하고 스레드 위젯 장착"""
        for agent in self.agent_mng.get_agent_list():
            if agent.name not in self.agent_log_ctn_dict:
                new_log_ctn = _AgentLogContainer(agent=agent)
                self.agent_log_ctn_dict[agent.name] = new_log_ctn
                self.log_switcher.add_content(new_log_ctn)