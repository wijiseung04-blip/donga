from datetime import date, datetime, timezone
import json

import pytest
from scripts.project_analysis import (
    compute_burndown,
    compute_cycle_time,
    compute_velocity,
    main,
    render_markdown_report,
)


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


def test_compute_burndown_rejects_end_date_before_start_date():
    with pytest.raises(ValueError, match="Sprint end date"):
        compute_burndown(
            [],
            date(2026, 9, 7),
            date(2026, 9, 1),
            total_story_points=10,
        )


def test_render_markdown_report_includes_metrics_and_notes_missing_burndown_inputs():
    report = render_markdown_report(
        {
            "count": 1,
            "avg_days": 2.0,
            "median_days": 2.0,
            "p90_days": 2.0,
        },
        {
            "total_points": 1.0,
            "weeks": [{"week_start": "2026-09-07", "completed_points": 1.0}],
        },
        burndown=None,
    )

    assert "# Project Metrics" in report
    assert "## Cycle Time" in report
    assert "## Velocity" in report
    assert "| 2026-09-07 | 1.00 |" in report
    assert "## Burndown" in report
    assert "Not calculated." in report


def test_render_markdown_report_includes_burndown_when_available():
    report = render_markdown_report(
        {"count": 0, "avg_days": 0.0, "p90_days": 0.0, "items": []},
        {"total_points": 0.0, "weeks": []},
        burndown={
            "start_remaining": 3.0,
            "end_remaining": 2.0,
            "daily": [
                {"date": "2026-09-01", "remaining": 3.0, "ideal": 3.0},
                {"date": "2026-09-02", "remaining": 2.0, "ideal": 0.0},
            ],
        },
    )

    assert "**Sprint scope:** 3.00 sizing units" in report
    assert "| 2026-09-02 | 2.00 | 0.00 |" in report


def test_main_writes_report_and_json_with_burndown(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "issues.json"
    report_path = tmp_path / "project-metrics.md"
    input_path.write_text(
        json.dumps(
            [
                {
                    "id": "1",
                    "created_at": "2026-09-01T00:00:00Z",
                    "closed_at": "2026-09-02T00:00:00Z",
                    "size": 1,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "project_analysis.py",
            "--input",
            str(input_path),
            "--output-markdown",
            str(report_path),
            "--sprint-start",
            "2026-09-01",
            "--sprint-end",
            "2026-09-03",
            "--total-story-points",
            "3",
        ],
    )

    main()

    result = json.loads(capsys.readouterr().out)
    report = report_path.read_text(encoding="utf-8")
    assert result["burndown"]["end_remaining"] == 2
    assert "| 2026-09-02 | 2.00 |" in report
