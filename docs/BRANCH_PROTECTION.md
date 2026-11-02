# Branch Protection Rules

`main` 브랜치에 적용하는 보호 규칙입니다. 저장소 관리자가 **Settings → Branches → Add branch ruleset**(또는 *Branch protection rules*)에서 설정합니다.

## 대상

- Branch name pattern: `main`

## 운영 기준: 1인 저장소

현재 이 저장소는 혼자 운영합니다. GitHub는 본인 PR을 본인이 승인하는 것을 막으므로, **승인 대신 "PR 필수 + CI 통과 + 리뷰 스레드 해결"** 으로 품질을 지킵니다. 협업자가 합류하면 아래 표의 *협업 시* 값으로 올립니다.

## 설정 항목

| 항목 | 1인 운영 (현재) | 협업 시 | 이유 |
|---|---|---|---|
| Require a pull request before merging | ✅ | ✅ | `main` 직접 push 금지, 모든 변경을 PR로 남김 |
| └ Required approvals | `0` | `1` | 본인 PR은 본인이 승인할 수 없음 |
| └ Dismiss stale approvals on new commits | ❌ | ✅ | 승인자가 없으면 의미 없음 |
| └ Require review from Code Owners | ❌ | ✅ | CODEOWNERS가 본인뿐이라 켜면 머지 불가 |
| └ Require conversation resolution before merging | ✅ | ✅ | 셀프 리뷰의 `[MUST]` 미해결 상태 머지 방지 |
| Require status checks to pass | ✅ | ✅ | CI 통과 필수 |
| └ Required checks | `build (3.10)`, `build (3.11)`, `build (3.12)`, `build (3.13)` | 동일 | pytest, flake8 (Python application 매트릭스) |
| └ Require branches to be up to date | ❌ | ✅ | DORA 워크플로가 수시로 `main`에 커밋해 PR이 계속 뒤처짐 |
| Require linear history | ❌ | 선택 | 지금까지 Merge commit으로 머지해 왔음 |
| Block force pushes | ✅ | ✅ | 이력 보호 |
| Restrict deletions | ✅ | ✅ | 브랜치 삭제 방지 |

## 자동 워크플로 예외 (필수)

`collect-dora-metrics.yml`, `throughput.yml` 등은 `GITHUB_TOKEN`으로 `main`에 **직접 커밋**합니다. "Require a pull request"를 켜면 이 워크플로가 실패하므로 반드시 예외를 둡니다.

- 기존 *Branch protection rules*(classic)는 GitHub Actions를 예외로 둘 수 없습니다.
- **Rulesets**를 사용하고 **Bypass list**에 **GitHub Actions** 앱을 추가합니다.

## UI로 설정

1. **Settings → Rules → Rulesets → New ruleset → New branch ruleset**
2. Ruleset name: `main-protection`, Enforcement status: **Active**
3. Bypass list → **Add bypass** → **GitHub Actions** (Always allow)
4. Target branches → **Add target → Include default branch**
5. 위 표의 *1인 운영* 열대로 규칙을 체크하고 저장

## GitHub CLI로 설정

```bash
gh api -X POST repos/wijiseung04-blip/donga/rulesets --input - <<'JSON'
{
  "name": "main-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [
    { "actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always" }
  ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [
          { "context": "build (3.10)" },
          { "context": "build (3.11)" },
          { "context": "build (3.12)" },
          { "context": "build (3.13)" }
        ]
      }
    }
  ]
}
JSON
```

`actor_id: 15368`은 GitHub Actions 앱의 ID입니다. 설정 후 DORA 워크플로를 한 번 수동 실행해 `main` 커밋이 성공하는지 확인합니다.
