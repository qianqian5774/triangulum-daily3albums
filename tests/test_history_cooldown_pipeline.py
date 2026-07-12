from __future__ import annotations

import json
from pathlib import Path

import pytest

from daily3albums.constraints import HistoryLoadError, album_key_from_parts, load_history_index


def _pick(index: int, *, rg_mbid: str | None = None, album_key: str | None = None) -> dict:
    payload = {
        "title": f"Album {index}",
        "artist_credit": f"Artist {index}",
        "artist_mbids": [f"artist-{index}"],
        "artist_keys": [f"artist-{index}"],
        "first_release_year": 2000 + index,
        "style_key": "ambient",
    }
    if rg_mbid is not None:
        payload["rg_mbid"] = rg_mbid
    if album_key is not None:
        payload["album_key"] = album_key
    return payload


def _issue(date_key: str, run_id: str, *, target_in_slot: int = 2, fallback_target: bool = False) -> dict:
    slots = []
    next_index = 0
    for slot_id in range(3):
        picks = []
        for _ in range(3):
            rg_mbid = f"rg-{date_key}-{next_index}"
            album_key = None
            if slot_id == target_in_slot and len(picks) == 1:
                if fallback_target:
                    rg_mbid = None
                    album_key = album_key_from_parts("", "Legacy Album", "Legacy Artist", 1999)
                else:
                    rg_mbid = "rg-target"
            picks.append(_pick(next_index, rg_mbid=rg_mbid, album_key=album_key))
            if album_key:
                picks[-1].update(
                    {
                        "title": "Legacy Album",
                        "artist_credit": "Legacy Artist",
                        "first_release_year": 1999,
                    }
                )
            next_index += 1
        slots.append(
            {
                "slot_id": slot_id,
                "theme": "ambient" if slot_id == target_in_slot else f"tag-{slot_id}",
                "theme_key": "ambient" if slot_id == target_in_slot else f"tag-{slot_id}",
                "picks": picks,
            }
        )
    return {
        "output_schema_version": "1.0",
        "date": date_key,
        "run_id": run_id,
        "theme_of_day": "fixture",
        "top_level_note": "top-level picks intentionally omit rg-target",
        "picks": slots[0]["picks"],
        "slots": slots,
    }


def _write_history(data_dir: Path, issues: list[dict], *, aliases: bool = True) -> dict[Path, bytes]:
    items = []
    snapshots: dict[Path, bytes] = {}
    for issue in issues:
        date_key = issue["date"]
        run_id = issue["run_id"]
        data = (json.dumps(issue, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        nested = data_dir / "archive" / date_key / f"{run_id}.json"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_bytes(data)
        snapshots[nested] = data
        if aliases:
            alias = data_dir / "archive" / f"{date_key}.json"
            alias.write_bytes(data)
            snapshots[alias] = data
        items.append(
            {
                "date": date_key,
                "run_id": run_id,
                "run_at": f"{date_key}T06:00:00+08:00",
            }
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "index.json").write_text(
        json.dumps({"output_schema_version": "1.0", "items": items}),
        encoding="utf-8",
    )
    return snapshots


def test_history_loader_reads_complete_slots_and_counts_alias_once(tmp_path: Path):
    data_dir = tmp_path / "data"
    _write_history(data_dir, [_issue("2026-07-11", "run-1", target_in_slot=2)])

    history = load_history_index(
        data_dir,
        current_date_key="2026-07-12",
        max_lookback_days=7,
        source="external_seed",
    )

    assert history.source == "external_seed"
    assert history.dates == ("2026-07-11",)
    assert history.archive_count == 1
    assert history.picks_loaded == 9
    assert history.album_last_seen["rg-target"] == "2026-07-11"
    assert history.album_identity_kind["rg-target"] == "rg_mbid"
    assert history.artist_last_seen["artist-7"] == "2026-07-11"
    assert history.style_last_seen["ambient"] == "2026-07-11"


@pytest.mark.parametrize(
    ("history_date", "expected_loaded"),
    [
        ("2026-07-11", True),
        ("2026-07-09", True),
        ("2026-07-05", True),
        ("2026-07-04", False),
    ],
)
def test_album_history_uses_bjt_natural_date_window(
    tmp_path: Path,
    history_date: str,
    expected_loaded: bool,
):
    data_dir = tmp_path / history_date
    _write_history(data_dir, [_issue(history_date, "run-1")], aliases=False)

    history = load_history_index(data_dir, "2026-07-12", max_lookback_days=7)

    assert ("rg-target" in history.album_last_seen) is expected_loaded


def test_history_loader_uses_stable_fallback_identity_for_legacy_pick(tmp_path: Path):
    data_dir = tmp_path / "data"
    issue = _issue("2026-07-09", "legacy", fallback_target=True)
    _write_history(data_dir, [issue])
    expected_key = album_key_from_parts("", "Legacy Album", "Legacy Artist", 1999)

    history = load_history_index(data_dir, "2026-07-12", max_lookback_days=7)

    assert history.album_last_seen[expected_key] == "2026-07-09"
    assert history.album_identity_kind[expected_key] == "fallback"
    assert history.album_identity_counts()["fallback"] == 1


def test_history_loader_allows_explicit_empty_index(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "index.json").write_text('{"output_schema_version":"1.0","items":[]}', encoding="utf-8")

    history = load_history_index(data_dir, "2026-07-12", source="external_seed")

    assert history.source == "external_seed"
    assert history.archive_count == 0
    assert history.picks_loaded == 0


@pytest.mark.parametrize(
    "items",
    [
        [{"date": "invalid", "run_id": "bad"}],
        [{"date": "2026-07-13", "run_id": "future"}],
    ],
)
def test_history_loader_rejects_invalid_or_future_index_dates(tmp_path: Path, items: list[dict]):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "index.json").write_text(json.dumps({"items": items}), encoding="utf-8")

    with pytest.raises(HistoryLoadError):
        load_history_index(data_dir, "2026-07-12", source="external_seed")


def test_history_loader_does_not_treat_missing_external_seed_as_first_run(tmp_path: Path):
    with pytest.raises(HistoryLoadError, match="source directory is missing"):
        load_history_index(tmp_path / "missing", "2026-07-12", source="external_seed")
