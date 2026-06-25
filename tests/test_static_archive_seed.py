from __future__ import annotations

from scripts.restore_static_archive_seed import _select_recent_unique_dates


def test_select_recent_unique_dates_prefers_latest_run_per_day():
    items = [
        {"date": "2026-06-24", "run_id": "morning", "run_at": "2026-06-24T06:00:00+08:00"},
        {"date": "2026-06-25", "run_id": "morning", "run_at": "2026-06-25T06:00:00+08:00"},
        {"date": "2026-06-25", "run_id": "manual", "run_at": "2026-06-25T12:00:00+08:00"},
        {"date": "2026-06-23", "run_id": "previous", "run_at": "2026-06-23T06:00:00+08:00"},
        {"date": "2026-06-22", "run_id": "older", "run_at": "2026-06-22T06:00:00+08:00"},
    ]

    selected = _select_recent_unique_dates(items, max_days=3)

    assert [(item["date"], item["run_id"]) for item in selected] == [
        ("2026-06-25", "manual"),
        ("2026-06-24", "morning"),
        ("2026-06-23", "previous"),
    ]
