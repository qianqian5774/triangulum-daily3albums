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


def test_select_recent_unique_dates_can_keep_seven_days():
    items = [
        {"date": f"2026-06-{day:02d}", "run_id": str(day), "run_at": f"2026-06-{day:02d}T06:00:00+08:00"}
        for day in range(18, 26)
    ]

    selected = _select_recent_unique_dates(items, max_days=7)

    assert [item["date"] for item in selected] == [
        "2026-06-25",
        "2026-06-24",
        "2026-06-23",
        "2026-06-22",
        "2026-06-21",
        "2026-06-20",
        "2026-06-19",
    ]
