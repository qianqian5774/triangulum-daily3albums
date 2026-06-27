from __future__ import annotations

from scripts.restore_static_archive_seed import _pages_base_url, _select_recent_unique_dates


def test_pages_base_url_uses_explicit_custom_domain_override(monkeypatch):
    monkeypatch.setenv("DAILY3ALBUMS_PAGES_BASE_URL", "https://triangulumdaily.space")

    assert _pages_base_url() == "https://triangulumdaily.space/"


def test_pages_base_url_keeps_project_pages_fallback_until_override(monkeypatch):
    monkeypatch.delenv("DAILY3ALBUMS_PAGES_BASE_URL", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "qianqian5774/triangulum-daily3albums")

    assert _pages_base_url() == "https://qianqian5774.github.io/triangulum-daily3albums/"


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
        {
            "date": f"2026-06-{day:02d}",
            "run_id": str(day),
            "run_at": f"2026-06-{day:02d}T06:00:00+08:00",
        }
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
