"""Collect weekly DORA metrics from GitHub pull requests and deployments."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


WEEK_COUNT = 12
OUTPUT_PATH = Path("docs/images/docs/dora-metrics.json")
REPORT_PATH = OUTPUT_PATH.with_name("dora-weekly-report.md")
API_BASE = "https://api.github.com"


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class GitHubApi:
    def __init__(self, repository: str, token: str) -> None:
        self.base_url = f"{API_BASE}/repos/{repository}"
        self.token = token

    def get(self, url: str) -> tuple[object, str | None]:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "donga-dora-metrics-collector",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response), response.headers.get("Link")
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API returned {error.code}: {details}") from error
        except URLError as error:
            raise RuntimeError(f"Could not reach GitHub API: {error.reason}") from error

    def list_all(self, path: str) -> list[dict[str, object]]:
        url = f"{self.base_url}{path}"
        records = []
        while url:
            payload, link_header = self.get(url)
            if not isinstance(payload, list):
                raise RuntimeError(f"Expected a list response from {url}")
            records.extend(payload)
            next_link = re.search(r'<([^>]+)>;\s*rel="next"', link_header or "")
            url = next_link.group(1) if next_link else ""
        return records


def _week_start(value: datetime) -> date:
    return value.date() - timedelta(days=value.weekday())


def build_metrics(
    pulls: list[dict[str, object]],
    deployments: list[dict[str, object]],
    now: datetime | None = None,
    environments: set[str] | None = None,
) -> dict[str, object]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    end_date = _week_start(now)
    first_week = end_date - timedelta(weeks=WEEK_COUNT)
    week_starts = [first_week + timedelta(weeks=index) for index in range(WEEK_COUNT)]
    rows: dict[date, dict[str, object]] = {
        week: {
            "weekStart": week.isoformat(),
            "deployments": 0,
            "successfulDeployments": 0,
            "failures": 0,
            "leadTimeHours": None,
            "leadTimeSamples": 0,
            "restoreHours": None,
            "restoreSamples": 0,
            "_leadTimeTotal": 0.0,
            "_restoreTimeTotal": 0.0,
        }
        for week in week_starts
    }
    included_environments: set[str] = set()

    for pull in pulls:
        merged_at = pull.get("merged_at")
        created_at = pull.get("created_at")
        if not isinstance(merged_at, str) or not isinstance(created_at, str):
            continue
        merged = parse_timestamp(merged_at)
        week = _week_start(merged)
        if week not in rows:
            continue
        lead_hours = max(0.0, (merged - parse_timestamp(created_at)).total_seconds() / 3600)
        row = rows[week]
        row["_leadTimeTotal"] = float(row["_leadTimeTotal"]) + lead_hours
        row["leadTimeSamples"] = int(row["leadTimeSamples"]) + 1

    status_events: list[tuple[datetime, str, str, date]] = []
    for deployment in deployments:
        created_at = deployment.get("created_at")
        if not isinstance(created_at, str):
            continue
        created = parse_timestamp(created_at)
        week = _week_start(created)
        if week not in rows:
            continue
        environment = str(deployment.get("environment", "production"))
        if environments and environment.lower() not in environments:
            continue
        included_environments.add(environment)
        row = rows[week]
        statuses = deployment.get("statuses", [])
        if not isinstance(statuses, list):
            continue
        failed = False
        succeeded = False
        completed = False
        for status in statuses:
            if not isinstance(status, dict):
                continue
            state = str(status.get("state", "")).lower()
            succeeded = succeeded or state == "success"
            completed = completed or state in {"failure", "error", "success"}
            status_created_at = status.get("created_at")
            if state in {"failure", "error"}:
                failed = True
            if state not in {"failure", "error", "success"} or not isinstance(status_created_at, str):
                continue
            timestamp = parse_timestamp(status_created_at)
            if first_week <= _week_start(timestamp) < end_date:
                status_events.append((timestamp, environment, state, week))
        if not completed:
            continue
        row["deployments"] = int(row["deployments"]) + 1
        if failed:
            row["failures"] = int(row["failures"]) + 1
        if succeeded:
            row["successfulDeployments"] = int(row["successfulDeployments"]) + 1

    pending_incident: dict[str, tuple[datetime, date]] = {}
    for timestamp, environment, state, incident_week in sorted(status_events):
        row = rows.get(incident_week)
        if row is None:
            continue
        if state in {"failure", "error"}:
            pending_incident.setdefault(environment, (timestamp, incident_week))
        elif state == "success" and environment in pending_incident:
            failed_at, failed_week = pending_incident.pop(environment)
            failed_row = rows[failed_week]
            restore_hours = max(0.0, (timestamp - failed_at).total_seconds() / 3600)
            failed_row["_restoreTimeTotal"] = float(failed_row["_restoreTimeTotal"]) + restore_hours
            failed_row["restoreSamples"] = int(failed_row["restoreSamples"]) + 1

    for row in rows.values():
        lead_count = int(row["leadTimeSamples"])
        restore_count = int(row["restoreSamples"])
        if lead_count:
            row["leadTimeHours"] = round(float(row["_leadTimeTotal"]) / lead_count, 4)
        if restore_count:
            row["restoreHours"] = round(float(row["_restoreTimeTotal"]) / restore_count, 4)
        del row["_leadTimeTotal"]
        del row["_restoreTimeTotal"]

    return {
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "rangeWeeks": WEEK_COUNT,
        "environments": sorted(included_environments),
        "weekly": list(rows.values()),
    }


def render_weekly_report(metrics: dict[str, object]) -> str:
    weeks = metrics["weekly"]
    if not isinstance(weeks, list) or not weeks:
        raise ValueError("DORA metrics must contain at least one weekly row")

    def weighted_average(value_key: str, samples_key: str) -> tuple[float | None, int]:
        sample_count = sum(int(week.get(samples_key, 0)) for week in weeks)
        if not sample_count:
            return None, 0
        total = sum(
            float(week[value_key] or 0) * int(week.get(samples_key, 0))
            for week in weeks
        )
        return total / sample_count, sample_count

    def display(value: float | None, unit: str = "") -> str:
        return "데이터 없음" if value is None else f"{value:.4g}{unit}"

    total_deployments = sum(int(week.get("deployments", 0)) for week in weeks)
    successful_deployments = sum(int(week.get("successfulDeployments", 0)) for week in weeks)
    failures = sum(int(week.get("failures", 0)) for week in weeks)
    lead_time, lead_samples = weighted_average("leadTimeHours", "leadTimeSamples")
    restore_time, restore_samples = weighted_average("restoreHours", "restoreSamples")
    failure_rate = failures / total_deployments * 100 if total_deployments else None
    average_frequency = successful_deployments / len(weeks)

    lines = [
        "# DORA 주간 보고서",
        "",
        f"- 저장소: {metrics.get('repository') or '알 수 없음'}",
        f"- 생성 시각(UTC): {metrics.get('generatedAt', '알 수 없음')}",
        f"- 집계 기간: 최근 완료된 {len(weeks)}주",
        "",
        "## 기간 요약",
        "",
        "| 지표 | 결과 |",
        "| --- | ---: |",
        f"| 변경 리드 타임 | {display(lead_time, '시간')} ({lead_samples}개 PR) |",
        f"| 배포 빈도 | {display(average_frequency, '회/주')} ({successful_deployments}회 성공 배포) |",
        f"| 변경 실패율 | {display(failure_rate, '%')} ({failures}/{total_deployments}건) |",
        f"| 평균 복구 시간 | {display(restore_time, '시간')} ({restore_samples}건) |",
        "",
        "## 주별 추이",
        "",
        "| 주 시작 | 성공 배포 | 실패 배포 | 실패율 | 리드 타임 | 복구 시간 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for week in weeks:
        deployments = int(week.get("deployments", 0))
        week_failures = int(week.get("failures", 0))
        week_failure_rate = week_failures / deployments * 100 if deployments else None
        lead_value = week.get("leadTimeHours") if week.get("leadTimeSamples") else None
        restore_value = week.get("restoreHours") if week.get("restoreSamples") else None
        lines.append(
            "| {week} | {successes} | {failures} | {rate} | {lead} | {restore} |".format(
                week=week["weekStart"],
                successes=week.get("successfulDeployments", 0),
                failures=week_failures,
                rate=display(week_failure_rate, "%"),
                lead=display(lead_value, "시간"),
                restore=display(restore_value, "시간"),
            )
        )

    lines.extend(
        [
            "",
            "배포 지표는 GitHub Deployments 기록 기준입니다. 리드 타임은 PR 생성부터 병합까지 계산합니다.",
            "",
        ]
    )
    return "\n".join(lines)


def collect(api: GitHubApi, now: datetime | None = None) -> dict[str, object]:
    pulls = api.list_all("/pulls?state=closed&per_page=100")
    deployments = api.list_all("/deployments?per_page=100")
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    first_week = _week_start(current_time) - timedelta(weeks=WEEK_COUNT)
    environments = {
        name.strip().lower()
        for name in os.environ.get("DORA_ENVIRONMENTS", "").split(",")
        if name.strip()
    }
    relevant_deployments = []
    for deployment in deployments:
        created_at = deployment.get("created_at")
        if not isinstance(created_at, str) or _week_start(parse_timestamp(created_at)) < first_week:
            continue
        if environments and str(deployment.get("environment", "production")).lower() not in environments:
            continue
        deployment_id = deployment.get("id")
        if deployment_id is None:
            continue
        statuses = api.list_all(f"/deployments/{deployment_id}/statuses?per_page=100")
        relevant_deployments.append({**deployment, "statuses": statuses})
    return build_metrics(pulls, relevant_deployments, current_time, environments)


def main() -> None:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repository or not token:
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    if not re.fullmatch(r"[^/]+/[^/]+", repository):
        raise SystemExit("GITHUB_REPOSITORY must use owner/repository format")

    metrics = collect(GitHubApi(repository, token))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_weekly_report(metrics), encoding="utf-8")
    print(f"Wrote {len(metrics['weekly'])} weeks of DORA data to {OUTPUT_PATH} and {REPORT_PATH}")


if __name__ == "__main__":
    main()