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
    assert "### Candidate counts" in text
    assert "### Source share" in text
    assert "### Rejection reasons" in text
    assert "### Final 9 picks metadata coverage" in text
    assert "### Enrichment success rate" in text
    assert "unavailable_in_current_pick_schema" in text
    assert "MusicBrainz normalization" in text


def test_main_writes_github_summary_file(tmp_path: Path):
    payload_path = tmp_path / "recommendation-observability.json"
    summary_path = tmp_path / "summary.md"
    payload_path.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    rc = main(["--path", str(payload_path), "--github-summary", "--summary-file", str(summary_path)])

    assert rc == 0
    assert "Recommendation Observability" in summary_path.read_text(encoding="utf-8")
