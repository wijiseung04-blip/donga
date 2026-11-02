# Architecture Decision Records

되돌리기 어렵거나 여러 선택지를 비교해 내린 기술 결정을 기록합니다.

## 작성 방법
1. [template.md](template.md)를 복사해 `NNNN-짧은-제목.md`로 저장합니다. 번호는 마지막 번호 + 1입니다.
2. 처음에는 상태를 "제안됨"으로 두고 PR을 엽니다.
3. 리뷰 후 머지할 때 "승인됨"으로 바꿉니다.
4. 결정이 바뀌면 기존 ADR은 지우지 않고 "ADR-XXXX로 대체됨"으로 표시합니다.

## 목록
| 번호 | 제목 | 상태 |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | 기술 결정을 ADR로 기록한다 | 승인됨 |
| [0002](0002-branch-protection-for-solo-repo.md) | 1인 운영 중에는 main의 삭제와 force push만 차단한다 | 승인됨 |