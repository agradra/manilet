# Nexus Agent 통신 프로토콜

에이전트(`nexuspy`)와 메인 앱(`NexusApp`) 간의 stdout 통신 규격입니다.
모든 통신은 아래의 JSON 포맷을 한 줄(Single-line)로 출력하여 전송합니다.

### 공통 규격 (Envelope)
```json
{
  "type": "{타입명(str)}",
  "payload": "{실제 데이터(dict)}"
}
```
### 1. 로그 데이터 (Log)
* type: "log"
* payload 속성:
  * l (Literal["error", "warn", "info", "debug"]): 로그 심각도 (자세한 내용은 `nexus_app/core/service/log.py` 참고)
  * m (str): 로그 메시지

출력 예시:
```json
{
  "type": "log",
  "payload": {"l": "error",
              "m": "어쩌구저쩌구"}
}
```