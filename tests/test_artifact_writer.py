from __future__ import annotations

import json
from pathlib import Path

import pytest

import daily3albums.artifact_writer as artifact_writer
from daily3albums.artifact_writer import OutputValidationError, write_daily_artifacts


def _pick(title: str, slot: str) -> dict:
    return {
        "slot": slot,
        "title": title,
        "artist_credit": "Artist",
        "rg_mbid": f"rg-{title}",
        "cover": {
            "has_cover": True,
            "optimized_cover_url": f"covers/{title}.jpg",
        },
    }


def _issue(date: str, run_id: str, run_at: str) -> dict:
    pick_slots = ["Headliner", "Lineage", "DeepCut"]
    slots = [
        {
            "slot_id": slot_id,
            "window_label": label,
            "theme": f"Theme {slot_id}",
            "picks": [_pick(f"{date}-{slot_id}-{idx}", pick_slots[idx]) for idx in range(3)],
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


def test_writer_keeps_configured_recent_unique_archive_dates(tmp_path: Path):
    out = tmp_path / "public"
    index_path = out / "data" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            {
                "output_schema_version": "1",
                "items": [
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
                        "run_id": "day-5",
                        "run_at": "2026-06-21T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-20",
                        "run_id": "day-6",
                        "run_at": "2026-06-20T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-19",
                        "run_id": "day-7",
                        "run_at": "2026-06-19T06:00:00+08:00",
                    },
                    {
                        "date": "2026-06-18",
                        "run_id": "day-8",
                        "run_at": "2026-06-18T06:00:00+08:00",
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
    old_dates = [
        "2026-06-24",
        "2026-06-23",
        "2026-06-22",
        "2026-06-21",
        "2026-06-20",
        "2026-06-19",
        "2026-06-18",
    ]
    for date in old_dates:
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
        ("2026-06-22", "day-4"),
        ("2026-06-21", "day-5"),
        ("2026-06-20", "day-6"),
        ("2026-06-19", "day-7"),
    ]
    assert index["archive_retention_days"] == 7
    assert (old_archive / "2026-06-24").exists()
    assert (old_archive / "2026-06-23").exists()
    assert (old_archive / "2026-06-22").exists()
    assert (old_archive / "2026-06-19").exists()
    assert not (old_archive / "2026-06-18").exists()
    assert not (old_archive / "2026-06-18.json").exists()


def test_writer_reuses_existing_archive_date_on_normal_rerun(tmp_path: Path):
    out = tmp_path / "public"
    data_dir = out / "data"
    archive_dir = data_dir / "archive"
    index_path = data_dir / "index.json"
    index_path.parent.mkdir(parents=True)

    archive_bytes_by_date: dict[str, bytes] = {}
    published_issue = _issue(
        "2026-06-25",
        "published-run",
        "2026-06-25T06:00:00+08:00",
    )
    published_bytes = (
        json.dumps(published_issue, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )
    (archive_dir / "2026-06-25").mkdir(parents=True)
    (archive_dir / "2026-06-25" / "published-run.json").write_bytes(published_bytes)
    (archive_dir / "2026-06-25.json").write_bytes(published_bytes)
    archive_bytes_by_date["2026-06-25"] = published_bytes

    retained_items = [
        {
            "date": "2026-06-24",
            "run_id": "previous-day-1",
            "theme_of_day": "Previous 1",
            "run_at": "2026-06-24T06:00:00+08:00",
        },
        {
            "date": "2026-06-23",
            "run_id": "previous-day-2",
            "theme_of_day": "Previous 2",
            "run_at": "2026-06-23T06:00:00+08:00",
        },
        {
            "date": "2026-06-22",
            "run_id": "previous-day-3",
            "theme_of_day": "Previous 3",
            "run_at": "2026-06-22T06:00:00+08:00",
        },
    ]
    for item in retained_items:
        retained_issue = _issue(item["date"], item["run_id"], item["run_at"])
        retained_issue["theme_of_day"] = item["theme_of_day"]
        retained_bytes = (
            json.dumps(retained_issue, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        )
        (archive_dir / item["date"]).mkdir(parents=True)
        (archive_dir / item["date"] / f"{item['run_id']}.json").write_bytes(retained_bytes)
        (archive_dir / f"{item['date']}.json").write_bytes(retained_bytes)
        archive_bytes_by_date[item["date"]] = retained_bytes

    index_path.write_text(
        json.dumps(
            {
                "output_schema_version": "1",
                "items": [
                    {
                        "date": "2026-06-25",
                        "run_id": "published-run",
                        "theme_of_day": "Theme",
                        "run_at": "2026-06-25T06:00:00+08:00",
                    },
                    *retained_items,
                ],
            }
        ),
        encoding="utf-8",
    )

    generated_issue = _issue(
        "2026-06-25",
        "generated-rerun",
        "2026-06-25T12:00:00+08:00",
    )

    paths = write_daily_artifacts(generated_issue, out_public_dir=out)

    assert generated_issue["run_id"] == "published-run"
    assert not (archive_dir / "2026-06-25" / "generated-rerun.json").exists()
    assert (data_dir / "today.json").read_bytes() == published_bytes
    assert (archive_dir / "2026-06-25" / "published-run.json").read_bytes() == published_bytes
    assert (archive_dir / "2026-06-25.json").read_bytes() == published_bytes
    assert paths["archive"] == archive_dir / "2026-06-25" / "published-run.json"

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert [(item["date"], item["run_id"]) for item in index["items"]] == [
        ("2026-06-25", "published-run"),
        ("2026-06-24", "previous-day-1"),
        ("2026-06-23", "previous-day-2"),
        ("2026-06-22", "previous-day-3"),
    ]
    for item in retained_items:
        assert (archive_dir / item["date"] / f"{item['run_id']}.json").read_bytes() == (
            archive_bytes_by_date[item["date"]]
        )
        assert (archive_dir / f"{item['date']}.json").read_bytes() == archive_bytes_by_date[
            item["date"]
        ]


def test_writer_fails_if_kept_historical_archive_json_changes(tmp_path: Path, monkeypatch):
    out = tmp_path / "public"
    data_dir = out / "data"
    archive_dir = data_dir / "archive"
    index_path = data_dir / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            {
                "output_schema_version": "1",
                "items": [
                    {
                        "date": "2026-06-24",
                        "run_id": "previous-day",
                        "theme_of_day": "Previous",
                        "run_at": "2026-06-24T06:00:00+08:00",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    previous_issue = _issue(
        "2026-06-24",
        "previous-day",
        "2026-06-24T06:00:00+08:00",
    )
    previous_bytes = (
        json.dumps(previous_issue, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )
    (archive_dir / "2026-06-24").mkdir(parents=True)
    (archive_dir / "2026-06-24" / "previous-day.json").write_bytes(previous_bytes)
    (archive_dir / "2026-06-24.json").write_bytes(previous_bytes)

    original_prune = artifact_writer._prune_archive_files

    def corrupt_historical_archive(archive: Path, keep_dates: set[str]) -> None:
        original_prune(archive, keep_dates)
        (archive / "2026-06-24.json").write_text(
            '{"date":"2026-06-24","corrupt":true}\n',
            encoding="utf-8",
        )

    monkeypatch.setattr(artifact_writer, "_prune_archive_files", corrupt_historical_archive)

    with pytest.raises(OutputValidationError, match="historical archive JSON changed unexpectedly"):
        write_daily_artifacts(
            _issue("2026-06-25", "new-day", "2026-06-25T06:00:00+08:00"),
            out_public_dir=out,
        )
