# Security Policy

## 지원 버전

보안 수정은 아래 버전에만 제공합니다.

| 대상 | 버전 | 지원 |
|---|---|---|
| donga (저장소, Docker 이미지 `ghcr.io/wijiseung04-blip/donga`) | 1.0.x, `latest` | ✅ |
| `@wijiseung04-blip/donga-utils` (npm) | 1.0.x | ✅ |
| 그 이전 버전 | - | ❌ |

## 취약점 신고 방법

**보안 취약점은 공개 Issue나 Discussion에 올리지 마세요.** 수정되기 전에 악용될 수 있습니다.

1. 저장소의 **Security** 탭 → **Report a vulnerability**에서 비공개로 신고합니다.
2. 신고 내용에 다음을 포함해 주세요.
   - 취약점 종류와 영향 범위
   - 재현 방법 (단계, 코드, 스크린샷)
   - 영향받는 버전이나 파일 경로

## 처리 절차

| 단계 | 목표 시간 |
|---|---|
| 접수 확인 회신 | 48시간 이내 |
| 영향도 평가와 대응 계획 공유 | 7일 이내 |
| 수정 릴리스 | 심각도에 따라 결정, 수정 후 Security Advisory로 공개 |

## 보안 자동화

| 항목 | 내용 |
|---|---|
| Dependabot | npm, pip, GitHub Actions, Docker 의존성을 매주 월요일 확인하고 업데이트 PR 생성. minor/patch는 모든 체크 통과 후 자동 병합 |
| 보안 스캔 | `security-scan.yml`이 매주 `npm audit`, `pip-audit`을 실행하고, 취약점이 있으면 `security` 라벨 이슈로 리포트 |
| 비밀값 관리 | 워크플로의 비밀값은 GitHub Secrets로만 관리하며 로그에 출력하지 않음. `.gitignore`로 `.env` 커밋 방지 |
