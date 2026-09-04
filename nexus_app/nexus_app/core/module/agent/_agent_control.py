from textual.app import ComposeResult
from textual.widgets import Rule, Label, Static

from nexus_app.core.module.base import NxRunButton, NxRadioSet, NxRadioButton
from nexus_app.core.service.agent import AgentManager, Agent, AgentSendMode
from nexus_app.core.service.log import SystemLogger
from ._base import AgPane


class AgentControlPane(AgPane):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.now_agent: Agent | None = None
        self.agent_mng = AgentManager()
        self.logger = SystemLogger()

        # widget var
        self.no_send_btn   = NxRadioButton("No send", callback_arg=AgentSendMode.NoSend)
        self.send_btn      = NxRadioButton("Send", callback_arg=AgentSendMode.Send)
        self.send_test_btn = NxRadioButton("Send test", callback_arg=AgentSendMode.SendTest)

    # VIEW =============================================================================================================
    DEFAULT_CSS = """
        AgentControlPane {
            layout: horizontal;
            height: 3;
            & > .spacer {
                width: 1fr;
            }
            & > Label {
                margin-left: 1;
                margin-right: 3;
            
                &:disabled {
                    text-opacity: 1;
                    text-style: dim;
                }
            }
        }
        """

    def compose(self) -> ComposeResult:
        self.border_title = "Control"
        yield NxRunButton("Run", action=self.run_agent, variant="success")
        yield NxRunButton("Stop", action=self.stop_agent, variant="error")
        yield NxRunButton("Reset", action=self.reset_agent)

        yield Static(classes="spacer")

        yield Rule(orientation="vertical")
        yield Label("Send mode:")
        yield NxRadioSet(
            self.no_send_btn, self.send_btn, self.send_test_btn,
            callback=self.send_mode_change
        )

    # EVENT ============================================================================================================

    def run_agent(self) -> None:
        if self.now_agent is not None:
            self.now_agent.run()

    def stop_agent(self) -> None:
        if self.now_agent is not None:
            self.now_agent.stop()

    def reset_agent(self) -> None:
        if self.now_agent is not None:
            self.now_agent.reset()

    def send_mode_change(self, send_mode: AgentSendMode) -> None:
        if self.now_agent is not None:
            self.now_agent.set_send_mode(send_mode)

    # LOGIC ============================================================================================================

    def watch_now_agent_name(self, new_name: str | None) -> None:
        """선택된 에이전트가 바뀔 때마다 작동"""
        if new_name is None:
            self.now_agent = None
            for child in self.children:
                child.disabled = True
            return

        self.now_agent = self.agent_mng.search_agent(new_name)
        if self.now_agent is None:
            for child in self.children:
                child.disabled = True
        else:
            self.sync_radio_button()
            for child in self.children:
                child.disabled = False


    def sync_radio_button(self) -> None:
        """현재 에이전트 전송 모드 -> 라디오 버튼 동기화"""
        if not self.now_agent:
            return

        now_mode = self.now_agent.send_mode

        if now_mode == AgentSendMode.NoSend:
            self.no_send_btn.value = True
        elif now_mode == AgentSendMode.Send:
            self.send_btn.value = True
        elif now_mode == AgentSendMode.SendTest:
            self.send_test_btn.value = True
        else:
            raise ValueError("와아아아아앗? ㅈㄴ 말안되는 전송 모드 들어옴: " + str(now_mode))
