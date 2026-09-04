# Nexus

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Hyperliquid DEX 자동매매 에이전트 관리 대시보드**

Windows 터미널(TUI) 환경에서 여러 트레이딩 에이전트를 실행·모니터링·관리할 수 있는 대시보드 애플리케이션입니다.
에이전트의 실시간 로그 확인, 시작/중지 제어, 디스코드 웹훅 알림을 하나의 인터페이스에서 제공합니다.

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| **에이전트 관리** | `NEXUS_AGENT/` 폴더의 `.py` 파일을 자동 탐지하여 개별 시작·중지·초기화 |
| **실시간 로그** | 레벨별(FATAL~DEBUG) 컬러 로그 표시 |
| **디스코드 알림** | 웹훅을 통한 상태 모니터링 및 로그 자동 전송 |
| **시스템 모니터** | CPU·RAM 사용량 실시간 표시 |
| **로그 저장** | 시스템/에이전트 로그를 텍스트 파일로 내보내기 |
| **단일 인스턴스** | Windows Mutex 기반 중복 실행 방지 |
| **안전 종료** | 모든 에이전트 프로세스 정리 후 안전 종료 |

---

## 빠른 시작

```bash
# 1. 클론
git clone https://github.com/agradra/manilet-nexus.git
cd manilet-nexus

# 2. 의존성 설치 (uv 필요)
uv sync

# 3. env.toml 작성 (디스코드 웹훅 등)

# 4. 실행
uv run nexus
```

> 자세한 설치·설정·사용법은 [사용자 매뉴얼](docs/user_manual.md)을 참고하세요.

---

## 프로젝트 구조

이 레포는 **uv workspace** 기반 모노레포로, 2개의 패키지를 포함합니다.

```
manilet-nexus/
├── nexus_app/              # 패키지 1: TUI 대시보드 앱
│   ├── nexus_app/
│   │   ├── cli.py          # CLI 진입점
│   │   ├── config.py       # 설정 관리
│   │   └── core/           # UI + 핵심 로직
│   │       ├── nexus_app.py
│   │       ├── style.tcss
│   │       ├── module/
│   │       └── service/
│   └── pyproject.toml
│
├── nexuspy/                # 패키지 2: 에이전트용 SDK
│   ├── nexuspy/
│   │   ├── log.py          # 로그 API
│   │   └── trade_bot/      # HyperLiquid 매매 래퍼
│   └── pyproject.toml
│
├── docs/                   # 문서
├── pyproject.toml          # 워크스페이스 루트
└── uv.lock
```

> 상세 모듈 구조와 설계는 [아키텍처 문서](docs/architecture.md)를 참고하세요.

---

## 에이전트 작성

`NEXUS_AGENT/` 폴더에 `.py` 파일을 생성하면 대시보드에서 자동 인식됩니다.

```python
import nexuspy.log as log

def main():
    log.info("에이전트 시작")
    # 트레이딩 로직 작성
    log.info("에이전트 종료")
```

> 로그 레벨, Config 접근, 실전 예제 등은 [nexuspy 가이드](docs/nexuspy_guide.md)를 참고하세요.

---

## 문서

| 문서 | 설명 |
|---|---|
| [사용자 매뉴얼](docs/user_manual.md) | 설치, 환경설정, 실행, 각 탭 사용법, 트러블슈팅 |
| [nexuspy 가이드](docs/nexuspy_guide.md) | 에이전트 작성법, 로그 API, 실전 예제 |
| [아키텍처](docs/architecture.md) | 내부 모듈 구조, 데이터 흐름, 스레딩 모델, 규칙 (개발용) |
| [Changelog](CHANGELOG.md) | 버전별 변경 이력 |

---

## 기술 스택

| 항목 | 기술 |
|---|---|
| **언어** | Python 3.12+ |
| **TUI** | [Textual](https://textual.textualize.io/) 8.2 |
| **로그** | [Rich](https://rich.readthedocs.io/) 15.0 |
| **모니터** | [psutil](https://psutil.readthedocs.io/) 7.2 |
| **HTTP** | [Requests](https://docs.python-requests.org/) |
| **거래소** | [Hyperliquid](https://hyperliquid.xyz/) DEX |

---

## 기여

기여를 환영합니다! [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요.

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)에 따라 배포됩니다.
