from __future__ import annotations

from pathlib import Path

import daily3albums.cli as cli


def _pick(title: str, slot: str) -> dict:
    return {
        "slot": slot,
        "title": title,
        "artist_credit": "Artist",
        "rg_mbid": f"rg-{title}",
        "first_release_year": 1999,
        "cover": {"has_cover": True, "source": "cover_art_archive"},
        "musicbrainz_url": f"https://musicbrainz.org/release-group/rg-{title}",
        "youtube_search_url": f"https://www.youtube.com/results?search_query={title}",
    }


def _archive_issue() -> dict:
    pick_slots = ["Headliner", "Lineage", "DeepCut"]
    return {
        "date": "2026-06-27",
        "run_id": "published-run",
        "slots": [
            {
                "slot_id": slot_id,
                "window_label": label,
                "theme": f"Theme {slot_id}",
                "picks": [_pick(f"album-{slot_id}-{idx}", pick_slots[idx]) for idx in range(3)],
            }
            for slot_id, label in enumerate(["06:00-11:59", "12:00-17:59", "18:00-23:59"])
        ],
    }


def test_generated_observability_labels_candidate_funnel_mode(tmp_path: Path):
    payload = cli._new_recommendation_observability(
        repo_root=tmp_path,
        issue={"date": "2026-06-27", "run_id": "generated-run"},
        slot_payloads=[],
        discogs_enabled=False,
    )

    assert payload["generation_mode"] == "generated"
    assert payload["candidate_funnel_rerun"] is True
    assert payload["reused_archive_seed"] is False
    assert payload["reused_archive_date"] is None
    assert payload["reused_archive_run_id"] is None
    assert payload["final_picks_source"] == "candidate_funnel"


def test_archive_lock_observability_labels_reused_published_archive(tmp_path: Path):
    payload = cli._archive_lock_observability(
        repo_root=tmp_path,
        issue=_archive_issue(),
        generated_run_id="generated-rerun",
    )

    assert payload["generation_mode"] == "reused_published_archive"
    assert payload["candidate_funnel_rerun"] is False
    assert payload["reused_archive_seed"] is True
    assert payload["reused_archive_date"] == "2026-06-27"
    assert payload["reused_archive_run_id"] == "published-run"
    assert payload["final_picks_source"] == "published_archive_seed"
    assert payload["archive_lock"] == {
        "reused_published_date": True,
        "published_date": "2026-06-27",
        "published_run_id": "published-run",
        "discarded_generated_run_id": "generated-rerun",
    }
    assert payload["final_pick_coverage"]["total"] == 9
    assert [slot["candidate_counts"]["raw"] for slot in payload["slots"]] == [0, 0, 0]
    assert [slot["candidate_counts"]["final_picks"] for slot in payload["slots"]] == [3, 3, 3]
