from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collect_dora_metrics import build_metrics


def test_build_metrics_aggregates_lead_time_deployments_and_recovery():
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    failed_at = "2026-07-14T10:00:00Z"
    recovered_at = "2026-07-16T10:00:00Z"
    metrics = build_metrics(
        pulls=[
            {"created_at": "2026-07-14T00:00:00Z", "merged_at": "2026-07-14T12:00:00Z"}
        ],
        deployments=[
            {
                "created_at": failed_at,
                "environment": "production",
                "statuses": [{"state": "failure", "created_at": failed_at}],
            },
            {
                "created_at": recovered_at,
                "environment": "production",
                "statuses": [{"state": "success", "created_at": recovered_at}],
            },
        ],
        now=now,
    )

    first_week = metrics["weekly"][0]
    assert first_week["deployments"] == 2
    assert first_week["successfulDeployments"] == 1
    assert first_week["failures"] == 1
    assert first_week["leadTimeHours"] == 12
    assert first_week["leadTimeSamples"] == 1
    assert first_week["restoreHours"] == 48
    assert first_week["restoreSamples"] == 1


def test_build_metrics_returns_empty_periods_without_fake_values():
    metrics = build_metrics([], [], now=datetime(2026, 10, 5, tzinfo=timezone.utc))

    assert len(metrics["weekly"]) == 12
    assert all(row["deployments"] == 0 for row in metrics["weekly"])
    assert all(row["successfulDeployments"] == 0 for row in metrics["weekly"])
    assert all(row["leadTimeHours"] is None for row in metrics["weekly"])
    assert all(row["restoreHours"] is None for row in metrics["weekly"])


def test_build_metrics_filters_to_configured_deployment_environments():
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    deployments = [
        {
            "created_at": "2026-07-14T10:00:00Z",
            "environment": "production",
            "statuses": [{"state": "success", "created_at": "2026-07-14T10:00:00Z"}],
        },
        {
            "created_at": "2026-07-14T10:00:00Z",
            "environment": "staging",
            "statuses": [{"state": "success", "created_at": "2026-07-14T10:00:00Z"}],
        },
        {
            "created_at": "2026-07-14T10:00:00Z",
            "environment": "production",
            "statuses": [{"state": "in_progress", "created_at": "2026-07-14T10:00:00Z"}],
        },
    ]

    metrics = build_metrics([], deployments, now=now, environments={"production"})

    assert metrics["weekly"][0]["deployments"] == 1
    assert metrics["environments"] == ["production"]