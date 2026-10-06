from datetime import date, datetime, timezone

from scripts.project_analysis import compute_burndown, compute_cycle_time, compute_velocity


def test_compute_cycle_time_aggregates_closed_work():
    items = [
        {
            "created_at": "2026-09-01T09:00:00Z",
            "closed_at": "2026-09-04T09:00:00Z",
            "size": 3,
        },
        {
            "created_at": "2026-09-08T09:00:00Z",
            "closed_at": "2026-09-11T09:00:00Z",
            "size": 5,
        },
    ]

    result = compute_cycle_time(items)

    assert result["count"] == 2
    assert result["avg_days"] == 3.0
    assert result["p90_days"] == 3.0


def test_compute_velocity_groups_completed_work_by_week():
    items = [
        {"completed_at": "2026-09-01T12:00:00Z", "size": 3},
        {"completed_at": "2026-09-04T10:00:00Z", "size": 2},
        {"completed_at": "2026-09-08T11:00:00Z", "size": 4},
    ]

    result = compute_velocity(items)

    assert result["total_points"] == 9
    assert result["weeks"][0]["week_start"] == "2026-08-31"
    assert result["weeks"][0]["completed_points"] == 5
    assert result["weeks"][1]["completed_points"] == 4


def test_compute_burndown_tracks_remaining_scope():
    sprint_start = date(2026, 9, 1)
    sprint_end = date(2026, 9, 7)
    items = [
        {"closed_at": "2026-09-02T12:00:00Z", "size": 2},
        {"closed_at": "2026-09-05T12:00:00Z", "size": 3},
    ]

    result = compute_burndown(items, sprint_start, sprint_end, total_story_points=10)

    assert result["start_remaining"] == 10
    assert result["end_remaining"] == 5
    assert result["last_day"]["remaining"] == 5
    assert result["last_day"]["ideal"] == 0.0
