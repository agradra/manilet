from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class QuitModal(ModalScreen[bool]):
    """Ctrl+Q 눌렀을 때 나타나는 종료 확인 모달"""

    DEFAULT_CSS = """
    QuitModal {
        align: center middle;
    
        Container {
            padding: 1 2;
            width: 44;
            height: 11;
            border: round $accent;
            align: center middle;
        }
    
        Label {
            color: $foreground;
            text-style: bold;
            text-align: center;
            width: 100%;
            height: 1fr;
            content-align: center middle;
        }
    
        Horizontal {
            width: 100%;
            height: auto;
            align: center middle;
        }
    }
    """

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("정말 앱을 종료하시겠습니까?", id="question")
            with Horizontal():
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Exit", id="exit", variant="error")

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        if event.button.id == "exit":
            self.dismiss(True)
        else:
            self.dismiss(False)
