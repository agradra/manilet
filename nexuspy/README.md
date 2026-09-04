# nexus-sdk (nexuspy)

**Nexus 에이전트 설계용 Python SDK**

Nexus 대시보드와 연동되는 트레이딩 에이전트를 작성할 때 사용하는 라이브러리입니다.

## 설치

```bash
pip install git+https://github.com/agradra/manilet-nexus.git#subdirectory=nexuspy
```

## 사용 예시

```python
import nexuspy.log as log

def main():
    log.info("에이전트 시작")
    # 트레이딩 로직 작성
    log.info("에이전트 종료")
```

## 포함 모듈

| 모듈 | 설명 |
|---|---|
| `nexuspy.log` | 에이전트용 로그 API (`error`, `warn`, `info`, `debug`) |
| `nexuspy.trade_bot` | HyperLiquid DEX 매매 래퍼 |

> 자세한 API 문서는 [nexuspy 가이드](../docs/nexuspy_guide.md)를 참고하세요.

## 라이선스

[MIT](../LICENSE)
