# Branch Protection Rules

`main` 브랜치에 적용하는 보호 규칙입니다. **Settings → Rules → Rulesets**에서 관리합니다.

## 현재 적용 규칙: 1인 운영

| 항목 | 값 |
|---|---|
| Ruleset name | `main-protection` |
| Enforcement status | Active |
| Target branches | Include default branch (`main`) |
| Bypass list | 없음 |
| Restrict deletions | ✅ |
| Block force pushes | ✅ |
| Require a pull request before merging | ❌ |
| Require status checks to pass | ❌ |
| 그 외 규칙 | ❌ (기본값) |

### PR 필수 규칙을 켜지 않는 이유

`collect-dora-metrics.yml`은 PR이 머지될 때마다 실행되어 `GITHUB_TOKEN`으로 `main`에 **직접 커밋**합니다(`chore: update DORA dashboard data`).

- 개인 저장소 Ruleset의 Bypass list에서는 GitHub Actions를 선택할 수 없습니다. PR 필수 규칙을 켜면 이 워크플로가 `GH013: Repository rule violations`로 실패합니다.
- 워크플로가 직접 커밋하지 않고 PR을 열게 바꾸는 방법도 쓸 수 없습니다.
  - `GITHUB_TOKEN`으로 만든 PR에서는 다른 워크플로가 실행되지 않으므로 CI 체크가 생기지 않습니다.
  - DORA PR을 머지하면 워크플로가 다시 실행되어 새 DORA PR을 여는 일이 반복됩니다.

### PR 흐름은 규칙으로 지킨다

저장소가 PR을 강제하지는 않으므로, 아래 흐름은 [CONTRIBUTING.md](../CONTRIBUTING.md)의 약속으로 지킵니다.

1. `main`에 직접 push하지 않고 작업 브랜치에서 PR을 엽니다.
2. PR마다 실행되는 CI(`build (3.10)` ~ `build (3.13)`)가 모두 통과한 뒤에 머지합니다.
3. 셀프 리뷰의 `[MUST]` 스레드를 모두 Resolve한 뒤에 머지합니다.

## 설정 방법

1. **Settings → Rules → Rulesets → New ruleset → New branch ruleset**
2. Ruleset Name: `main-protection`, Enforcement status: **Active**
3. Bypass list는 비워 둠
4. **Target branches → Add target → Include default branch**
5. **Restrict deletions**, **Block force pushes**만 체크 (둘 다 기본으로 켜져 있음)
6. **Create**
7. **Actions → Collect DORA Metrics → Run workflow**로 실행해 성공하는지 확인

### GitHub CLI로 설정

```bash
gh api -X POST repos/wijiseung04-blip/donga/rulesets --input - <<'JSON'
{
  "name": "main-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" }
  ]
}
JSON
```

## 협업자가 합류하면

PR 필수 규칙을 켜려면 먼저 DORA 데이터를 `main`이 아닌 보호하지 않는 브랜치(예: `dora-data`)에 커밋하도록 워크플로를 바꿉니다. 대시보드를 GitHub Pages로 서비스 중이라면 Pages 소스도 함께 옮깁니다. 그다음 Ruleset에 아래 규칙을 추가합니다.

| 항목 | 값 |
|---|---|
| Require a pull request before merging | ✅ |
| └ Required approvals | `1` |
| └ Dismiss stale pull request approvals when new commits are pushed | ✅ |
| └ Require review from Code Owners | ✅ |
| └ Require conversation resolution before merging | ✅ |
| Require status checks to pass | ✅ |
| └ Required checks | `build (3.10)`, `build (3.11)`, `build (3.12)`, `build (3.13)` |
| └ Require branches to be up to date before merging | ✅ |
