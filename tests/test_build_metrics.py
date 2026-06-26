from __future__ import annotations

import json
from pathlib import Path

from scripts.build_metrics import collect_public_metrics, format_bytes


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _issue(date: str, run_id: str) -> dict:
    return {
        "date": date,
        "run_id": run_id,
        "slots": [
            {"slot_id": slot_id, "picks": [{"title": f"{date}-{slot_id}-{idx}"} for idx in range(3)]}
            for slot_id in range(3)
        ],
        "picks": [{"title": "current"}],
    }


def test_format_bytes_uses_human_units():
    assert format_bytes(999) == "999 B"
    assert format_bytes(1536) == "1.50 KB"


def test_collect_public_metrics_counts_archive_and_today(tmp_path: Path):
    public = tmp_path / "public"
    data = public / "data"
    _write_json(data / "today.json", _issue("2026-06-25", "today"))
    _write_json(
        data / "index.json",
        {
            "output_schema_version": "1",
            "archive_retention_days": 7,
            "items": [
                {"date": "2026-06-25", "run_id": "today"},
                {"date": "2026-06-24", "run_id": "older"},
            ],
        },
    )
    _write_json(data / "archive" / "2026-06-25" / "today.json", _issue("2026-06-25", "today"))
    _write_json(data / "archive" / "2026-06-24.json", _issue("2026-06-24", "older"))

    metrics = collect_public_metrics(public)

    assert metrics["archive_retention_days"] == 7
    assert metrics["archive_day_count"] == 2
    assert metrics["archive_album_count"] == 18
    assert metrics["today_album_count"] == 9
    assert metrics["archive_missing_days"] == []
    assert metrics["public_size_bytes"] > 0
