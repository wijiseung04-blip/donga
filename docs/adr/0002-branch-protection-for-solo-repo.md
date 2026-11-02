# ADR-0002: 1인 운영 중에는 main의 삭제와 force push만 차단한다

- 상태: 승인됨
- 날짜: 2026-11-02
- 결정자: @wijiseung04-blip

## 배경 (Context)
`main`에 PR 필수와 CI 필수 규칙을 적용하려 했다. 그런데 `collect-dora-metrics.yml`이 PR 머지 때마다 `GITHUB_TOKEN`으로 `main`에 직접 커밋하고, 개인 저장소 Ruleset은 GitHub Actions를 bypass로 지정할 수 없다.

## 검토한 선택지 (Options)
1. PR 필수 + CI 필수: DORA 워크플로가 `GH013`으로 실패한다.
2. DORA 워크플로가 PR을 열도록 변경: `GITHUB_TOKEN`으로 만든 PR에서는 CI가 돌지 않아 머지할 수 없고, 머지할 때마다 새 DORA PR이 생기는 루프가 생긴다.
3. DORA 데이터를 별도 브랜치에 커밋: PR 필수를 켤 수 있지만 대시보드와 Pages 설정을 함께 옮겨야 한다.
4. 삭제·force push만 차단: 설정이 단순하고 DORA 워크플로가 그대로 동작한다. PR 흐름은 규칙으로 지킨다.

## 결정 (Decision)
선택지 4. PR 흐름은 CONTRIBUTING.md의 약속으로 지킨다. ([#42](https://github.com/wijiseung04-blip/donga/pull/42))

## 결과 (Consequences)
- DORA 지표 수집이 중단 없이 동작한다.
- `main` 직접 push를 저장소가 막지 않으므로 직접 주의해야 한다.
- 협업자가 합류하면 선택지 3으로 전환하고 이 ADR을 "대체됨"으로 바꾼다.