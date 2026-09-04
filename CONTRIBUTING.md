# Contributing

Nexus 프로젝트에 기여해 주셔서 감사합니다!

---

## 이슈

- 버그 리포트나 기능 제안은 [GitHub Issues](../../issues)에 등록해 주세요.
- 이슈 제목은 간결하고 명확하게 작성합니다.
- 버그 리포트 시 **재현 단계**, **기대 동작**, **실제 동작**을 포함해 주세요.

## Pull Request

1. 이 레포를 **Fork** 합니다.
2. 새 브랜치를 만듭니다: `git checkout -b feature/your-feature`
3. 변경사항을 커밋합니다: `git commit -m "feat: 설명"`
4. Push 합니다: `git push origin feature/your-feature`
5. **Pull Request**를 생성합니다.

### PR 규칙

- PR 제목은 [Conventional Commits](https://www.conventionalcommits.org/) 형식을 따릅니다.
  - `feat:` 새 기능
  - `fix:` 버그 수정
  - `docs:` 문서 변경
  - `refactor:` 코드 리팩터링
  - `chore:` 빌드·설정 변경
- 관련 이슈가 있으면 PR 본문에 `Closes #이슈번호`를 적어 주세요.

## 개발 환경 셋업

```bash
# uv 설치 (없는 경우)
pip install uv

# 의존성 설치
uv sync

# nexus_app 실행
uv run nexus
```

## 코딩 컨벤션

- Python 3.12+ 문법을 사용합니다.
- 네이밍 규칙은 [아키텍처 문서](docs/architecture.md)의 "네이밍 규칙" 섹션을 따릅니다.
- 비공개 모듈은 `_` 접두사를 붙입니다.
- 커밋 전에 코드가 정상 동작하는지 확인해 주세요.

## 라이선스

이 프로젝트에 기여하면, 해당 기여분은 프로젝트의 [MIT 라이선스](LICENSE)에 따라 라이선스됩니다.
