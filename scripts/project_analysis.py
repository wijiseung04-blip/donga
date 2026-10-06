"""Utility functions for project analytics based on cycle time, velocity, and burndown."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median


def _to_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)
    except ValueError:
        return None


def _week_start(value: date | datetime) -> date:
    current = value.date() if isinstance(value, datetime) else value
    return current - timedelta(days=current.weekday())


def compute_cycle_time(items: list[dict]) -> dict:
    cycle_days: list[float] = []
    summary: list[dict] = []

    for item in items:
        created_at = _to_datetime(item.get("created_at"))
        closed_at = _to_datetime(item.get("closed_at") or item.get("completed_at"))
        if created_at is None or closed_at is None:
            continue
        cycle_days_value = max(0.0, (closed_at - created_at).total_seconds() / 86400)
        cycle_days.append(cycle_days_value)
        summary.append(
            {
                "id": item.get("id") or item.get("title") or item.get("name"),
                "created_at": created_at.isoformat(),
                "closed_at": closed_at.isoformat(),
                "cycle_days": round(cycle_days_value, 2),
            }
        )

    if not cycle_days:
        return {"count": 0, "avg_days": 0.0, "p90_days": 0.0, "items": []}

    ordered = sorted(cycle_days)
    p90_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.9)))
    return {
        "count": len(cycle_days),
        "avg_days": round(float(mean(cycle_days)), 2),
        "p90_days": round(float(ordered[p90_index]), 2),
        "median_days": round(float(median(cycle_days)), 2),
        "items": summary,
    }


def compute_velocity(items: list[dict]) -> dict:
    completed_by_week: dict[str, float] = defaultdict(float)
    for item in items:
        completed_at = _to_datetime(item.get("completed_at") or item.get("closed_at"))
        if completed_at is None:
            continue
        week_start = _week_start(completed_at).isoformat()
        completed_by_week[week_start] += float(item.get("size", 1) or 1)

    weeks = []
    total_points = 0.0
    for week_start in sorted(completed_by_week):
        points = completed_by_week[week_start]
        total_points += points
        weeks.append({"week_start": week_start, "completed_points": round(points, 2)})

    return {
        "total_points": round(total_points, 2),
        "weeks": weeks,
    }


def compute_burndown(
    items: list[dict],
    sprint_start: date | str,
    sprint_end: date | str,
    total_story_points: float,
) -> dict:
    start_day = date.fromisoformat(str(sprint_start)) if isinstance(sprint_start, str) else sprint_start
    end_day = date.fromisoformat(str(sprint_end)) if isinstance(sprint_end, str) else sprint_end
    completed_by_day: dict[date, float] = defaultdict(float)

    for item in items:
        closed_at = _to_datetime(item.get("closed_at") or item.get("completed_at"))
        if closed_at is None:
            continue
        closed_day = closed_at.date()
        if start_day <= closed_day <= end_day:
            completed_by_day[closed_day] += float(item.get("size", 1) or 1)

    total_days = max((end_day - start_day).days, 1)
    remaining = float(total_story_points)
    trend: list[dict] = []
    for offset in range((end_day - start_day).days + 1):
        current_day = start_day + timedelta(days=offset)
        remaining -= completed_by_day.get(current_day, 0.0)
        ideal_remaining = max(0.0, total_story_points * (1 - (offset / total_days)))
        trend.append(
            {
                "date": current_day.isoformat(),
                "remaining": round(max(remaining, 0.0), 2),
                "ideal": round(ideal_remaining, 2),
            }
        )

    return {
        "start_remaining": round(float(total_story_points), 2),
        "end_remaining": round(max(trend[-1]["remaining"], 0.0), 2),
        "last_day": trend[-1],
        "daily": trend,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze project throughput with cycle time, velocity, and burndown.")
    parser.add_argument("--input", default="project-data.json", help="Path to a JSON file containing completed issue or PR items.")
    parser.add_argument("--total-story-points", type=float, default=0.0, help="Total planned story points for the sprint.")
    parser.add_argument("--sprint-start", default=None, help="Sprint start date in ISO format, e.g. 2026-09-01.")
    parser.add_argument("--sprint-end", default=None, help="Sprint end date in ISO format, e.g. 2026-09-07.")
    return parser


def _load_items(path: str) -> list[dict]:
    candidate = Path(path)
    if not candidate.exists():
        return []
    with candidate.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("issues") or payload.get("pull_requests") or []
        if isinstance(items, list):
            return items
    return []


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    items = _load_items(args.input)
    cycle_time = compute_cycle_time(items)
    velocity = compute_velocity(items)

    if items:
        start_dates = [item.get("created_at") for item in items]
        end_dates = [item.get("completed_at") or item.get("closed_at") for item in items]
        observed_start = min(_to_datetime(value) for value in start_dates if _to_datetime(value) is not None)
        observed_end = max(_to_datetime(value) for value in end_dates if _to_datetime(value) is not None)
        sprint_start = date.fromisoformat(args.sprint_start) if args.sprint_start else observed_start.date()
        sprint_end = date.fromisoformat(args.sprint_end) if args.sprint_end else observed_end.date()
    else:
        sprint_start = date.fromisoformat(args.sprint_start) if args.sprint_start else date.today()
        sprint_end = date.fromisoformat(args.sprint_end) if args.sprint_end else date.today()

    burndown = compute_burndown(items, sprint_start, sprint_end, args.total_story_points)
    payload = {
        "cycle_time": cycle_time,
        "velocity": velocity,
        "burndown": burndown,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
