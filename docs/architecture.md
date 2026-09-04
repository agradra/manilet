# 아키텍처 (개발 문서)

이 문서는 Nexus 프로젝트의 내부 구조, 설계 결정, 규칙 등을 정리한 **개발자 전용** 문서입니다.

---

## 1. 모듈 구조

```
src/
├── __init__.py
├── main.py                         # 진입점
├── common/                         # 공용 모듈 (전역 상수, 설정, 유틸)
│   ├── __init__.py                 # _const.*, Config 재export
│   ├── _const.py                   # Const, Util, LogLevel, LogStream, Log, AgentStatus, Agent
│   └── _config.py                  # _Config → Config 싱글턴 (env.toml 파싱)
└── core/                           # 핵심 앱 로직 + UI
    ├── __init__.py
    ├── nexus_app.py                # NexusApp (Textual App 서브클래스)
    ├── base.py                     # 공용 위젯 (MyButton, ClockLabel, BaseTab)
    ├── style.tcss                  # Textual CSS
    ├── discord.py                  # Discord 웹훅 관리
    ├── _agent_runner.py            # 에이전트 서브프로세스 러너 (__main__ 진입점)
    └── tab/
        ├── __init__.py             # AgentTab, HomeTab 재export
        ├── agent/
        │   ├── __init__.py         # AgentTab 재export
        │   ├── _agent_model.py     # AgentModel (에이전트 생명주기 관리)
        │   └── _agent_tab.py       # AgentTab, AgentList, AgentItem (UI)
        └── home/
            ├── __init__.py         # HomeTab 재export
            └── _home_tab.py        # HomeTab (시스템 로그 + 성능 모니터 UI)
```

---

## 2. 네이밍 규칙

| 대상 | 규칙 | 예시 |
|---|---|---|
| 비공개 모듈 | `_` 접두사 | `_const.py`, `_config.py`, `_agent_model.py` |
| 공개 모듈 | 접두사 없음 | `discord.py`, `base.py` |
| `__init__.py` | 하위 모듈의 공개 클래스를 재export | `from ._agent_tab import AgentTab` |
| 상수 클래스 | PascalCase | `Const`, `Util` |
| 데이터클래스 | PascalCase | `Log`, `Agent` |
| Enum | PascalCase + UPPER_SNAKE 멤버 | `LogLevel.FATAL`, `AgentStatus.RUNNING` |
| 비공개 메서드 | `_` 접두사 | `_agent_lifecycle()`, `_send_status()` |

---

## 3. 임포트 규칙

프로젝트에서 두 가지 임포트 패턴이 사용됩니다:

### bat에서 실행되는 코드 (src 내부)

`PYTHONPATH`가 프로젝트 루트로 설정되므로 아래 두 방식 모두 동작합니다:

```python
# 절대 경로 (src. 접두사 포함)
from nexus.common import Config, Util

# 축약 경로 (src. 생략) — Textual이 내부적으로 이 방식 사용
from common import Config, Util
from core.base import MyButton
```

> ⚠️ 현재 코드에서 두 방식이 혼용되고 있습니다. `base.py`는 `from src.common import Util`을 사용하고, `nexus_app.py`는 `from common import Const`를 사용합니다.

### 에이전트 코드 (NEXUS_AGENT 내부)

`_agent_runner.py`가 서브프로세스로 에이전트를 실행하며, 동일한 `PYTHONPATH` 환경을 상속받습니다:

```python
import nexuspy.log as log
from nexus.common import Config
```

---

## 4. 핵심 데이터 흐름

### 에이전트 로그 파이프라인

```
에이전트 프로세스                    대시보드 프로세스
┌──────────────────┐             ┌─────────────────────────────────────┐
│ nexuspy.log.info │             │                                     │
│       ↓          │             │  _agent_lifecycle (Thread)          │
│ LogStream.send() │  stdout     │       ↓                             │
│       ↓          │ ════════>   │  LogStream.read()                   │
│ JSON → print()   │   pipe      │       ↓                             │
│                  │             │  agent.logs (deque)                 │
│                  │             │  agent.discord_buffer (Queue)       │
│                  │             │       ↓                ↓            │
│                  │             │  AgentTab.update_view  Discord      │
│                  │             │  (0.3초 간격 폴링)     (3.5초 간격)  │
└──────────────────┘             └─────────────────────────────────────┘
```

### 시스템 로그 파이프라인

```
AgentModel / Discord 등         NexusApp              HomeTab
┌──────────────────┐          ┌──────────┐          ┌─────────────────┐
│ put_sys_log(msg)  │ ──────> │ sys_log_q │ ──────> │ consume_logs()  │
│ (콜백 함수)       │         │ (asyncio  │         │ (Textual @work) │
│                  │          │  Queue)   │         │    ↓             │
│                  │          │           │         │ RichLog에 출력    │
└──────────────────┘          └──────────┘          └─────────────────┘
```

---

## 5. 스레딩 모델

Nexus는 Textual의 asyncio 이벤트 루프 + 다수의 백그라운드 스레드로 구성됩니다.

### 메인 스레드

- Textual의 asyncio 이벤트 루프 (UI 렌더링, 이벤트 처리)
- `HomeTab.consume_logs()` — `@work` 데코레이터로 비동기 실행

### 백그라운드 스레드 (daemon)

| 스레드 | 생성 위치 | 역할 |
|---|---|---|
| `_agent_lifecycle` | `AgentModel.start_agent()` | 에이전트별 stdout 읽기 + 로그 수집 |
| `kill_and_wait` | `AgentModel.stop_agent()` | 에이전트 종료 시그널 + 타임아웃 감시 |
| `discord-update` | `Discord.__init__()` | 디스코드 웹훅 전송 루프 (3초 딜레이 후 시작) |

### 동기화

- `AgentModel.lock` (`threading.Lock`): `agent_dict` 접근 시 사용
- `Agent.discord_buffer` (`queue.Queue`): 에이전트별 디스코드 전송 대기 로그 큐

---

## 6. 클래스 관계도

```
NexusApp (Textual App)
├── sys_log_q: asyncio.Queue[Log]
├── HomeTab (BaseTab)
│   ├── RichLog (시스템 로그 뷰어)
│   ├── Label (성능 모니터)
│   └── consume_logs() — sys_log_q 소비
│
└── AgentTab (BaseTab)
    ├── AgentList (Vertical)
    │   ├── ListView
    │   │   └── AgentItem (ListItem) × N
    │   └── Disk Refresh 버튼
    │
    ├── AgentModel (비즈니스 로직)
    │   ├── agent_dict: dict[str, Agent]
    │   ├── lock: threading.Lock
    │   ├── Discord
    │   │   └── _update_loop() 스레드
    │   ├── start_agent() → _agent_lifecycle 스레드
    │   ├── stop_agent() → kill_and_wait 스레드
    │   └── kill() — atexit 등록
    │
    ├── RichLog (에이전트 로그 뷰어)
    └── 제어 버튼 (Start, Stop, Clear, Save Log)
```

---

## 7. 에이전트 상태 머신

```
          start_agent()              stop_agent()
SLEEPING ────────────> RUNNING ────────────> STOPPING
    ↑                     │                     │
    │                     │ (프로세스 자체 종료)   │ (시그널 후 프로세스 종료)
    │                     ↓                     ↓
    │               ┌─ STOPPED ←────────────────┘
    │               │
    └───────────────┘
        clear_agent()
```

| 상태 | 값 | 의미 |
|---|---|---|
| `SLEEPING` | 0 | 대기 중. 실행 가능 |
| `RUNNING` | 1 | 서브프로세스 실행 중 |
| `STOPPING` | 2 | 종료 시그널 전송됨. 프로세스 종료 대기 |
| `STOPPED` | 3 | 프로세스 종료 완료. 로그 보존 중 |

---

## 8. 주요 데이터 클래스

### Agent (`_const.py`)

```python
@dataclass
class Agent:
    name: str                                              # 에이전트 이름 (파일명 stem)
    status: AgentStatus = AgentStatus.SLEEPING              # 현재 상태
    file_exist: bool = True                                 # 디스크에 파일 존재 여부
    process: Optional[subprocess.Popen] = None              # 서브프로세스 핸들
    start_time: str | None = None                           # 시작 시각 문자열
    end_time: str | None = None                             # 종료 시각 문자열
    logs: deque[Log] = field(default_factory=lambda: deque(maxlen=1000))  # 로그 링버퍼
    is_discord_test: bool = False                           # 테스트 모드 여부
    discord_buffer: Queue[Log] = field(default_factory=Queue)  # 디스코드 전송 대기 큐
```

### Log (`_const.py`)

```python
@dataclass
class Log:
    msg: str                                    # 로그 메시지
    level: LogLevel = LogLevel.PRINT            # 로그 레벨
    time: str = field(default_factory=Util.get_time_str)  # 타임스탬프
```

---

## 9. Config 싱글턴 (`_config.py`)

`_Config` 클래스가 모듈 레벨에서 인스턴스화되어 `Config`로 제공됩니다.

```python
Config = _Config()  # 모듈 import 시 즉시 실행
```

- `from src.common import *` 호출 시 `_const.py`와 `_config.py`가 로드됩니다.
- `_Config.__init__()`에서 `env.toml` 파싱 실패 시 `ConfigError`가 발생하며, `main.py`의 최상위 try-except에서 잡힙니다.

### 경로 해석

```python
base_path = Path(__file__).resolve().parent.parent.parent  # 프로젝트 루트
# _config.py → common/ → src/ → Nexus/ (3단계 상위)
```

---

## 10. Textual UI 구조

### 탭 시스템

`NexusApp.TABS` 리스트에 탭 이름과 클래스를 등록합니다:

```python
TABS = [
    {"name": "Home", "class": HomeTab},
    {"name": "Agent", "class": AgentTab},
]
```

- `Tabs` + `ContentSwitcher` 조합으로 탭 전환 구현
- 각 탭은 `BaseTab`을 상속하며, `on_show()`/`on_hide()`에서 타이머를 자동 관리

### BaseTab

```python
class BaseTab(Widget):
    can_focus = True
    
    def on_show(self):   # 탭 활성화 시 타이머 resume
    def on_hide(self):   # 탭 비활성화 시 타이머 pause
```

탭 전환 시 불필요한 폴링을 방지하여 CPU 사용량을 절감합니다.

### 스타일 (`style.tcss`)

- 글로벌 스타일은 `style.tcss`에 정의
- Textual 변수 (`$background`, `$accent` 등) 활용
- 탭별 커스텀 스타일은 TCSS 셀렉터로 분리

---

## 11. 디스코드 모듈 (`discord.py`)

### 메시지 전략

| 채널 | HTTP 메서드 | 방식 |
|---|---|---|
| STATUS | POST (최초) → PATCH (이후) | 단일 메시지 실시간 갱신. 404 시 자동 재생성 |
| LOG | POST | 로그 일괄 전송 (3.5초 간격) |
| TEST | POST | 테스트 로그 일괄 전송 (3.5초 간격) |

### 에러 핸들링

- API 에러 시 `is_connect = False` 설정 + 시스템 로그 기록
- 스레드 내 예외 발생 시 10초 대기 후 재시도
- Timeout(5초) 시 재시도 로직

### 종료 처리

`kill()` 호출 시 `_off_status()`로 STATUS 메시지를 DELETE한 뒤 루프 종료.
