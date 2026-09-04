# Changelog

이 파일은 Nexus 프로젝트의 모든 주요 변경 사항을 기록합니다.
이 포맷은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 표준을 따르며, 유의적 버전(Semantic Versioning)을 준수합니다.

## [Unreleased] - (다음 버전에 추가될 예정인 기능들)
- 로그창을 RichLog에서 Log로 변환 및 하이라이트 생성으로 최적화
- 기타 미완성 디자인(tcss) 완성
- wallet 탭 추가
- V 디스코드 클래스 업그레이드
- home 탭에서 전반적으로 에이전트 보기 가능
- 단축키 기능 여러 추가
- nexuspy.hyperliquid 완벽 제공
---

## [0.1.0] - 2026-06-26
### Added
- **대시보드 앱 (`src/`)**: Textual 기반 터미널 UI 애플리케이션 구현
  - Home 탭: 시스템 로그 뷰어, CPU/RAM 실시간 모니터, 로그 리셋 및 내보내기
  - Agent 탭: 에이전트 리스트뷰, 실시간 로그 뷰어, 시작/중지/초기화/로그 저장 버튼
  - 상단바: 앱 이름, 버전, 탭 네비게이션, 실시간 시계
  - Textual CSS 기반 스타일링 (`style.tcss`)
- **에이전트 관리 시스템 (`_agent_model.py`)**
  - `NEXUS_AGENT/` 폴더의 `.py` 파일 자동 탐지 및 동기화 (`reset_agent_dict`)
  - 에이전트를 서브프로세스로 실행 (`subprocess.Popen`) 및 생명주기 관리
  - stdout 파이프를 통한 JSON 기반 로그 스트림 수집 (`_agent_lifecycle`)
  - 에이전트 상태 관리: SLEEPING → RUNNING → STOPPING → STOPPED
  - 에이전트 로그를 텍스트 파일로 저장 (`generate_log_file`)
  - 종료 시 전체 에이전트 프로세스 강제 종료 (`atexit`)
- **에이전트 러너 (`_agent_runner.py`)**: `importlib`로 에이전트 `.py` 파일을 동적 로드 후 `main()` 실행
- **디스코드 연동 (`discord.py`)**
  - 에이전트 상태 모니터링 메시지 (단일 메시지 PATCH 방식으로 실시간 갱신)
  - 에이전트 로그 자동 전송 (운영/테스트 채널 분리)
  - 연결 끊김 감지 및 자동 재시도
  - 앱 종료 시 상태 메시지 자동 삭제
- **공용 모듈 (`src/common/`)**
  - `Const`: 앱 이름, 버전
  - `Util`: 한국 시간 포맷팅 (`Asia/Seoul`), ANSI 컬러 출력
  - `LogLevel` (FATAL~PRINT), `LogStream` (JSON 직렬화/역직렬화), `Log` 데이터클래스
  - `AgentStatus`, `Agent` 데이터클래스
  - `Config`: `env.toml` 파싱 (디스코드 웹훅, 지갑 설정)
- **진입점 (`main.py`)**
  - ASCII 아트 배너 출력
  - Windows Mutex 기반 단일 인스턴스 보장 및 기존 창 포커스 복원
  - 콘솔 X 버튼 안전 종료 핸들러 (`SetConsoleCtrlHandler`)
  - `--from-bat` 인자 검증 (bat 파일 이외 실행 차단)
- **nexuspy 라이브러리**
  - `nexuspy.log`: 에이전트용 로그 API (`error`, `warn`, `info`, `debug`)
  - `nexuspy.trade_bot`: HyperLiquid DEX 매매 래퍼 (`HyperLiquid` 클래스, `WsMaster` 웹소켓 관리) — 일부 미완성
  - `nexuspy.trade_bot_beta`: 베타 버전 매매 래퍼 — 일부 미완성
- **실행 스크립트**: `start.bat` (일반 실행), `dev.bat` (Textual 개발 모드)

---