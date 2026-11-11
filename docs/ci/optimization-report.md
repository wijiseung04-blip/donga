# CI/CD 워크플로 최적화 리포트

- 측정일: 2026-11-07 (최적화 전), 2026-11-11 (최적화 후)
- 대상 워크플로: [`ci.yml`](../../.github/workflows/ci.yml), [`cache-benchmark.yml`](../../.github/workflows/cache-benchmark.yml)
- 관련 PR: [#60](https://github.com/wijiseung04-blip/donga/pull/60) (최적화 전 파이프라인), [#62](https://github.com/wijiseung04-blip/donga/pull/62) (최적화)
- 측정 방법: GitHub Actions API의 Job·Step 시작/종료 시각으로 계산. "Job 시간 합계"는 모든 Job 실행 시간의 합(러너 사용량)이고, "총 소요 시간"은 실행 시작부터 끝까지 걸린 시간입니다.

## 1. 요약

| 항목 | 최적화 전 | 최적화 후 | 변화 |
|---|---|---|---|
| 코드 변경 PR 1회의 Job 시간 합계 | 267초 (ci.yml 218 + python-app.yml 49) | 253초 (ci.yml만) | **-5%** |
| 문서만 바뀐 push 1회의 Job 시간 합계 | 260초 (Lint·Build·Test 전체 실행) | **5초** (변경 감지만 실행) | **-98%** |
| Python 설정·설치 단계 정의 위치 | 2개 워크플로에 중복 | Composite Action 1곳 | 중복 제거 |
| 배포 대상 | production 1개 | production·staging·preview 3개 (브랜치·PR 조건) | 선택적 배포 |
| pip 캐시 효과 (설치 단계) | 6.8초 (캐시 없음) | 8.3초 (캐시 사용) | **-22% (오히려 느려짐)** |

가장 큰 개선은 캐싱이 아니라 **변경 파일 감지(paths-filter)로 불필요한 실행을 건너뛴 것**이었습니다. 캐싱은 이 저장소의 의존성 규모에서는 효과가 없었고, 그 이유는 3장에 정리했습니다.

## 2. 구조 변경

```
ci.yml (호출자)
 ├─ changes   dorny/paths-filter로 코드 변경 감지 → 문서만 바뀌면 이후 Job 전부 건너뜀
 ├─ lint      uses: ./.github/actions/setup-project        (Composite Action)
 ├─ build     uses: ./.github/actions/setup-project + upload-artifact
 ├─ test      uses: ./.github/workflows/reusable-test.yml  (Reusable Workflow, 3 OS × 3 버전)
 ├─ Production  main push        ┐
 ├─ Staging     develop          ├ uses: ./.github/workflows/reusable-deploy.yml
 └─ Preview     pull_request     ┘ (inputs: environment / secrets: deploy-token / outputs: deployment-url)
cache-benchmark.yml → reusable-test.yml (use-cache: true/false)
python-app.yml → 삭제 (ci.yml과 중복)
```

| 구성 요소 | 파일 | 재사용하는 곳 |
|---|---|---|
| Composite Action | `.github/actions/setup-project/action.yml` | lint, build, reusable-test (3곳) |
| Reusable Workflow (테스트) | `.github/workflows/reusable-test.yml` | ci.yml, cache-benchmark.yml |
| Reusable Workflow (배포) | `.github/workflows/reusable-deploy.yml` | Production, Staging, Preview (3곳) |

추가 최적화:
- `concurrency`: PR에 새 커밋이 오면 이전 실행을 취소. main·develop 배포는 끊지 않음
- `timeout-minutes`: Job마다 5\~15분 상한을 두어 무한 대기 방지
- 배포 단계에서 secret 값을 출력하지 않고 길이만 확인

## 3. 캐싱 전후 비교

`Cache Benchmark` 워크플로를 캐시 사용 3회, 미사용 2회 실행했습니다(OS 3종 × Python 3.12). 측정 대상은 Composite Action 단계(Python 설치 + 캐시 복원 + 의존성 설치)와 Job 전체 시간입니다.

| OS | 설치 단계: 캐시 없음 | 설치 단계: 캐시 사용 | 개선률 | Job 전체: 캐시 없음 | Job 전체: 캐시 사용 | 개선률 |
|---|---|---|---|---|---|---|
| ubuntu-latest | 6.5초 | 6.0초 | +8% | 11.5초 | 11.3초 | +1% |
| windows-latest | 10.0초 | 12.7초 | -27% | 22.5초 | 24.3초 | -8% |
| macos-latest | 4.0초 | 6.3초 | -58% | 9.5초 | 14.0초 | -47% |
| **전체 평균** | **6.8초** | **8.3초** | **-22%** | **14.5초** | **16.6초** | **-14%** |

캐시가 정상적으로 적중했는지는 로그로 확인했습니다(`Cache hit for: setup-python-...-pip-...`, `Cache restored successfully`, `Using cached pytest-9.2.0`).

**분석: 왜 캐시가 효과가 없었나**
- 이 저장소의 의존성은 `pytest` 하나(전이 의존성 포함 5개, 약 0.4MB)입니다. PyPI에서 내려받는 시간이 1\~2초에 불과합니다.
- 반면 캐시 복원은 pip 캐시 전체(2\~4MB)를 내려받아 압축을 풀어야 해서, 내려받기보다 오래 걸리는 경우가 생깁니다.
- 측정값 차이가 1\~5초 수준이라 러너 상태에 따른 편차가 결과에 크게 작용합니다(같은 조건에서도 9\~30초).

**결론과 판단**
- 강의 목표(50% 단축)는 이 저장소에서는 달성하지 못했습니다. 의존성이 수십 MB 이상(예: numpy, pandas)인 프로젝트에서 효과가 나는 기법입니다.
- 캐시를 끄지 않고 유지합니다. 손해가 작고, 이후 의존성이 늘어나면 효과가 커지기 때문입니다. 대신 실제 시간 단축은 4장의 변경 감지로 확보했습니다.

## 4. 변경 파일 감지 효과

| 실행 | 조건 | 실행된 Job | 총 소요 시간 |
|---|---|---|---|
| [#5](https://github.com/wijiseung04-blip/donga/actions/runs/43014544770) | main push (코드 변경) | 13개 (Lint, Build, Test 9, Production 등) | 3분 23초 (production 승인 대기 포함) |
| [#6](https://github.com/wijiseung04-blip/donga/actions/runs/43015302096) | develop push (코드 변경 없음) | **1개** (Detect changes만, 나머지 Skipped) | **8초** |

DORA 대시보드 데이터 커밋, 문서 수정처럼 코드와 무관한 변경에서 9개 OS·버전 테스트를 통째로 건너뜁니다.

## 5. Matrix 실행 시간 분석 (OS × Python 버전)

5회 실행(최적화 전 2회, 후 3회)의 Test Job 평균입니다. 조합마다 6개 표본입니다.

| OS | Python 3.10 | Python 3.12 | Python 3.13 | 평균 |
|---|---|---|---|---|
| ubuntu-latest | 18초 | 11초 | 12초 | 14초 |
| macos-latest | 34초 | 15초 | 15초 | 21초 |
| windows-latest | 59초 | 23초 | 23초 | 35초 |

- Windows가 Ubuntu보다 약 2.5배 느립니다.
- Python 3.10이 모든 OS에서 가장 느립니다(Windows 59초). 러너에 미리 설치된 버전이 아니라 실행 때마다 내려받기 때문으로 보입니다.
- `fail-fast: false`로 한 조합이 실패해도 나머지 결과를 모두 확인합니다.
- 개선 여지: 3.10 지원이 꼭 필요하지 않다면 Windows·macOS에서는 3.10을 `exclude`하면 Test Job 시간 합계를 약 44% 줄일 수 있습니다(93초 / 9개 조합 합계 210초).

## 6. 선택적 배포 결과

| 조건 | 배포 환경 | 보호 규칙 | 실행 | 결과 |
|---|---|---|---|---|
| PR | preview | 없음 | [#3](https://github.com/wijiseung04-blip/donga/actions/runs/43013510839) | ✅ Production·Staging은 Skipped |
| main push | production | 승인자 필수, main 브랜치만 | [#5](https://github.com/wijiseung04-blip/donga/actions/runs/43014544770) | ✅ 승인 대기 후 승인하여 배포 |
| develop (수동 실행) | staging | develop 브랜치만 | [#7](https://github.com/wijiseung04-blip/donga/actions/runs/43015370411) | ✅ 1차 거부 → 규칙 수정 후 성공 |

#7의 1차 시도는 staging의 배포 허용 규칙이 브랜치가 아닌 **태그** 규칙으로 잘못 만들어져 `Branch "develop" is not allowed to deploy to staging due to environment protection rules.`로 거부되었습니다. 규칙을 Branch로 고친 뒤 실패한 Job만 재실행해 성공했습니다. 환경 보호 규칙이 허용되지 않은 브랜치의 배포를 실제로 막는다는 것을 확인한 사례입니다.
