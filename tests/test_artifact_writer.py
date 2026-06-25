from __future__ import annotations

import json
from pathlib import Path

from daily3albums.artifact_writer import write_daily_artifacts


def _pick(title: str) -> dict:
    return {
        "slot": "Headliner",
        "title": title,
        "artist_credit": "Artist",
        "rg_mbid": f"rg-{title}",
        "cover": {
            "has_cover": True,
            "optimized_cover_url": f"covers/{title}.jpg",
        },
    }


def _issue(date: str, run_id: str, run_at: str) -> dict:
    slots = [
        {
            "slot_id": slot_id,
            "window_label": label,
            "theme": f"Theme {slot_id}",
            "picks": [_pick(f"{date}-{slot_id}-{idx}") for idx in range(3)],
        }
        for slot_id, label in enumerate(["06:00-11:59", "12:00-17:59", "18:00-23:59"])
    ]
    return {
        "output_schema_version": "1",
        "date": date,
        "run_id": run_id,
        "theme_of_day": "Theme",
        "run_at": run_at,
        "slots": slots,
        "picks": slots[0]["picks"],
    }


def test_writer_keeps_recent_three_unique_archive_dates(tmp_path: Path):
    out = tmp_path / "public"
    index_path = out / "data" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            {
                "output_schema_version": "1",
                "items": [
                    {
                        "date": "2026-06-25",
                        "run_id": "old-same-day",
                        "run_at": "2026-06-25T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-24",
                        "run_id": "day-2",
                        "run_at": "2026-06-24T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-23",
                        "run_id": "day-3",
                        "run_at": "2026-06-23T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-22",
                        "run_id": "day-4",
                        "run_at": "2026-06-22T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-21",
                        "run_id": "dev-seed-local",
                        "run_at": "2026-06-21T06:00:00+08:00",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    old_archive = out / "data" / "archive"
    for date in ["2026-06-24", "2026-06-23", "2026-06-22"]:
        (old_archive / date).mkdir(parents=True, exist_ok=True)
        (old_archive / date / "seed.json").write_text("{}", encoding="utf-8")
        (old_archive / f"{date}.json").write_text("{}", encoding="utf-8")

    write_daily_artifacts(
        _issue("2026-06-25", "new-same-day", "2026-06-25T12:00:00+08:00"),
        out_public_dir=out,
    )

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert [(item["date"], item["run_id"]) for item in index["items"]] == [
        ("2026-06-25", "new-same-day"),
        ("2026-06-24", "day-2"),
        ("2026-06-23", "day-3"),
    ]
    assert (old_archive / "2026-06-24").exists()
    assert (old_archive / "2026-06-23").exists()
    assert not (old_archive / "2026-06-22").exists()
    assert not (old_archive / "2026-06-22.json").exists()
