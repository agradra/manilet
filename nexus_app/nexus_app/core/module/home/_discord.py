from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label, Rule

from nexus_app.core.module.base import NxRadioButton, NxRadioSet, Pane
from nexus_app.core.service.discord import DChannel, Discord, DMode


class _DiscordInput(Input):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_value: str = self.value if self.value else ""

    # 엔터 눌렀을 떄
    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_value = event.value.strip()

        if self.old_value != new_value:
            self.old_value = new_value
            self.value = new_value

        self.screen.set_focus(self.parent)

    # 포커스 풀렸을 때
    def on_blur(self) -> None:
        self.value = self.old_value


_CONNECT_BAD_TEXT = "[$panel]▐[/][$error blink on $panel]●[/][$panel]▌[/]"
_CONNECT_GOOD_TEXT = "[$panel]▐[/][$success blink on $panel]●[/][$panel]▌[/]"


class DiscordPane(Pane):
    DEFAULT_CSS = """
    DiscordPane{
        max-height: 10;
        .discord_top_label{
            margin-right: 3;
        }
        
        #discord-connect {
            dock: right;
        }
    }
    
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Discord"

        self.discord = Discord()

        self.connect_label = Label(_CONNECT_BAD_TEXT, id="discord-connect")
        self.radio_set = NxRadioSet(
            callback=self.discord.change_mode,
            *(
                NxRadioButton(
                    label=item.name.capitalize(),
                    callback_arg=item,  # DMode 객체를 통째로 넣음
                    is_default=(item == self.discord.mode),
                )
                for item in DMode
            ),
        )

        self.status_url = self.discord.get_url(DChannel.STATUS)
        self.log_url = self.discord.get_url(DChannel.LOG)
        self.test_url = self.discord.get_url(DChannel.TEST)

    def on_mount(self):
        self.set_interval(0.5, self.tick_connect_label)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Mode:", classes="discord_top_label")
            yield self.radio_set
            yield self.connect_label

        yield Rule()

        yield Label("Status channel")
        yield _DiscordInput(value=self.status_url, id="status-channel-input", classes="discord_input")

        yield Label("Log channel")
        yield _DiscordInput(value=self.log_url, id="log-channel-input", classes="discord_input")

        yield Label("Test log channel")
        yield _DiscordInput(value=self.test_url, id="test-channel-input", classes="discord_input")

    @on(Input.Submitted, ".discord_input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        clean_value = event.input.value.strip()
        if input_id:
            match input_id:
                case "status-channel-input":
                    if self.status_url != clean_value:
                        self.status_url = clean_value
                        self.discord.update_url(DChannel.STATUS, clean_value)
                case "log-channel-input":
                    if self.log_url != clean_value:
                        self.log_url = clean_value
                        self.discord.update_url(DChannel.LOG, clean_value)
                case "test-channel-input":
                    if self.test_url != clean_value:
                        self.test_url = clean_value
                        self.discord.update_url(DChannel.TEST, clean_value)
                case _:
                    raise ValueError("불가능한 id 감지")

    def rs_mode_change(self, mode: DMode) -> None:
        self.discord.change_mode(mode)

    def tick_connect_label(self):
        if self.discord.is_connect:
            self.connect_label.update(_CONNECT_GOOD_TEXT)
        else:
            self.connect_label.update(_CONNECT_BAD_TEXT)
