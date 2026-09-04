from typing import Literal

from rich.cells import cell_len
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.content import Content
from textual.reactive import reactive
from textual.widgets import Input, Rule, Switch

from nexus_app.core.module.base import Pane, NxDataTable, NxRunButton, EmptyWidget
from nexus_app.core.service.agent import AgentStatus, AgentManager, AgentSendMode
from nexus_app.core.service.db import CryptoDB
from nexus_app.core.service.log import SystemLogger, LogLevel

_COL_NAME = Literal["status", "name_etc"]
_COL_WIDTH: dict[_COL_NAME, int] = {
    "status": 3,
    "name_etc": 32,
}
_NAME_ETC_WIDTH: int = _COL_WIDTH["name_etc"]

_STATUS_ICON: dict[AgentStatus, Content]  = {
    AgentStatus.SLEEPING : Content.from_markup("[$foreground dim] ⁃ [/]"),
    AgentStatus.RUNNING : Content.from_markup("[$success-lighten-2] ▶ [/]"),
    AgentStatus.STOPPING : Content.from_markup("[$warning-lighten-2] ▶ [/]"),
    AgentStatus.STOPPED : Content.from_markup("[$error-lighten-2] ◼ [/]"),
}
_AGENT_SEND_MODE_ICON: dict[AgentSendMode, str] = {
    AgentSendMode.NoSend  : "[$foreground dim]Ⓧ[/]",
    AgentSendMode.Send    : "[$foreground dim]Ⓛ[/]",
    AgentSendMode.SendTest: "[$foreground dim]Ⓣ[/]",
}
_NOT_FILE_EXIST_ICON: str = "[$error-lighten-3 bold blink italic]NO FILE[/]"

_IGNORE_CHARS = str.maketrans("", "", " _-")

_SORT_STATUS_PRIORITY = {
    "▶": 0,
    "◼": 1,
    "⁃": 2
}

class AgentListPane(Pane):

    # 공유 데이터
    now_agent_name: str | None = reactive(None)

    BINDINGS = [
        Binding("up", "cursor_up", "에이전트 선택 위로 이동", priority=True),
        Binding("down", "cursor_down", "에이전트 선택 아래로 이동", priority=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sys_logger = SystemLogger()
        self.agent_mng = AgentManager()
        self.db = CryptoDB("AgentListPane")

        self.is_sort_status: bool = self.db.create("is_sort_status", False, exist_ok=True)

        # 위젯
        self.search_agent_input = Input(placeholder="Search agent", id="search_agent_input")
        self.sort_status_switch = Switch(id="sort_status_switch", value=self.is_sort_status)

        self.empty_widget = EmptyWidget("No agent",id="table_container")
        self.agent_table = NxDataTable(show_header=False, cursor_foreground_priority="renderable")
        self.agent_table.cell_padding = 0

        self.agent_dir_input = Input(str(self.agent_mng.agents_dir_path or ""), placeholder="Agents directory path", id="agent_dir_input")

        # 캐쉬
        self.col_keys = {}
        self.row_keys = []

    # === view =======================================================================

    DEFAULT_CSS = """
    AgentListPane {
        width: 40;
        max-width: 40;
        min-width: 40;
        
        & > NxDataTable {
            overflow-x: hidden;
            &:focus {
                overflow-x: hidden;
            }
        }
            
        & > Horizontal {
            height: 1;
            
            & > Input {
                width: 1fr;
                margin-right: 1;
            }
            & > Switch {
                margin-left: 1;
            }
        }
    }
    
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield self.search_agent_input
            yield Rule(orientation="vertical")
            yield self.sort_status_switch
        yield Rule()

        yield self.empty_widget
        yield self.agent_table

        yield Rule()
        with Horizontal():
            yield self.agent_dir_input
            yield NxRunButton("Reload", self.click_reload_button)

    def on_mount(self):
        self.border_title = "Agents"

        for name, width in _COL_WIDTH.items():
            self.col_keys[name] = self.agent_table.add_column(label=name, width=width)

        self._refresh_table()
        self.set_interval(0.5, self._refresh_table)

    # 이벤트 ============================================================================================================

    # 위아래 화살표키 전부 DataTable로 몰빵
    def action_cursor_up(self) -> None:
        self.agent_table.action_cursor_up()

    def action_cursor_down(self) -> None:
        self.agent_table.action_cursor_down()

    @on(Switch.Changed, "#sort_status_switch")
    def change_sort_status_switch(self, event: Switch.Changed):
        self.is_sort_status = event.value
        self.db.update("is_sort_status", event.value)
        self._refresh_table()

    @on(Input.Submitted, "#agent_dir_input")
    def enter_agent_dir_input(self, event: Input.Submitted) -> None:
        new_path: str = event.value.strip()
        old_path: str = str(self.agent_mng.agents_dir_path or "")

        if new_path == old_path: # 같으면 리턴
            return

        if not new_path: # 비었으면 리턴
            self.sys_logger.emit(LogLevel.FAIL, f"에이전트 폴더 경로를 입력해 주세요.")
            event.input.value = old_path
            self.agent_dir_input.action_end()
            return

        self.agent_mng.set_agents_dir(new_path)
        changed_path = str(self.agent_mng.agents_dir_path or "")
        event.input.value = changed_path
        event.input.action_end()

        if changed_path != old_path:
            self.screen.set_focus(None)
            self.focus()

        self._refresh_table()

    def click_reload_button(self):
        self.agent_mng.reload_agents()
        self._refresh_table()

    @on(NxDataTable.RowHighlighted)
    @on(NxDataTable.RowSelected)
    def agent_table_focus(self, event: NxDataTable.RowHighlighted | NxDataTable.RowSelected) -> None:
        """테이블 커서가 위아래로 움직여서 새로운 에이전트가 포커스 되었을 때"""
        if event.row_key:
            self.now_agent_name = event.row_key.value
        else:
            self.now_agent_name = None
        self.border_subtitle = self.now_agent_name

    # ==================================================================================================================

    def _refresh_table(self) -> None:
        # TODO: 정렬, 캐싱, 폴더 변경 및 검색, 포커스에 따른 self.now_agent_name값 수정 최적화 필요 (일단 지금 버그는 없음)

        search_txt = self.search_agent_input.value.lower().translate(_IGNORE_CHARS)
        # 검색어 필터
        filtered_agents = []
        for agent in self.agent_mng.get_agent_list():
            if search_txt and search_txt not in agent.name.lower().translate(_IGNORE_CHARS):
                continue
            filtered_agents.append(agent)

        if self.is_sort_status: # 상태순 -> 이름순 정렬
            filtered_agents.sort(
                key=lambda a: (
                    _SORT_STATUS_PRIORITY.get(str(_STATUS_ICON.get(a.status, "").plain).strip(), 99),
                    a.name
                )
            )
        else: # 이름순 정렬
            filtered_agents.sort(key=lambda a: a.name)

        # 화면 표시
        if not filtered_agents:
            self.empty_widget.display = True
            self.agent_table.display = False
            self.row_keys = []
            self.now_agent_name = None
            self.agent_table.clear()
            return
        else:
            self.empty_widget.display = False
            self.agent_table.display = True

        # 테이블 업데이트
        new_row_keys = [a.name for a in filtered_agents]
        current_keys_set = set(self.row_keys)
        new_keys_set = set(new_row_keys)

        for removed_key in (current_keys_set - new_keys_set):
            self.agent_table.remove_row(removed_key)

        status_col_key = self.col_keys["status"]
        name_etc_col_key = self.col_keys["name_etc"]

        for agent in filtered_agents:
            status_content = _STATUS_ICON.get(agent.status, _STATUS_ICON[AgentStatus.SLEEPING])

            etc_markup = " " + _AGENT_SEND_MODE_ICON[agent.send_mode] + " "
            if not agent.is_file_exist:
                etc_markup += _NOT_FILE_EXIST_ICON + " "

            etc_len = Content.from_markup(etc_markup).cell_length

            name_allow_width = _NAME_ETC_WIDTH - etc_len

            display_name = agent.name
            if cell_len(display_name) > name_allow_width:
                cur_len = 0
                trunc = ""
                for char in display_name:
                    cl = cell_len(char)
                    if cur_len + cl > name_allow_width -1:
                        break
                    trunc += char
                    cur_len += cl
                display_name = trunc + "+"

            info_str = Content.from_markup(f"{display_name} {etc_markup}")

            if agent.name not in current_keys_set:
                self.agent_table.add_row(status_content, info_str, key=agent.name)
            else:
                self.agent_table.update_cell(agent.name, status_col_key, status_content)
                self.agent_table.update_cell(agent.name, name_etc_col_key, info_str)

        if self.row_keys != new_row_keys:
            def sort_content(cell_values):
                if isinstance(cell_values, tuple):  # status 정렬 모드
                    status_val, name_val = cell_values

                    status_plain = str(status_val.plain).strip()
                    name_plain = str(name_val.plain).strip()

                    return _SORT_STATUS_PRIORITY.get(status_plain, 99), name_plain

                else: # 이름 모드
                    name_plain = str(cell_values.plain).strip()
                    return name_plain

            if self.is_sort_status:
                self.agent_table.sort(status_col_key, name_etc_col_key, key=sort_content)
            else:
                self.agent_table.sort(name_etc_col_key, key=sort_content)

            self.row_keys = new_row_keys


        self.now_agent_name =  str(self.get_current_row_data()).strip()
        self.border_subtitle = self.now_agent_name


    def get_current_row_data(self) -> list:
        """현재 DataTable의 커서가 위치한 행의 모든 셀 데이터를 가져옵니다."""
        cursor_coord = self.agent_table.cursor_coordinate
        row_key, _ = self.agent_table.coordinate_to_cell_key(cursor_coord)
        return row_key.value
