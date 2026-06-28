from __future__ import annotations

import json
from pathlib import Path

from scripts.recommendation_observability_summary import main, render_markdown


def _sample_payload() -> dict:
    slots = []
    for slot_id, window in enumerate(["06:00", "12:00", "18:00"]):
        slots.append(
            {
                "slot_id": slot_id,
                "window": window,
                "theme": f"tag-{slot_id}",
                "candidate_counts": {
                    "raw": 10,
                    "merged": 8,
                    "normalization_attempted": 7,
                    "normalized": 6,
                    "eligible": 4,
                    "final_picks": 3,
                },
                "source_share": {"lastfm": 8, "discogs": 1, "listenbrainz": 0, "multi_source": 1},
                "final_picks_by_source": {"lastfm": 3, "discogs": 0, "listenbrainz": 0, "multi_source": 0},
                "rejection_reasons": {
                    "various_artists": 0,
                    "unsupported_primary_type": 1,
                    "duplicate_album_same_day": 0,
                    "duplicate_artist_same_day": 0,
                    "artist_cooldown": 0,
                    "theme_cooldown": 0,
                    "musicbrainz_normalization_failed": 1,
                    "missing_required_metadata": 0,
                    "other": 0,
                },
                "final_picks": [],
            }
        )
    return {
        "schema_version": 1,
        "generation_mode": "generated",
        "candidate_funnel_rerun": True,
        "reused_archive_seed": False,
        "reused_archive_date": None,
        "reused_archive_run_id": None,
        "final_picks_source": "candidate_funnel",
        "date": "2026-06-27",
        "run_id": "run-1",
        "slots": slots,
        "final_pick_coverage": {
            "total": 9,
            "year_present": 9,
            "year_missing": 0,
            "region_status": "unavailable_in_current_pick_schema",
            "language_status": "unavailable_in_current_pick_schema",
        },
        "final_pick_metadata_coverage": {
            "total": 9,
            "rating_present": 2,
            "tags_present": 8,
            "wikipedia_overview_present": 1,
            "cover_present": 7,
            "musicbrainz_rg_mbid_present": 9,
            "artist_mbids_present": 9,
            "youtube_search_url_present": 9,
            "musicbrainz_url_present": 9,
            "cover_source_distribution": {"cover_art_archive": 7, "placeholder": 2},
        },
        "enrichment": {
            "musicbrainz_normalization_attempted": 21,
            "musicbrainz_normalization_success": 18,
            "musicbrainz_detail_attempted": 9,
            "musicbrainz_detail_success": 8,
            "cover_attempted": 9,
            "cover_success": 7,
            "wikipedia_overview_attempted": 2,
            "wikipedia_overview_success": 1,
            "discogs_candidate_source_attempted": True,
            "listenbrainz_candidate_source_attempted": True,
        },
        "notes": ["Observability only."],
    }


def test_render_markdown_includes_required_sections():
    text = render_markdown(_sample_payload())

    assert "## Recommendation Observability" in text
    assert "### Generation mode" in text
    assert "| Generation mode | generated |" in text
    assert "| Candidate funnel rerun | yes |" in text
    assert "### Candidate counts" in text
    assert "| 0 | 06:00 | tag-0 | 10 | 8 | 7 | 6 | 4 | 3 |" in text
    assert "### Source share" in text
    assert "### Rejection reasons" in text
    assert "### Final 9 picks metadata coverage" in text
    assert "### Enrichment success rate" in text
    assert "unavailable_in_current_pick_schema" in text
    assert "MusicBrainz normalization" in text


def test_render_markdown_explains_reused_archive_mode():
    payload = _sample_payload()
    payload.update(
        {
            "generation_mode": "reused_published_archive",
            "candidate_funnel_rerun": False,
            "reused_archive_seed": True,
            "reused_archive_date": "2026-06-27",
            "reused_archive_run_id": "published-run",
            "final_picks_source": "published_archive_seed",
            "run_id": "published-run",
            "archive_lock": {
                "reused_published_date": True,
                "published_date": "2026-06-27",
                "published_run_id": "published-run",
                "discarded_generated_run_id": "generated-rerun",
            },
        }
    )
    for slot in payload["slots"]:
        slot["candidate_counts"].update(
            {
                "raw": 0,
                "merged": 0,
                "normalization_attempted": 0,
                "normalized": 0,
                "eligible": 0,
                "final_picks": 3,
            }
        )

    text = render_markdown(payload)

    assert "| Generation mode | reused_published_archive |" in text
    assert "| Candidate funnel rerun | no |" in text
    assert "| Final picks source | published_archive_seed |" in text
    assert "| Reused archive date | 2026-06-27 |" in text
    assert "| Reused archive run | published-run |" in text
    assert "Candidate funnel: not rerun; final picks were restored from the published archive seed." in text
    assert "| 0 | 06:00 | tag-0 | 0 | 0 | 0 | 0 | 0 | 3 |" in text


def test_render_markdown_handles_legacy_payload_without_generation_fields():
    payload = _sample_payload()
    for key in (
        "generation_mode",
        "candidate_funnel_rerun",
        "reused_archive_seed",
        "reused_archive_date",
        "reused_archive_run_id",
        "final_picks_source",
    ):
        payload.pop(key, None)

    text = render_markdown(payload)

    assert "### Generation mode" not in text
    assert "### Candidate counts" in text
    assert "| 0 | 06:00 | tag-0 | 10 | 8 | 7 | 6 | 4 | 3 |" in text


def test_main_writes_github_summary_file(tmp_path: Path):
    payload_path = tmp_path / "recommendation-observability.json"
    summary_path = tmp_path / "summary.md"
    payload_path.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    rc = main(["--path", str(payload_path), "--github-summary", "--summary-file", str(summary_path)])

    assert rc == 0
    assert "Recommendation Observability" in summary_path.read_text(encoding="utf-8")
