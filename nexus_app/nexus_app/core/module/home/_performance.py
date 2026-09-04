import platform
from collections import deque
from typing import Literal

import psutil
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Rule
from textual.widgets._data_table import ColumnKey

from nexus_app.core.module.base import Pane, NxRadioSet, NxRadioButton, NxDataTable
from nexus_app.core.service.agent import AgentManager
from nexus_app.core.service.db import CryptoDB

_SYSTEM_SHELL_NAMES = frozenset({ # 소문자로 통일
    # Windows
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "explorer.exe",
    "services.exe",
    "conhost.exe",
    "svchost.exe",
    "windowsterminal.exe",
    "mintty.exe",
    "wsl.exe",

    # Linux, macOS
    "bash",
    "zsh",
    "sh",
    "fish",
    "dash",
    "ksh",
    "csh",
    "tcsh",

    # 터미널 멀티플렉서, 가상 환경
    "tmux", "tmux: server", "tmux: client", "screen", "zellij", "byobu",
    # OS 시스템 데몬, 원격 접속
    "systemd", "init", "sshd", "cron", "crond", "launchd",
    # GUI 터미널 에뮬레이터 (리눅스 데스크톱 환경)
    "gnome-terminal-server", "xterm", "konsole", "alacritty", "kitty", "wezterm-gui",
})

# 컬럼 설정
_COL_NAME = Literal["Gen", "PID", "Name", "CPU", "RAM", "Thr"]
_COL_WIDTH: dict[_COL_NAME, int | None] = {
    "Gen": 9,  # [n]Parent , [0]Self, [-n]Child
    "PID": 7,  # 1234567
    "CPU": 10, # ↓ CPU (16)
    "RAM": 10, # 999.99 MiB
    "Thr": 5,  # ↓ Thr
    "Name": None,
} # 반복문 시 _COL_WIDTH 순서를 사용 ex) for name, width in _COL_WIDTH.items():

# 컴퓨터 환경값
_OS_NAME = f"{"macOS" if platform.system() == "Darwin" else platform.system()} {platform.release()}"
_CPU_COUNT = psutil.cpu_count(logical=True)
_RAM_TOTAL = psutil.virtual_memory().total

class PerformancePane(Pane):

    cpu_ram_share: tuple[str,str] = reactive(("", "")) #NxFooter 공유
    agent_mng = AgentManager()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # DB, 초기 설정값
        self.db = CryptoDB("PerformancePane")

        self.sort_col: _COL_NAME = self.db.create("sort_col", "Gen", exist_ok=True)
        self.sort_reverse: bool = self.db.create("sort_reverse", False, exist_ok=True)

        self.cpu_per_core: bool = self.db.create("cpu_per_core", False, exist_ok=True)
        self.ram_as_percent: bool = self.db.create("ram_as_percent", False, exist_ok=True)

        # 프로세스 테이블용
        self.tick_n = 0
        self.col_cache: dict[_COL_NAME, ColumnKey] = {} # 헤더

        self.current_process: psutil.Process = psutil.Process()
        self.parent_proc_cache: list[psutil.Process] = [] # [현재 프로세스 -> 부모 프로세스]
        self.child_proc_cache: dict[int, tuple[int, str, psutil.Process]] = {} # pid : (깊이, 이름, proc)

        self.assign_parent_process()
        self.assign_child_process()

        # 위젯 변수
        self.process_table = NxDataTable(show_cursor=False)
        #self.overview_static = Static() #TODO 다음 버전

    # === view =======================================================================
    DEFAULT_CSS = """
        PerformancePane {
            
            & > #performance-button-bar {
                height: 1;
                & > NxRadioSet { margin-right: 1; }
                & > NxRadioSet:last-child { margin-left: 1; }
            }
        }
        """

    def compose(self) -> ComposeResult:
        with Horizontal(id="performance-button-bar"):
            yield NxRadioSet(NxRadioButton("All-Core", False, is_default=(not self.cpu_per_core)),
                             NxRadioButton("Per-Core", True, is_default=self.cpu_per_core),
                             callback=self.change_cpu_mode)

            yield Rule(orientation="vertical")

            yield NxRadioSet(NxRadioButton("RAM Size", False, is_default=(not self.ram_as_percent)),
                             NxRadioButton("RAM Usage", True, is_default=self.ram_as_percent),
                             callback=self.change_ram_mode)
        yield Rule()
        #yield self.overview_static # TODO: 다음 버전에 업그레이드
        #yield Rule()
        yield self.process_table

    # TODO: gen_overview() 다음 버전에 추가

    def gen_overview(self, load: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
        return
        load = psutil.getloadavg()
        cpu_temps = "(N/A)"
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()

            if temps:
                try:
                    first_sensor_list = list(temps.values())[0]
                    if first_sensor_list:
                        current_temp = first_sensor_list[0].current
                        cpu_temps = f"{current_temp:.1f} °C"
                except (IndexError, AttributeError):
                    pass


        design = f"""System
├╴os: {self.os_str}
├╴load average: {load[0]} (1m) / {load[1]} (5m) / {load[2]} (15m)
├────────────────────────────
└╴CPU
  ├╴usage: {0} %
  ├╴clock {0} MHz
  │  ├╴min: {0} MHz
  │  └╴max: {0} MHz
  └╴temperature: {cpu_temps}
            yield Label(f"Load average:   1.05, 0.70, 0.65")
            yield Label(f"[$primary]CPU[/]:   0 % / 0.0 MHz / 0.0 °C")
            yield Label(f"RAM:   0.0 GiB / {_RAM_TOTAL} GiB (0.0 %)")
            yield Label(f"IO: W 0.0, R")
            yield Label(f"Net: ▴ 0.0MiB / ▾ 0.0 MiB")
        """

        self.overview_static.update(design)

    # ==========================================================================

    def on_mount(self) -> None:
        self.border_title = "Process"
        self.border_subtitle = "1000ms"

        for name, width in _COL_WIDTH.items():
            self.col_cache[name] = self.process_table.add_column( # type: ignore
                label=self.gen_col_label(name), key=name, width=width # type: ignore
            )

        self.tick()
        self.set_interval(1.0, self.tick)


    def gen_col_label(self, col_name: _COL_NAME) -> str:
        if col_name == "CPU":
            col_label = "CPU (1)" if self.cpu_per_core else f"CPU ({_CPU_COUNT or 'N/A'})"

        #elif col_name == "RAM":
            #col_label = "RAM (%)" if self.ram_as_percent else "RAM (MiB)"

        else: col_label = col_name

        if col_name == self.sort_col:
            return f"[bold]{"↑" if self.sort_reverse else "↓"} {col_label}[/]"
        else:
            return f"{col_label}"

    # 이벤트 =============================================================

    def change_cpu_mode(self, mode: bool) -> None:
        self.cpu_per_core = mode
        self.db.update("cpu_per_core", mode)

        self.process_table.columns[self.col_cache["CPU"]].label = self.gen_col_label("CPU")
        self.tick()

    def change_ram_mode(self, mode: bool) -> None:
        self.ram_as_percent = mode
        self.db.update("ram_as_percent", mode)

        self.tick()

    def on_data_table_header_selected(self, event: NxDataTable.HeaderSelected) -> None:
        """컬럼 헤더 클릭 시"""
        event_col: _COL_NAME = event.column_key.value # type: ignore

        if self.sort_col == event_col: # 같은 버튼 -> 정렬 순서 변경
            self.sort_reverse = not self.sort_reverse
            self.db.update("sort_reverse", self.sort_reverse)
        else: # 다른 버튼 -> 정렬 기준 변경
            self.sort_col = event_col
            self.db.update("sort_col", self.sort_col)

        for name, col_key in self.col_cache.items():
            self.process_table.columns[col_key].label = self.gen_col_label(name) # type: ignore

        self.apply_sort()

    # DataTable =====================================================================

    def tick(self) -> None:
        """1초마다 호출: 프로세스 목록 수집 → DataTable 갱신"""

        # TODO: 최적화 더 가능?

        if self.tick_n % 3 == 0:
            self.assign_child_process()
        if self.tick_n % 10 == 0:
            self.assign_parent_process()
        self.tick_n += 1

        cpu_divisor = 1.0 if self.cpu_per_core else (_CPU_COUNT or 1)
        rows: dict[str, tuple] = {}  # { pid → (Gen, Name, PID, CPU, RAM, Thread) }

        # 데이터 문자열
        def _make_row(_proc: psutil.Process, _gen: str, _display_name: str | None = None)\
        -> tuple[str, str, str, str, str, str] | None:

            try:
                with _proc.oneshot():
                    p_id = str(_proc.pid)
                    cpu = f"{_proc.cpu_percent() / cpu_divisor:.2f} %"

                    if self.ram_as_percent:
                        ram_str = f"{_proc.memory_percent():.2f} %"
                    else:
                        ram_str = self.fmt_bytes(_proc.memory_full_info().uss)

                    thr = str(_proc.num_threads())
                    name = _display_name or _proc.name()
            except psutil.Error:
                return None

            return _gen, p_id, cpu, ram_str, thr, name # 순서 주의

        # 현재 프로세스
        row = _make_row(self.current_process, "[0]Self", _display_name="NexusApp")
        if row:
            rows[str(self.current_process.pid)] = row
            self.cpu_ram_share = (row[2], row[3])

        # 부모 프로세스
        for idx, proc in enumerate(self.parent_proc_cache):
            row = _make_row(proc, f"[{idx+1}]Parent")
            if row:
                rows[str(proc.pid)] = row

        # 자식 프로세스
        for pid, (depth, display_name, proc) in list(self.child_proc_cache.items()):
            row = _make_row(proc, f"[-{depth}]Child", display_name)
            if row:
                rows[str(pid)] = row
            else:
                self.child_proc_cache.pop(pid, None)

        # 테이블 업데이트 =======================

        # 현재 테이블에 렌더링되어 있는 기존 row key(PID)들을 Set으로 수집
        existing_keys: set[str] = {str(rk.value) for rk in self.process_table.rows}
        new_keys: set[str] = set(rows.keys())

        # [삭제] 이번 턴(rows)에 없는 프로세스는 죽은 것이므로 테이블에서 제거
        for dead_key in existing_keys - new_keys:
            self.process_table.remove_row(dead_key)

        # (Gen, PID, CPU, RAM, Thread, Name)
        col_order = list(_COL_WIDTH.keys())

        for pid_key, cells in rows.items():
            if pid_key in existing_keys:
                for col_name, value in zip(col_order, cells):
                    self.process_table.update_cell(pid_key, col_name, value, update_width=False)
            else:
                # 새로 생성된 프로세스 -> 새 행(Row) 추가
                self.process_table.add_row(*cells, key=pid_key)

        #self.mini_gen_overview() #TODO
        self.apply_sort()

    def apply_sort(self) -> None:
        """현재 상태에 맞춰 테이블 정렬"""

        def custom_sort_key(value) -> float | int | str:
            val_str = str(value)

            if self.sort_col == "Name":
                return val_str.lower()

            elif self.sort_col in ("PID", "Thr"):
                return float(val_str)

            elif self.sort_col == "RAM":
                if val_str[-1] == "%":
                    return float(val_str[:-2])
                elif val_str[-3] == "M":
                    return float(val_str[:-4])
                else:
                    return float(val_str[:-4]) * 1024

            elif self.sort_col == "CPU":
                return float(val_str[:-2])

            elif self.sort_col == "Gen":
                return int(val_str[1:val_str.index("]")])

            else:
                raise ValueError(f"process table 정렬 정규화 실패 - (sort_col: {self.sort_col})")

        self.process_table.sort(
            self.sort_col,
            key=custom_sort_key,
            reverse=self.sort_reverse
        )


    # 프로세스 수집 =====================================================================

    def assign_parent_process(self) -> None:
        """부모 프로세스 체인을 캐시에 저장

        * 정렬 순서 : [직계 부모(1대) -> 조부모(2대) -> 증조부모(3대) ...]
        """
        chain = []

        for parent in self.current_process.parents():
            try:
                # 범용 쉘이나 시스템 프로세스를 만나면 상위 추적 중단
                if parent.name().lower() in _SYSTEM_SHELL_NAMES:
                    break

                chain.append(parent)

            except psutil.Error:
                break

        self.parent_proc_cache = chain

    def assign_child_process(self) -> None:
        """현재 프로세스의 자식 트리를 탐색하여 {pid: display_name} 딕셔너리 반환

        * agent PID가 포함된 줄기 → 해당 줄기 전체를 agent name으로 통일
        * 한 줄기에 2개 이상의 agent가 존재하거나, agent와 무관한 줄기, 혹은 줄기가 이중으로 갈라지는 줄기 -> 알수없음 으로 표기
        """
        agent_pid_map: dict[int, str] = self.agent_mng.get_agent_pid_map()

        # 모든 자식 프로세스 수집
        try:
            all_children = self.current_process.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.child_proc_cache = {}
            return

        proc_map: dict[int, psutil.Process] = {}
        orig_names: dict[int, str] = {}

        for child in all_children:
            pid = child.pid
            try:
                if pid in self.child_proc_cache:
                    cached_proc = self.child_proc_cache[pid][2]  # (depth, name, proc)에서 proc 꺼내기
                    proc_map[pid] = cached_proc
                    orig_names[pid] = child.name()
                else:
                    child.cpu_percent(interval=None)
                    proc_map[pid] = child
                    orig_names[pid] = child.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 부모-자식 인접 리스트 생성
        children_of: dict[int, list[int]] = {}
        root_pid = self.current_process.pid

        for pid, proc in proc_map.items():
            try:
                ppid = proc.ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                ppid = root_pid

            if ppid not in children_of:
                children_of[ppid] = []
            children_of[ppid].append(pid)

        # 문어 다리 분석 , 새 캐시 생성
        new_child_cache: dict[int, tuple[int, str, psutil.Process]] = {}

        for leg_root_pid in children_of.get(root_pid, []):
            leg_pids: list[tuple[int, int]] = []
            leg_agents: set[str] = set()
            is_abnormal_split = False

            queue = deque([(leg_root_pid, 1)])

            while queue:
                curr_pid, depth = queue.popleft()
                leg_pids.append((curr_pid, depth))

                if curr_pid in agent_pid_map:
                    leg_agents.add(agent_pid_map[curr_pid])

                c_pids = children_of.get(curr_pid, [])

                # 문어 다리 갈라지면 비정상
                if len(c_pids) > 1:
                    is_abnormal_split = True

                for c_pid in c_pids:
                    queue.append((c_pid, depth + 1))

            # 이름 판정
            if is_abnormal_split or len(leg_agents) > 1:
                final_name = "알수없음"
            elif len(leg_agents) == 1:
                # set에서 하나 남은 요소를 에러 없이 꺼냄
                final_name = list(leg_agents)[0]
            else:
                final_name = None

                # 새 캐시에 기록
            for pid, depth in leg_pids:
                proc = proc_map[pid]
                if final_name:
                    new_child_cache[pid] = (depth, final_name, proc)
                else:
                    new_child_cache[pid] = (depth, orig_names.get(pid, "알수없음"), proc)

        self.child_proc_cache = new_child_cache

    @staticmethod
    def fmt_bytes(n: int) -> str:
        """0~999.99MiB는 MiB, 1000MiB 이상은 GiB)"""
        if n < 1024:
            return f"{n}B"

        mib_value = n / (1024 ** 2)

        if mib_value < 1000:
            return f"{mib_value:.2f} MiB"
        else:
            gib_value = n / (1024 ** 3)
            return f"{gib_value:.2f} GiB"




