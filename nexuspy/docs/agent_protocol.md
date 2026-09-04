# 출력 프로토콜

에이전트(`nexuspy`)와 메인 앱(`Nenxus_app`) 간의 stdout 출력 규격입니다. 모든 통신은 아래의 JSON 포맷을 한 줄(Single-line)로 출력합니다. 관련 코드는 각 패키지의 `stream.py`(또는 `_stream.py`)에서 구현합니다.

### 공통 규격 (Envelope)
```json
{
  "type": "{타입명(str)}",
  "payload": "{실제 데이터(dict)}"
}
```
### 1. 로그 데이터 (Log)
* `type` (str): `"log"`
* `payload` 속성:
  * `l` (Literal["error", "warn", "info", "debug"]): 로그 심각도 (자세한 내용은 `nexus_app/core/service/log.py` 참고)
  * `m` (str): 로그 메시지

**출력 예시:**
```json
{
  "type": "log",
  "payload": {"l": "error",
              "m": "어쩌구저쩌구"}
}
```