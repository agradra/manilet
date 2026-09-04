# nexuspy 가이드

`nexuspy`는 Nexus 에이전트 내부에서 사용하는 라이브러리입니다.
에이전트가 대시보드와 소통하기 위한 로그 API와, HyperLiquid DEX 매매를 위한 래퍼 클래스를 제공합니다.

---

## 1. 에이전트 기본 구조

`NEXUS_AGENT/` 폴더에 `.py` 파일을 생성하면 대시보드에서 자동으로 인식됩니다.

### 규칙

- 파일에 반드시 `def main():` 함수가 있어야 합니다.
- `main()` 함수가 없으면 `FATAL` 로그와 함께 즉시 종료됩니다.
- 에이전트는 대시보드와 별도의 서브프로세스에서 실행됩니다.
- `KeyboardInterrupt` 예외는 에이전트 러너가 자동으로 잡아 정상 종료 처리합니다.
- 기타 예외 발생 시 traceback이 `FATAL` 로그로 기록됩니다.

### 최소 예제

```python
import nexuspy.log as log

def main():
    log.info("에이전트가 시작되었습니다.")
    
    # 여기에 트레이딩 로직 작성
    
    log.info("에이전트가 종료되었습니다.")
```

---

## 2. nexuspy.log

대시보드 로그 뷰어와 디스코드로 메시지를 전송하는 로그 API입니다.

### 함수

```python
import nexuspy.log as log

log.error("에러 메시지")    # LogLevel.ERROR (-2)
log.warn("경고 메시지")     # LogLevel.WARN  (-1)
log.info("정보 메시지")     # LogLevel.INFO   (0)
log.debug("디버그 메시지")  # LogLevel.DEBUG  (1)
```

### 로그 레벨 상세

| 레벨 | 값 | 색상 | 용도 |
|---|---|---|---|
| `FATAL` | -3 | 빨강(반전) | 에이전트 러너가 자동 사용 (직접 호출 불가) |
| `ERROR` | -2 | 빨강 | 복구 불가능한 에러 |
| `WARN` | -1 | 노랑 | 주의가 필요한 상황 |
| `INFO` | 0 | 시안 | 일반 정보 (매매 신호, 상태 변경 등) |
| `DEBUG` | 1 | 초록 | 디버그용 상세 정보 |
| `PRINT` | 2 | 파랑 | 에이전트 내 `print()` 출력이 자동 변환됨 |

### 동작 원리

`log.info("메시지")` 호출 시 내부적으로 아래와 같은 JSON이 stdout으로 출력됩니다:

```json
{"l": 0, "m": "메시지", "t": "2026-06-28 PM 05:30:00"}
```

대시보드의 `_agent_lifecycle`이 이 stdout을 파이프로 읽어 `LogStream.read()`로 파싱합니다.
JSON이 아닌 일반 `print()` 출력은 `PRINT` 레벨로 자동 변환됩니다.

> 💡 에이전트 내에서 `print()`를 사용해도 로그에 표시되지만, 레벨 분류를 위해 `nexuspy.log`를 사용하는 것을 권장합니다.

---

## 3. Config 접근

에이전트 내에서 `env.toml`의 설정에 접근할 수 있습니다.

```python
from nexus.common import Config

# 지갑 정보 가져오기
wallet = Config.WALLET("my_wallet")
secret_key = wallet["SECRET_KEY"]
address = wallet["ADDRESS"]

# 경로 접근
project_root = Config.PATH.PROJECT   # 프로젝트 루트 Path
agent_dir = Config.PATH.AGENT        # NEXUS_AGENT/ 폴더 Path
log_dir = Config.PATH.LOGS           # LOGS/ 폴더 Path
```

---

## 4. 실전 에이전트 예제

### 주기적으로 동작하는 에이전트

```python
import time
import nexuspy.log as log

def main():
    log.info("모니터링 에이전트 시작")
    
    while True:
        try:
            # === 여기에 분석/매매 로직 ===
            log.debug("사이클 1회 완료")
            time.sleep(60)
            
        except KeyboardInterrupt:
            log.info("종료 신호 수신")
            break
        
        except Exception as e:
            log.error(f"예상치 못한 에러: {e}")
            time.sleep(10)  # 에러 시 대기 후 재시도
    
    log.info("모니터링 에이전트 종료")
```

### HyperLiquid 매매 에이전트 (참고용)

> ⚠️ `nexuspy.trade_bot`은 현재 개발 중이며, 아직 미완성 상태입니다.

```python
import nexuspy.log as log
# from nexuspy.trade_bot import HyperLiquid  # 개발 완료 후 사용 가능

def main():
    log.info("매매 에이전트 시작")
    
    # HyperLiquid 인스턴스 초기화 (예정)
    # hl = HyperLiquid(coin_name="ETH", leverage=5, balance=100.0)
    
    # 매매 로직 (예정)
    # hl.open_long(ratio=0.5)
    # hl.close()
    
    log.info("매매 에이전트 종료")
```

---

## 5. 주의사항

- **프로세스 분리**: 에이전트는 대시보드와 별도 프로세스에서 실행됩니다. 대시보드 내부 객체에 직접 접근할 수 없습니다.
- **안전 종료**: 대시보드에서 Stop 버튼 클릭 시 `CTRL_BREAK_EVENT` → `KeyboardInterrupt`가 발생합니다. `while True` 루프에서 이를 잡아 리소스를 정리하세요.
- **로그 최대 라인**: 에이전트당 최대 1,000줄의 로그가 메모리에 유지됩니다 (`deque(maxlen=1000)`). 대시보드 로그 뷰어는 500줄까지 표시합니다.
- **디스코드 전송 간격**: 로그는 약 3.5초 간격으로 일괄 전송됩니다. 실시간이 아닌 배치 전송입니다.
- **PYTHONPATH**: bat 파일이 `PYTHONPATH`를 프로젝트 루트로 설정하므로, 에이전트 내에서 `from src.common import ...` 또는 `import nexuspy` 등의 임포트가 가능합니다.
