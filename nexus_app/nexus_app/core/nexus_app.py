from textual import on
from textual.app import ComposeResult, App
from textual.containers import Horizontal, Container, Vertical, Grid
from textual.widgets import ContentSwitcher, Tabs, Tab, Label, Static
from textual.widgets._tabs import Underline

from .module.agent import *
from .module.home import *
from .module.modal import QuitModal
from .module.shell import NxFooter, NxHeader
from .service.agent import AgentManager
from .service.discord import Discord

# 텍스트 드래그 방지용
for class_type in [
    NxFooter,
    NxHeader,
    Container,
    Horizontal,
    Vertical,
    Static,
    Tabs,
    Tab,
    Underline,
]:class_type.ALLOW_SELECT = False

class NexusApp(App):
    CSS_PATH = "style.tcss"

    def __init__(self):
        super().__init__()
        self.switcher = ContentSwitcher(id="switcher")

    # 탭 변경
    @on(Tabs.TabActivated)
    def handle_tab_activated(self, event: Tabs.TabActivated):
        if event.tab.id:
            self.switcher.current = event.tab.id.replace("_btn", "")

    def on_unmount(self):
        Discord().kill()
        AgentManager().kill()

    # ^q -> 앱 종료 팝업
    # f1 -> 키 모음 팝업
    BINDINGS = [("ctrl+q", "request_quit", "Quit"),("f1","toggle_help_panel", "key")]
    def action_request_quit(self) -> None:

        def check_quit(should_quit: bool | None) -> None:
            if should_quit:
                self.exit()

        self.push_screen(QuitModal(), check_quit)

    def action_toggle_help_panel(self):
        if self.screen.query("HelpPanel"):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    # 공유 데이터 ===============================================

    log_save_dir_path: str = ""

    # 디자인 ====================================================

    CSS = """

        /* 헤더 > 탭 변경 버튼 */
        Tabs { /* 탭 버튼 넓이 자동 조절 안됨 */
            width: 21;
        }

        Tab.-active { /* 탭 버튼 포커스 시 색깔 풀림 방지 */
            text-style: $block-cursor-text-style;
            color: $block-cursor-foreground;
            background: $block-cursor-background;
        }

        /* 메인 */
        #switcher {
            padding: 1 2;
            height: 1fr;        
            & > * {
                width: 100%;
                height: 100%;
            }
        }
        
        /*===[ 탭 설정 ]=======================================================*/
        #home-tab {
            layout: grid;
            grid-size: 2 1;
            grid-columns: 1fr 1fr;
        }
        #agent-tab {
            layout: grid;
            grid-size: 1 2;
            grid-rows: 1fr 3;
            
            & > Grid {
                grid-size: 2 1;
                grid-columns: 2fr 3fr;
            }
        }

        #wallet-tab{
            text-style: bold;
            color: $foreground-muted 50%;
            align: center middle;
            hatch: right $foreground-muted 20%;
        }

        """

    def compose(self) -> ComposeResult:
        with NxHeader():
            yield Tabs(
                Tab("Home", id="home-tab_btn"),
                Tab("Agent", id="agent-tab_btn"),
                Tab("Wallet", id="wallet-tab_btn"),
            )

        with self.switcher:
            with Container(id="home-tab"):
                with Container():
                    yield PerformancePane()
                    yield DiscordPane()
                with Container():
                    yield LogSaveDirPathPane()
                    yield SystemLogPane()

            with Container(id="agent-tab"):
                with Horizontal():
                    yield AgentListPane()
                    with Vertical():
                        yield AgentInfoPane()
                        yield AgentLogPane()
                with Grid():
                    yield DefaultVenvPathPane()
                    yield AgentControlPane()

            with Container(id="wallet-tab"):
                yield Label("개발중...")

        yield NxFooter()