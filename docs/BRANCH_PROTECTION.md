# Branch Protection Rules

`main` 브랜치에 적용하는 보호 규칙입니다. 저장소 관리자가 **Settings → Branches → Add branch ruleset**(또는 *Branch protection rules*)에서 설정합니다.

## 대상

- Branch name pattern: `main`

## 설정 항목

| 항목 | 값 | 이유 |
|---|---|---|
| Require a pull request before merging | ✅ | `main` 직접 push 금지 |
| └ Required approvals | `1` | 최소 1명 리뷰 승인 |
| └ Dismiss stale pull request approvals when new commits are pushed | ✅ | 승인 후 변경된 코드도 재검토 |
| └ Require review from Code Owners | ✅ | `.github/CODEOWNERS` 기반 리뷰어 강제 |
| └ Require conversation resolution before merging | ✅ | `[MUST]` 코멘트 미해결 상태 머지 방지 |
| Require status checks to pass before merging | ✅ | CI 통과 필수 |
| └ Required checks | `build` (Python application) | pytest, flake8 |
| └ Require branches to be up to date before merging | ✅ | 최신 `main` 기준 검증 |
| Require linear history | ✅ | Squash merge 기반 깔끔한 이력 |
| Allow force pushes | ❌ | 이력 보호 |
| Allow deletions | ❌ | 브랜치 삭제 방지 |

> 1인 저장소에서는 본인 PR을 본인이 승인할 수 없으므로, 협업자가 없는 동안에는 *Required approvals*를 `0`으로 두고 나머지 규칙만 적용합니다.

## 자동 워크플로 예외

`collect-dora-metrics.yml` 등 `main`에 직접 커밋하는 워크플로가 있습니다. 보호 규칙을 켤 때는 다음 중 하나를 선택합니다.

1. Ruleset의 **Bypass list**에 `github-actions[bot]`(또는 해당 GitHub App)을 추가한다.
2. 워크플로가 별도 브랜치에 커밋하고 PR을 열도록 변경한다.

## GitHub CLI로 설정

```bash
gh api -X PUT repos/wijiseung04-blip/donga/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -f "required_status_checks[strict]=true" \
  -f "required_status_checks[contexts][]=build" \
  -F "enforce_admins=false" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -F "required_pull_request_reviews[require_code_owner_reviews]=true" \
  -F "required_conversation_resolution=true" \
  -F "required_linear_history=true" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false" \
  -F "restrictions=null"
```
