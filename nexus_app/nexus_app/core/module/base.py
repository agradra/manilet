import re
from typing import Any, Callable

from rich.highlighter import Highlighter
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.geometry import Size
from textual.timer import Timer
from textual.widgets import Button, DataTable, Label, RadioButton, RadioSet, Static
from textual.widgets import Log as LogWidget

from nexus_app.core.service.log import Log
from nexus_app.core.service.time import NtpTimer


class Pane(Container):
    can_focus = True
    BINDINGS = [Binding("ctrl+g", "toggle_maximize", "Toggle maximize")]
    DEFAULT_CSS = """
    Pane {
        border: round $panel-lighten-2;
        padding-left: 1;  
        padding-right: 1;
        
        &:focus {
            border: round $accent;
        }
          
        &:focus-within {
            border: round $accent;
        }
    }

    """

    def action_toggle_maximize(self) -> None:
        if not self.is_maximized:
            self.screen.maximize(self)
        else:
            self.screen.minimize()


class NxRunButton(Button):
    def __init__(self, label: str, action: Callable[[], Any] | None = None, *args, **kwargs):
        """
        Args:
            label: 버튼에 표시될 텍스트
            action: 버튼이 눌렸을 때 실행될 함수 (콜백)
        """
        super().__init__(label, *args, **kwargs)
        self._timer: Timer | None = None
        self.callback = action

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.add_class("press")
        if self._timer is not None:
            self._timer.stop()

        def action_delayed() -> None:
            self.remove_class("press")

        self._timer = self.set_timer(0.1, action_delayed)

        if self.callback is not None:
            self.run_callback_in_background()

    @work(thread=True)
    def run_callback_in_background(self) -> None:
        self.callback()


class NxRadioButton(RadioButton):
    def __init__(self, label: str, callback_arg=None, is_default: bool = False, *args, **kwargs):
        """
        Args:
            label: 보여지는 이름
            callback_arg (Any): 콜백 함수에게 넘겨줄 인수
            is_default (bool): 초기 선택 여부
        """
        super().__init__(label, value=is_default, *args, **kwargs)
        self.callback_arg = callback_arg

    def render(self):
        return self.label

    # 내부 부모 함수 오버리아드로 가로 크기 수정
    def get_content_width(self, container: Size, viewport: Size) -> int:
        return self._label.get_optimal_width(self.styles, 0)


class NxRadioSet(RadioSet):
    DEFAULT_CSS = """
    NxRadioSet {
        layout: horizontal;
        width: auto;
        height: 1;
        border: none;
        padding: 0;
        background: transparent;
        
        &.two-buttons {
            width: 1fr;
        }
        
        &:focus {
            border: none;
        }
        
        & > RadioButton:last-child {
            margin-right: 0;
        }
        
        &.two-buttons NxRadioButton {
            margin-right: 0;
            width: 1fr;
        }
    
        NxRadioButton {
            margin-right: 1;
            width: auto;
            min-width: 1;
            padding: 0 1;
            
            height: 1;
            background: $surface;
            color: $accent 50%;
            text-align: center;
            
            &.-selected { /* 포커스 상태 */
                text-style: bold;
                background: $panel;
            }
            
            &.-on { /* 선택된 상태 */
                background: $accent 10%;
                color: $accent;
                text-style: bold blink;
            }
            
            &:hover {
                background: $panel-darken-2;
                color: $text;
            }
        }
    }"""

    def __init__(self, *args, callback: Callable[[Any], Any] | None = None, **kwargs):
        for arg in args:
            if not isinstance(arg, RadioButton) or type(arg).__name__ != "NxRadioButton":
                raise TypeError(f"NxRadioSet에는 NxRadioButton만 넣을 수 있습니다. 잘못된 타입: {type(arg).__name__}")

        super().__init__(*args, **kwargs)

        self.callback_fn = callback

        if len(args) == 2:
            self.add_class("two-buttons")

    def on_mount(self) -> None:
        self.call_later(self._sync_cursor)

    def _sync_cursor(self) -> None:
        for i, btn in enumerate(self.query(RadioButton)):
            if btn.value:
                self._selected = i
                break

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self._sync_cursor()

        if self.callback_fn and hasattr(event.pressed, "callback_arg"):
            self.app.call_after_refresh(self.callback_fn, event.pressed.callback_arg)


class _LogHighlighter(Highlighter):
    LEVEL_STYLES = {
        "PRINT": "bold blue",
        "FATAL": "bold reverse red",
        "ERROR": "bold reverse red",
        "FAIL": "bold red",
        "WARN": "bold yellow",
        "INFO": "bold cyan",
        "PASS": "bold green",
        "DEBUG": "bold blue dim",
    }

    LEVEL_DIM_STYLES = {
        "PRINT": "blue dim",
        "FATAL": "red dim",
        "ERROR": "red dim",
        "FAIL": "red dim",
        "WARN": "yellow dim",
        "INFO": "cyan dim",
        "PASS": "green dim",
        "DEBUG": "dim",
    }

    LOG_PATTERN = re.compile(r"^(\[[^]]+])\s+([^\s:]+)\s*(:\s*)(.*)$")

    def __init__(self) -> None:
        super().__init__()
        self.last_level: str | None = None

    def highlight(self, text: Text) -> None:
        match = self.LOG_PATTERN.match(text.plain)

        if match:
            text.stylize("dim", *match.span(1))

            raw_level = match.group(2)
            clean_level = raw_level.split(".")[-1].upper()
            self.last_level = clean_level

            # 레벨 고유 스타일 적용 (Group 2)
            level_style = self.LEVEL_STYLES.get(clean_level, "bold")
            text.stylize(level_style, *match.span(2))

            dim_style = self.LEVEL_DIM_STYLES.get(clean_level, "dim")
            text.stylize(dim_style, *match.span(3))

            if clean_level == "FATAL":
                dim_style = self.LEVEL_DIM_STYLES.get(clean_level, "dim")
                text.stylize(dim_style, *match.span(3))
                text.stylize("red", *match.span(4))

            elif clean_level == "DEBUG":
                text.stylize("dim", *match.span(3))
                text.stylize("dim", *match.span(4))

            else:
                dim_style = self.LEVEL_DIM_STYLES.get(clean_level, "dim")
                text.stylize(dim_style, *match.span(3))

        else:
            if self.last_level == "FATAL":
                text.stylize("red", 0, len(text.plain))

            elif self.last_level == "DEBUG":
                text.stylize("dim", 0, len(text.plain))

            pipe_idx = text.plain.find("│")
            if pipe_idx != -1 and self.last_level:
                dim_style = self.LEVEL_DIM_STYLES.get(self.last_level, "dim")
                text.stylize(dim_style, pipe_idx, pipe_idx + 1)


class NxLog(LogWidget):
    """Nexus Log에 최적화 된 특수한 Log 위젯"""

    DEFAULT_CSS = """
        NxLog {
            overflow-x: hidden;
            overflow-y: auto;
            background: $background;
            
            &:focus {
                overflow-x: auto;
            }
            &:dark {
                background: initial;
            }
        }

        """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, highlight=True)
        self.ntp_timer = NtpTimer()
        self.highlighter = _LogHighlighter()

    def write_log(self, log: Log) -> str:
        """Nexus Log를 적절한 문자열로 가공하여 작성합니다.
        Args:
            log (Log): 로그 객체

        Returns:
            str: 가공된 문자열
        """

        real_tf = self.ntp_timer.float_to_str(log.time)
        header = f"[{real_tf}] {log.level.name:<5} : "

        lines = log.msg.split("\n")
        formatted_msg = f"{header}{lines[0]}\n"

        indent = " " * (len(header) - 2) + "│ "
        for line in lines[1:]:
            formatted_msg += f"{indent}{line}\n"
        self.write_line(formatted_msg)
        return formatted_msg


class EmptyWidget(Static):
    """빈공간 디자인용 위젯

    Args:
        label: 가운데 표시할 이름 (None: 표시 안함)

    """

    DEFAULT_CSS = """
    EmptyWidget {
        height: 1fr;
        color: $foreground-muted 50%;
        align: center middle;
        hatch: right $foreground-muted 20%;  
    }
    """

    def __init__(self, label: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        if self.label is not None:
            yield Label(self.label)


class NxDataTable(DataTable):
    DEFAULT_CSS = """
    NxDataTable:dark, DataTable {
        overflow-x: hidden;
        overflow-y: auto;
        color: $text;
        background: initial;
        height: 1fr;
        &:focus {
            overflow-x: auto;
        }
    
    
        /* 헤더 디자인 */
        & > .datatable--header {
            text-style: none;
            background: $primary;
            color: $text;
        }
        & > .datatable--header-hover {
            background: $primary-darken-1;
        }
    
        /* 줄무늬 디자인 */
        & > .datatable--odd-row{}
        & > .datatable--even-row {
            background: $primary 15%;
        }
    
    
        & > .datatable--hover {
            background: $accent 15%;
        }
        & > .datatable--cursor {
            background: $accent 25%;
            color: $text;
            text-style: none;
        }
    
    }
    """

    def on_mount(self):
        self.cursor_type = "row"
        self.zebra_stripes = True
