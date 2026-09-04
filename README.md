# Manilet

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## 프로젝트 구성

### 1. [Nexus App](./nexus_app/README.md)
에이전트 통합 관리 TUI 프로그램

### 2. [Nexuspy](./nexuspy/README.md)
에이전트 전용 SDK


### 3. [VTM](https://www.youtube.com/watch?v=3baR3FK2Poc)
백테스팅, 에이전트 연구 및 제작용 프레임워크
> 현재 개발중...

---

## 빠른 시작
manilet의 모든 프로젝트(main 브랜치)를 가상환경에 설치합니다.

> 현재 VTM은 개발중이므로 설치가 불가능합니다. 아래 패키지 설치 방법은 VTM을 제외한 패키지 설치 방법입니다.

### 1. 가상환경 생성 및 진입
프로젝트가 생성되길 원하는 폴더에서 터미널을 열고 운영체제에 따라 아래 명령어를 선택하여 실행합니다.

#### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Mac/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```
> Mac/Linux 환경에서 `python3` 대신 `python`으로 알리아스가 설정되어 있다면 `python3 -m venv .venv`를 사용해도 무방합니다.

### 2. 패키지 설치
가상환경에 진입된 터미널에서 아래 명령어를 전부 복사하여 실행합니다.
```bash
# nexus_app 설치
pip install "manilet-nexus-app @ git+https://github.com/agradra/manilet.git#subdirectory=nexus_app"

# nexuspy 설치
pip install "manilet-nexuspy @ git+https://github.com/agradra/manilet.git#subdirectory=nexuspy"
```

### 3. 사용
[프로젝트 구성](#프로젝트-구성)에 따라 원하는 패키지를 사용한다.

---

## 개발자 가이드

### Nexuspy
- [통신 프로토콜 (Nexus App ⇄ Nexuspy)](./nexuspy/docs/agent_protocol.md)