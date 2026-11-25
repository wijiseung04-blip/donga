# Docker 기반 배포 파이프라인 전략

donga의 프런트엔드(DORA 대시보드)와 API 서버를 어떻게 빌드·배포·검증·복구하는지 정리한 문서입니다.

| 대상 | 플랫폼 | 라이브 URL |
|---|---|---|
| 대시보드 (정적 사이트) | Vercel | https://donga-two.vercel.app |
| API 서버 (컨테이너) | Google Cloud Run (us-central1) | https://donga-4z36kbbboa-uc.a.run.app |

## 1. 전체 흐름

```
PR ─┬─ CI/CD Pipeline: Lint → Build → Test(3 OS × 3 Python) → Preview 배포
    ├─ Docker Publish: 이미지 빌드(테스트 단계 포함), 푸시 안 함
    └─ Vercel: PR별 Preview URL (상단에 미리보기 배너)

main 머지 ─┬─ Docker Publish ── 빌드 → ghcr.io 푸시(sha-xxxxxxx, latest) → 컨테이너 실행·헬스체크 검증
           │        │
           │        └─(workflow_run, 성공 시)→ Deploy to Cloud Run
           │                 ├─ production 환경 승인 (Required reviewers)
           │                 ├─ ghcr.io → Artifact Registry 이미지 이전
           │                 ├─ gcloud run deploy (startup·liveness probe)
           │                 └─ /health 스모크 테스트 → 실패 시 이전 리비전으로 롤백
           └─ Vercel: Production 배포 (대시보드 관련 파일이 바뀐 경우만)

매시 17분 ── Health Check: Cloud Run /health + Vercel 확인 → 실패 시 incident 이슈
5분마다   ── Cloud Monitoring 업타임 체크 → 실패 시 이메일 알림
```

## 2. 이미지 설계

| 항목 | 결정 | 이유 |
|---|---|---|
| 베이스 이미지 | `python:3.15-slim` | 크기와 호환성의 균형. 버전은 Dependabot이 주간 확인 |
| 멀티 스테이지 | 1단계에서 pytest 실행, 2단계는 소스만 복사 | 테스트가 실패하면 이미지가 만들어지지 않고, 최종 이미지에 테스트 도구가 남지 않음 |
| 실행 사용자 | `appuser` (uid 10001) | root 실행 방지 |
| 설정 주입 | `PORT`, `APP_VERSION` 환경 변수 | 같은 이미지를 로컬·Cloud Run에서 그대로 사용 (12-Factor) |
| 헬스체크 | `HEALTHCHECK` → `/healthz` | 로컬 Docker·Compose에서 컨테이너 상태를 healthy/unhealthy로 표시 |

## 3. 태그와 레지스트리 전략

| 태그 | 붙는 시점 | 용도 |
|---|---|---|
| `sha-<커밋7자리>` | main push마다 | **배포 단위.** 어떤 커밋이 운영 중인지 추적하고, 같은 태그로 언제든 재배포 |
| `latest` | main push마다 | 로컬 실행·데모용. 운영 배포에는 쓰지 않음 |
| `<버전>` (예: `1.0.1`) | `v*` 태그 push 시 | 릴리스 버전 고정 |
| `pr-<번호>` | (PR에서는 푸시하지 않음) | 빌드 검증만 수행 |

- **ghcr.io**: 빌드 결과의 원본 저장소 (GitHub 패키지, 공개)
- **Artifact Registry**: Cloud Run이 가져오는 배포용 사본. Cloud Run은 ghcr.io를 직접 쓰지 못하므로 배포 워크플로가 커밋 태그로 옮긴다

## 4. 환경과 승격

| 환경 | 트리거 | 보호 규칙 |
|---|---|---|
| preview | PR | 없음 (CI의 모의 배포, Vercel 프리뷰) |
| staging | develop 브랜치 | develop 브랜치만 배포 가능 |
| production | main + Docker Publish 성공 | **승인자 필수**, main 브랜치만 배포 가능 |

같은 이미지(같은 digest)를 PR 빌드 검증 → main 푸시 → 승인 후 운영 배포로 승격시키며, 단계마다 이미지를 다시 빌드하지 않는다.

## 5. 인증과 비밀값

| 대상 | 방식 |
|---|---|
| ghcr.io 푸시 | 워크플로 기본 토큰(`GITHUB_TOKEN`, `packages: write`) |
| GCP | **Workload Identity Federation** — 서비스 계정 키를 만들지 않고, GitHub OIDC 토큰으로 로그인. 이 저장소의 main 브랜치 워크플로만 허용 |
| 권한 분리 | 배포 계정(`github-deployer`): Cloud Run 관리 + 이 저장소 이미지 쓰기만. 실행 계정(`donga-runtime`): 권한 없음 |
| GitHub에 저장한 값 | 프로젝트 ID, 리전, 공급자 경로, 서비스 계정 이메일 → 비밀이 아니므로 Variables로 관리 |

## 6. 헬스체크와 모니터링

| 계층 | 검사 | 실패 시 |
|---|---|---|
| 이미지 빌드 | Dockerfile 테스트 단계 | 이미지 생성 중단 |
| 이미지 검증 | Docker Publish에서 컨테이너 실행 → `HEALTHCHECK` healthy + `/healthz`, `/` 응답 | 워크플로 실패, 배포로 넘어가지 않음 |
| 배포 시작 | Cloud Run **startup probe** `/healthz` (3초 간격, 10회) | 새 리비전에 트래픽이 가지 않음 |
| 실행 중 | Cloud Run **liveness probe** `/healthz` (30초 간격, 3회) | 컨테이너 재시작 |
| 배포 직후 | 스모크 테스트 `/health`에서 새 버전 확인 | **이전 리비전으로 트래픽 롤백** |
| 운영 중 | GitHub Actions Health Check (매시) | `🚨 헬스체크 실패` 이슈 생성, 복구 시 자동 종료 |
| 운영 중 | Cloud Monitoring 업타임 체크 (5분) | 이메일 알림 |

> Cloud Run은 `z`로 끝나는 일부 경로(`/healthz` 등)를 외부 요청에서 예약해 404를 반환한다. 그래서 컨테이너 내부 probe는 `/healthz`, 외부 확인은 `/health`를 사용한다. 첫 배포에서 스모크 테스트가 이 문제로 실패해 수정했다(#81).

## 7. 롤백 전략

1. **자동**: 스모크 테스트가 실패하면 배포 워크플로가 직전 리비전으로 트래픽 100%를 되돌린다.
2. **수동**: 문제가 늦게 발견되면 아래 명령으로 원하는 리비전에 트래픽을 돌린다. 이미지를 다시 빌드할 필요가 없다.
   ```bash
   gcloud run revisions list --service donga --region us-central1
   gcloud run services update-traffic donga --region us-central1 --to-revisions <리비전 이름>=100
   ```
3. **재배포**: 특정 커밋으로 되돌리려면 그 커밋의 `sha-xxxxxxx` 이미지를 지정해 배포한다.

## 8. 비용 관리

- Cloud Run: `--min-instances 0`(요청이 없으면 0대), `--max-instances 1`, CPU 1·메모리 256Mi
- 결제 예산 알림 ₩1,000 (50·90·100%)
- Vercel Hobby(무료), ghcr.io 공개 패키지(무료)

## 9. 로컬 실행

```bash
docker compose up           # compose.yaml: 운영과 같은 이미지·헬스체크
curl http://localhost:8080/health
docker compose ps           # STATUS에 (healthy)
```
