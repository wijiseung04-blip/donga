import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

WEEK_COUNT = 12
API_BASE = "https://api.github.com"
OUTPUT_PATH = Path("docs/images/docs/dora-metrics.json")
REPORT_PATH = Path("docs/images/docs/dora-weekly-report.md")

SUCCESS_STATES = {"success"}
FAILURE_STATES = {"failure", "error"}
COMPLETED_STATES = SUCCESS_STATES | FAILURE_STATES


def parse_time(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def iso_time(value):
    return value.astimezone(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


class GitHubAPI:
    def __init__(self, repository, token):
        self.repository = repository
        self.token = token

    def get(self, path):
        url = f"{API_BASE}/repos/{self.repository}{path}"

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "dora-metrics-collector",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API 요청 실패: {path} "
                f"(HTTP {exc.code}): {body}"
            ) from exc

    def list_all(self, path):
        results = []
        page = 1

        while True:
            separator = "&" if "?" in path else "?"
            page_path = (
                f"{path}{separator}per_page=100&page={page}"
            )
            data = self.get(page_path)

            if not isinstance(data, list):
                raise RuntimeError(
                    f"예상하지 못한 API 응답: {page_path}"
                )

            results.extend(data)

            if len(data) < 100:
                break

            page += 1

        return results

    def deployment_statuses(self, deployment_id):
        return self.list_all(
            f"/deployments/{deployment_id}/statuses"
        )


def week_start(value):
    monday = value.date() - timedelta(days=value.weekday())
    return datetime(
        monday.year, monday.month, monday.day,
        tzinfo=timezone.utc,
    )


def build_weeks(now):
    current_monday = week_start(now)
    weeks = []

    for offset in reversed(range(WEEK_COUNT)):
        start = current_monday - timedelta(weeks=offset)
        weeks.append({
            "week": start.date().isoformat(),
            "deployments": 0,
            "successfulDeployments": 0,
            "failures": 0,
            "changeFailureRate": None,
            "leadTimeHours": None,
            "leadTimeSamples": 0,
            "restoreHours": None,
            "restoreSamples": 0,
        })

    return weeks


def latest_status(statuses):
    """배포의 최종 상태는 가장 최근 상태 이벤트로 판정한다."""
    dated = [
        status for status in statuses
        if parse_time(status.get("created_at"))
    ]

    if not dated:
        return None

    return max(
        dated,
        key=lambda status: parse_time(status["created_at"]),
    )


def collect(repository, token, now):
    api = GitHubAPI(repository, token)

    weeks = build_weeks(now)
    by_week = {item["week"]: item for item in weeks}
    start_time = parse_time(weeks[0]["week"] + "T00:00:00Z")

    environments = {
        value.strip()
        for value in os.getenv("DORA_ENVIRONMENTS", "production").split(",")
        if value.strip()
    }

    pulls = api.list_all(
        "/pulls?state=closed&sort=updated&direction=desc"
    )
    deployments = api.list_all(
        "/deployments?per_page=100"
    )

    # 상태를 조회하고 운영 환경의 완료된 배포만 추린다.
    completed_deployments = []

    for deployment in deployments:
        environment = deployment.get("environment", "unknown")

        if environments and environment not in environments:
            continue

        created_at = parse_time(deployment.get("created_at"))

        if not created_at or created_at < start_time:
            continue

        statuses = api.deployment_statuses(deployment["id"])
        final_status = latest_status(statuses)

        if not final_status:
            continue

        state = final_status.get("state")
        status_time = parse_time(final_status.get("created_at"))

        if state not in COMPLETED_STATES or not status_time:
            continue

        completed_deployments.append({
            "id": deployment["id"],
            "sha": deployment.get("sha"),
            "environment": environment,
            "created_at": created_at,
            "completed_at": status_time,
            "state": state,
        })

    # 배포 빈도와 변경 실패율은 배포 완료 주차에 집계한다.
    for deployment in completed_deployments:
        key = week_start(deployment["completed_at"]).date().isoformat()
        item = by_week.get(key)

        if item is None:
            continue

        item["deployments"] += 1

        if deployment["state"] in SUCCESS_STATES:
            item["successfulDeployments"] += 1
        else:
            item["failures"] += 1

    for item in weeks:
        total = item["deployments"]

        if total:
            item["changeFailureRate"] = round(
                item["failures"] / total * 100, 2
            )

    # PR 병합부터 그 이후 최초 성공 배포까지의 시간을 계산한다.
    # 주의: 커밋 시점부터의 정확한 DORA 리드 타임은 아니다.
    successful_deployments = sorted(
        (
            deployment for deployment in completed_deployments
            if deployment["state"] in SUCCESS_STATES
        ),
        key=lambda deployment: deployment["completed_at"],
    )

    lead_times = defaultdict(list)

    for pull in pulls:
        if not pull.get("merged_at"):
            continue

        merged_at = parse_time(pull["merged_at"])

        if not merged_at or merged_at < start_time:
            continue

        first_deployment = next(
            (
                deployment
                for deployment in successful_deployments
                if deployment["environment"] in environments
                and deployment["completed_at"] >= merged_at
            ),
            None,
        )

        if not first_deployment:
            continue

        hours = (
            first_deployment["completed_at"] - merged_at
        ).total_seconds() / 3600

        key = week_start(merged_at).date().isoformat()

        if key in by_week and hours >= 0:
            lead_times[key].append(hours)

    for key, values in lead_times.items():
        by_week[key]["leadTimeHours"] = round(
            sum(values) / len(values), 2
        )
        by_week[key]["leadTimeSamples"] = len(values)

    # GitHub 배포 상태만으로는 실제 장애 발생 및 복구 시점을
    # 확정할 수 없으므로, 복구 시간은 임의로 산출하지 않는다.
    return {
        "generatedAt": iso_time(now),
        "rangeWeeks": WEEK_COUNT,
        "environments": sorted(environments),
        "weeks": weeks,
        "metricNotes": {
            "leadTimeHours": (
                "PR 병합부터 최초 성공 배포까지의 시간. "
                "커밋부터 배포까지의 정확한 DORA 리드 타임은 아님."
            ),
            "changeFailureRate": (
                "완료된 배포 중 최종 상태가 failure 또는 error인 비율."
            ),
            "restoreHours": (
                "실제 장애 발생 및 복구 기록이 없어 계산하지 않음."
            ),
        },
    }


def write_report(metrics):
    weeks = metrics["weeks"]
    successful = sum(w["successfulDeployments"] for w in weeks)
    failures = sum(w["failures"] for w in weeks)
    total = sum(w["deployments"] for w in weeks)

    lead_values = [
        (w["leadTimeHours"], w["leadTimeSamples"])
        for w in weeks
        if w["leadTimeHours"] is not None
        and w["leadTimeSamples"] > 0
    ]

    lead_samples = sum(count for _, count in lead_values)
    weighted_lead = (
        sum(hours * count for hours, count in lead_values) / lead_samples
        if lead_samples else None
    )

    failure_rate = failures / total * 100 if total else None
    deployment_frequency = successful / WEEK_COUNT

    lines = [
        "# DORA 주간 보고서",
        "",
        f"- 생성 시각(UTC): {metrics['generatedAt']}",
        f"- 집계 기간: 최근 {WEEK_COUNT}주",
        f"- 대상 환경: {', '.join(metrics['environments']) or '전체'}",
        "",
        "## 요약",
        "",
        (
            f"- 성공 배포 빈도: 주당 {deployment_frequency:.2f}회 "
            f"({successful}회 / {WEEK_COUNT}주)"
        ),
        (
            f"- 변경 실패율: {failure_rate:.2f}% "
            f"({failures}/{total}회)"
            if failure_rate is not None
            else "- 변경 실패율: 데이터 없음"
        ),
        (
            f"- PR 병합→최초 성공 배포 시간: {weighted_lead:.2f}시간 "
            f"({lead_samples}개 PR)"
            if weighted_lead is not None
            else "- PR 병합→최초 성공 배포 시간: 데이터 없음"
        ),
        "- 장애 복구 시간: 데이터 없음 (장애·복구 이벤트 기록 필요)",
        "",
        "## 주별 지표",
        "",
        "| 주 시작일(UTC) | 성공 배포 | 완료 배포 | 실패 배포 | 변경 실패율 | PR 병합→배포 평균(시간) |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for week in weeks:
        rate = (
            f"{week['changeFailureRate']:.2f}%"
            if week["changeFailureRate"] is not None
            else "데이터 없음"
        )
        lead = (
            f"{week['leadTimeHours']:.2f}"
            if week["leadTimeHours"] is not None
            else "데이터 없음"
        )

        lines.append(
            f"| {week['week']} "
            f"| {week['successfulDeployments']} "
            f"| {week['deployments']} "
            f"| {week['failures']} "
            f"| {rate} "
            f"| {lead} |"
        )

    lines.extend([
        "",
        "## 해석 시 주의사항",
        "",
        "- PR 병합부터 배포까지의 시간은 커밋부터 배포까지의 정확한 DORA 리드 타임과 다릅니다.",
        "- 변경 실패율은 배포의 최종 상태를 사용하므로, 배포 후 발생한 실제 서비스 장애를 모두 의미하지는 않습니다.",
        "- 복구 시간은 실제 장애 감지·복구 시각을 기록하는 별도 모니터링 데이터가 있어야 계산할 수 있습니다.",
        "",
    ])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    repository = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")

    if not repository or not token:
        raise SystemExit(
            "GITHUB_REPOSITORY와 GITHUB_TOKEN 환경 변수가 필요합니다."
        )

    now = datetime.now(timezone.utc)
    metrics = collect(repository, token, now)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(metrics)

    print(f"DORA 지표 저장 완료: {OUTPUT_PATH}")
    print(f"주간 보고서 저장 완료: {REPORT_PATH}")


if __name__ == "__main__":
    main()
