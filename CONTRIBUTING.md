# Contributing Guide

이 저장소에 기여하는 방법을 정리한 문서입니다. 모든 변경은 **Feature 브랜치 → Pull Request → 리뷰 → 머지** 흐름을 따릅니다.

## 1. 브랜치 전략

`main`은 항상 배포 가능한 상태를 유지하며, 직접 push하지 않습니다. 작업은 `main`에서 분기한 짧은 수명의 브랜치에서 진행합니다.

| 접두사 | 용도 | 예시 |
|---|---|---|
| `feature/` | 새 기능 | `feature/greet-validation` |
| `fix/` | 버그 수정 | `fix/pytest-path` |
| `docs/` | 문서 | `docs/contributing-guide` |
| `chore/` | 설정, 빌드, 정리 | `chore/gitignore-pycache` |
| `ci/` | CI 워크플로 | `ci/python-matrix` |
| `refactor/` | 동작 변화 없는 구조 개선 | `refactor/metrics-loader` |

규칙:

- 브랜치 이름은 소문자와 `-`만 사용합니다.
- 하나의 브랜치는 하나의 목적만 다룹니다.
- 머지 후 브랜치는 삭제합니다.

```bash
git switch main
git pull origin main
git switch -c feature/<short-description>
```

## 2. 커밋 메시지 — Conventional Commits

```
<type>(<scope>): <subject>

<body>

<footer>
```

| type | 의미 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `style` | 포맷, 세미콜론 등 동작과 무관한 변경 |
| `refactor` | 기능 변화 없는 코드 구조 개선 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 패키지, 설정 등 기타 |
| `ci` | CI 설정 변경 |
| `perf` | 성능 개선 |

규칙:

- `subject`는 50자 이내, 명령형("추가", "수정")으로 쓰고 마침표를 붙이지 않습니다.
- `scope`는 선택이며 변경 영역을 나타냅니다. 예: `app`, `ci`, `metrics`, `docs`.
- 호환성을 깨는 변경은 `feat!:`처럼 `!`를 붙이거나 footer에 `BREAKING CHANGE:`를 적습니다.
- 이슈는 footer에 `Closes #12` 형식으로 연결합니다.

예시:

```
feat(app): greet 함수에 이름 입력 검증 추가

공백 문자열이나 빈 문자열이 들어오면 ValueError를 발생시킨다.

Closes #12
```

## 3. Pull Request

1. 작업 브랜치를 push하고 `main` 대상으로 PR을 엽니다.
2. PR 제목도 Conventional Commits 형식으로 작성합니다. (Squash merge 시 커밋 메시지가 됩니다.)
3. PR 템플릿(`.github/pull_request_template.md`)의 항목을 채웁니다.
4. CI(`Python application` 워크플로)가 통과해야 합니다.
5. CODEOWNERS에 지정된 리뷰어 1명 이상의 승인이 필요합니다.
6. 머지 방식은 **Squash and merge**를 기본으로 합니다.

PR 크기는 리뷰하기 쉽도록 변경 400줄 이하를 권장합니다.

## 4. 코드 리뷰

리뷰 방법과 코멘트 태그(`[MUST]`, `[SHOULD]` 등)는 [리뷰 가이드](docs/REVIEW_GUIDE.md)를 따릅니다.

## 5. 로컬 개발

```bash
pip install -r requirements.txt flake8
pytest
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## 6. 브랜치 보호 규칙

`main` 브랜치에 적용하는 보호 규칙은 [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md)에 정리되어 있습니다.
