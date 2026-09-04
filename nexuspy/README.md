# Nexuspy

**에이전트 설계를 위한 파이썬 SDK**

`nexuspy`는 에이전트 내부에서 사용하는 라이브러리입니다.
에이전트가 Nexus App과 소통하기 위한 로그 API와, HyperLiquid 매매를 위한 래퍼 클래스를 제공합니다.

> 현재 HyperLiquid 매매 기능 미지원

## 설치
```bash
pip install "manilet-nexuspy @ git+https://github.com/agradra/manilet.git#subdirectory=nexuspy"
```
> [빠른 시작](../README.md#빠른-시작)을 이미 진행하였다면 넘어갑니다.

## 간단한 사용 예시

설치 후, 에이전트 파이썬 스크립트에서 아래 예시처럼 작성하여 사용 가능합니다.

```python
import nexuspy.log as log


def main():
    log.info("에이전트가 정상적으로 시작되었습니다.")

    log.error("에러가 발생하였습니다!!!")
```

## 주요 기능

* [**로그 전송 (nexuspy.log)**](./docs/log_guide.md)
* > 하이퍼리퀴드 래퍼(nexuspy.trade_bot) `개발중`


