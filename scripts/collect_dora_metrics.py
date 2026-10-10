import json
import os
import urllib.error
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
        monday.year,
        monday.month,
        monday.day,
        tzinfo=timezone.utc,
    )


def build_weeks(now):
    current_monday = week_start(now)

    return [
        {
            "week": (
                current_monday - timedelta(weeks=offset)
            ).date().isoformat(),
            "deployments": 0,
            "successfulDeployments": 0,
            "failures": 0,
            "changeFailureRate": None,
            "leadTimeHours": None,
            "leadTimeSamples": 0,
            "restoreHours": None,
            "restoreSamples": 0,
        }
        for offset in reversed(range(1, WEEK_COUNT + 1))
    ]


def latest_status(statuses):
    """완료된 배포 상태 중 가장 최근 이벤트를 반환한다."""
    dated = [
        status
        for status in statuses
        if status.get("state") in COMPLETED_STATES
        and parse_time(status.get("created_at"))
    ]

    if not dated:
        return None

    return max(
        dated,
        key=lambda status: parse_time(status["created_at"]),
    )

def build_metrics(pulls, deployments, now, environments=None):
    weeks = build_weeks(now)
    by_week = {item["week"]: item for item in weeks}
    allowed = set(environments) if environments is not None else None

    observed_environments = set()
    completed = []

    for deployment in deployments:
        environment = deployment.get("environment", "unknown")

        if allowed is not None and environment not in allowed:
            continue

        observed_environments.add(environment)

        statuses = deployment.get("statuses", [])
        final_status = latest_status(statuses)

        if final_status is None:
            continue

        state = final_status.get("state")
        completed_at = parse_time(final_status.get("created_at"))

        if state not in COMPLETED_STATES or completed_at is None:
            continue

        completed.append({
            "environment": environment,
            "state": state,
            "created_at": parse_time(deployment.get("created_at")),
            "completed_at": completed_at,
        })

    # 배포 횟수와 변경 실패율
    for deployment in completed:
        key = week_start(deployment["completed_at"]).date().isoformat()
        item = by_week.get(key)

        if item is None:
            continue

        item["deployments"] += 1

        if deployment["state"] == "success":
            item["successfulDeployments"] += 1
        else:
            item["failures"] += 1

    for item in weeks:
        if item["deployments"]:
            item["changeFailureRate"] = round(
                item["failures"] / item["deployments"] * 100,
                2,
            )

    # 테스트에서 정의한 리드 타임: PR 생성부터 병합까지
    lead_values = defaultdict(list)

    for pull in pulls:
        created_at = parse_time(pull.get("created_at"))
        merged_at = parse_time(pull.get("merged_at"))

        if created_at is None or merged_at is None:
            continue
        if merged_at < created_at:
            continue

        key = week_start(merged_at).date().isoformat()

        if key in by_week:
            lead_values[key].append(
                (merged_at - created_at).total_seconds() / 3600
            )

    for key, values in lead_values.items():
        by_week[key]["leadTimeHours"] = round(
            sum(values) / len(values), 2
        )
        by_week[key]["leadTimeSamples"] = len(values)

    # 복구 시간: 실패 배포 이후 같은 환경에서 처음 성공한 배포까지
    restore_values = defaultdict(list)

    for failed in completed:
        if failed["state"] != "failure" and failed["state"] != "error":
            continue

        recoveries = [
            deployment
            for deployment in completed
            if deployment["environment"] == failed["environment"]
            and deployment["state"] == "success"
            and deployment["completed_at"] > failed["completed_at"]
        ]

        if not recoveries:
            continue

        recovered = min(
            recoveries,
            key=lambda deployment: deployment["completed_at"],
        )

        hours = (
            recovered["completed_at"] - failed["completed_at"]
        ).total_seconds() / 3600

        key = week_start(failed["completed_at"]).date().isoformat()

        if key in by_week:
            restore_values[key].append(hours)

    for key, values in restore_values.items():
        by_week[key]["restoreHours"] = round(
            sum(values) / len(values), 2
        )
        by_week[key]["restoreSamples"] = len(values)

    result = {
        "generatedAt": iso_time(now),
        "rangeWeeks": WEEK_COUNT,
        "environments": sorted(observed_environments),
        "weekly": weeks,
    }

    # 기존 collect() 및 보고서 코드와의 호환성 유지
    result["weeks"] = weeks

    return result
    
def collect(repository, token, now):
    api = GitHubAPI(repository, token)

    weeks = build_weeks(now)
    by_week = {item["week"]: item for item in weeks}
    start_time = parse_time(weeks[0]["week"] + "T00:00:00Z")

    environments = {
        value.strip()
        for value in os.getenv(
            "DORA_ENVIRONMENTS", "production"
        ).split(",")
        if value.strip()
    }

    pulls = api.list_all(
        "/pulls?state=closed&sort=updated&direction=desc"
    )
    deployments = api.list_all("/deployments?per_page=100")

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

        if final_status is None:
            continue

        state = final_status.get("state")
        completed_at = parse_time(final_status.get("created_at"))

        if state not in COMPLETED_STATES or completed_at is None:
            continue

        completed_deployments.append({
            "id": deployment["id"],
            "sha": deployment.get("sha"),
            "environment": environment,
            "created_at": created_at,
            "completed_at": completed_at,
            "state": state,
        })

    # 1. 배포 빈도와 변경 실패율
    for deployment in completed_deployments:
        key = week_start(
            deployment["completed_at"]
        ).date().isoformat()

        item = by_week.get(key)

        if item is None:
            continue

        item["deployments"] += 1

        if deployment["state"] == "success":
            item["successfulDeployments"] += 1
        else:
            item["failures"] += 1

    for item in weeks:
        total = item["deployments"]

        if total:
            item["changeFailureRate"] = round(
                item["failures"] / total * 100,
                2,
            )

    # 2. 리드 타임의 대리 지표
    # PR 병합 시각부터 이후 최초 성공 배포까지 계산한다.
    # 정확한 DORA 리드 타임에는 배포된 변경 사항과 PR의 연결이 필요하다.
    successful_deployments = sorted(
        (
            deployment
            for deployment in completed_deployments
            if deployment["state"] == "success"
        ),
        key=lambda deployment: deployment["completed_at"],
    )

    lead_times = defaultdict(list)

    for pull in pulls:
        if not pull.get("merged_at"):
            continue

        merged_at = parse_time(pull["merged_at"])

        if merged_at is None or merged_at < start_time:
            continue

        # 가능하면 PR의 merge commit SHA와 일치하는 배포를 우선한다.
        merge_sha = pull.get("merge_commit_sha")

        matching_deployments = [
            deployment
            for deployment in successful_deployments
            if (
                (not environments
                 or deployment["environment"] in environments)
                and deployment["completed_at"] >= merged_at
                and (
                    not merge_sha
                    or deployment["sha"] == merge_sha
                )
            )
        ]

        # GitHub deployment SHA가 PR의 merge SHA와 일치하지 않으면
        # 정확한 연결이 불가능하므로 임의로 다른 배포를 선택하지 않는다.
        if not merge_sha or not matching_deployments:
            continue

        first_deployment = min(
            matching_deployments,
            key=lambda deployment: deployment["completed_at"],
        )

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

    return {
        "generatedAt": iso_time(now),
        "rangeWeeks": WEEK_COUNT,
        "environments": sorted(environments),
        "weeks": weeks,
        "metricNotes": {
            "leadTimeHours": (
                "PR 병합 시각부터 동일 merge SHA를 사용하는 "
                "성공 배포까지의 시간. SHA 연결이 불가능하면 제외."
            ),
            "changeFailureRate": (
                "완료된 배포 중 최종 완료 상태가 failure 또는 error인 비율. "
                "실제 서비스 장애율과 반드시 같지는 않음."
            ),
            "restoreHours": (
                "장애 발생 및 복구 시각을 기록하는 데이터가 없어 계산하지 않음."
            ),
        },
    }


def render_weekly_report(metrics):
    weeks = metrics.get("weekly", metrics.get("weeks", []))

    successful = sum(w["successfulDeployments"] for w in weeks)
    failures = sum(w["failures"] for w in weeks)
    total = sum(w["deployments"] for w in weeks)

    lead_values = [
        (w["leadTimeHours"], w["leadTimeSamples"])
        for w in weeks
        if w["leadTimeHours"] is not None and w["leadTimeSamples"] > 0
    ]
    lead_samples = sum(count for _, count in lead_values)
    average_lead = (
        sum(hours * count for hours, count in lead_values) / lead_samples
        if lead_samples else None
    )

    restore_values = [
        (w["restoreHours"], w["restoreSamples"])
        for w in weeks
        if w["restoreHours"] is not None and w["restoreSamples"] > 0
    ]
    restore_samples = sum(count for _, count in restore_values)
    average_restore = (
        sum(hours * count for hours, count in restore_values) / restore_samples
        if restore_samples else None
    )

    failure_rate = failures / total * 100 if total else None

    def format_hours(value):
        if value is None:
            return "데이터 없음"
        return f"{value:g}시간"

    lines = [
        "# DORA 주간 보고서",
        "",
        f"- 생성 시각(UTC): {metrics.get('generatedAt', 'N/A')}",
        f"- 집계 기간: 최근 {metrics.get('rangeWeeks', WEEK_COUNT)}주",
        "",
        "## 요약",
        "",
        "| 지표 | 결과 |",
        "|---|---|",
        (
            f"| 변경 리드 타임 | {format_hours(average_lead)} "
            f"({lead_samples}개 PR) |"
            if average_lead is not None
            else "| 변경 리드 타임 | 데이터 없음 |"
        ),
        (
            f"| 변경 실패율 | {failure_rate:g}% ({failures}/{total}건) |"
            if failure_rate is not None
            else "| 변경 실패율 | 데이터 없음 |"
        ),
        (
            f"| 평균 복구 시간 | {format_hours(average_restore)} "
            f"({restore_samples}건) |"
            if average_restore is not None
            else "| 평균 복구 시간 | 데이터 없음 |"
        ),
        "",
        "## 주별 지표",
        "",
        "| 주 시작 | 성공 배포 | 실패 배포 | 실패율 | 리드 타임 | 복구 시간 |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for week in weeks:
        rate = week["changeFailureRate"]
        rate_text = f"{rate:g}%" if rate is not None else "데이터 없음"

        lead = format_hours(week["leadTimeHours"])
        restore = format_hours(week["restoreHours"])

        lines.append(
            f"| {week['week']} "
            f"| {week['successfulDeployments']} "
            f"| {week['failures']} "
            f"| {rate_text} "
            f"| {lead} "
            f"| {restore} |"
        )

    return "\n".join(lines) + "\n"
    

def write_report(metrics):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        render_weekly_report(metrics),
        encoding="utf-8",
    )

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
