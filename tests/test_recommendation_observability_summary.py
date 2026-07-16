from __future__ import annotations

import json
from pathlib import Path

from daily3albums.runtime_outcomes import OutcomeCode
from scripts import recommendation_observability_summary as summary
from scripts.recommendation_observability_summary import main, render_markdown, render_result


def _sample_payload() -> dict:
    slots = []
    for slot_id, window in enumerate(["08:00", "12:30", "16:00"]):
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
                    "album_cooldown": 2,
                    "artist_cooldown": 0,
                    "theme_cooldown": 0,
                    "musicbrainz_normalization_failed": 1,
                    "missing_required_metadata": 0,
                    "other": 0,
                },
                "history_context": {
                    "source": "external_seed",
                    "dates_loaded": ["2026-06-26"],
                    "archive_count": 1,
                    "picks_loaded": 9,
                },
                "fallback": {
                    "stage": 0,
                    "candidate_scope_expanded": False,
                    "expansion_before": 0,
                    "expansion_after": 0,
                    "additional_requests": 0,
                    "album_cooldown_days": 7,
                    "artist_cooldown_days": 7,
                    "theme_cooldown_days": 3,
                    "stage3_used": False,
                },
                "normalization_shadow": {
                    "status": "observed_not_enforced",
                    "references": {
                        "cli_reference": {
                            "min_confidence": 0.80,
                            "ambiguity_gap": 0.06,
                            "text_search_evaluated": 4,
                            "rejected_total": 2,
                            "rejected_low_confidence": 1,
                            "rejected_ambiguous": 1,
                            "normalized_remaining": 4,
                            "eligible_remaining": 2,
                            "final_picks_impacted": 1,
                            "possible_higher_fallback": True,
                        },
                        "config_reference": {
                            "min_confidence": 0.72,
                            "ambiguity_gap": 0.08,
                            "text_search_evaluated": 4,
                            "rejected_total": 1,
                            "rejected_low_confidence": 0,
                            "rejected_ambiguous": 1,
                            "normalized_remaining": 5,
                            "eligible_remaining": 3,
                            "final_picks_impacted": 0,
                            "possible_higher_fallback": False,
                        },
                    },
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
        "normalization_shadow": {
            "status": "observed_not_enforced",
            "enforced": False,
            "production_sample_eligible": True,
        },
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
    assert "### Normalization shadow observation" in text
    assert "| 0 | cli_reference | 0.8 | 0.06 | 4 | 2 | 1 | 1 | 4 | 2 | 1 | yes |" in text
    assert "| 0 | 08:00 | tag-0 | 10 | 8 | 7 | 6 | 4 | 3 |" in text
    assert "### Source share" in text
    assert "### History and cooldown fallback" in text
    assert "| 0 | external_seed | 2026-06-26 | 1 | 9 | 0 | no | 0 / 0 | 0 | 7 | 7 | 3 | no |" in text
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
            "normalization_shadow": {
                "status": "not_available_reused_published_archive",
                "enforced": False,
                "production_sample_eligible": False,
            },
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
    assert "Normalization shadow data is not available for this reused published archive." in text
    assert "| 0 | 08:00 | tag-0 | 0 | 0 | 0 | 0 | 0 | 3 |" in text


def test_render_markdown_handles_legacy_payload_without_generation_fields():
    payload = _sample_payload()
    for key in (
        "generation_mode",
        "candidate_funnel_rerun",
        "reused_archive_seed",
        "reused_archive_date",
        "reused_archive_run_id",
        "final_picks_source",
        "normalization_shadow",
    ):
        payload.pop(key, None)

    text = render_markdown(payload)

    assert "### Generation mode" not in text
    assert "### Candidate counts" in text
    assert "| 0 | 08:00 | tag-0 | 10 | 8 | 7 | 6 | 4 | 3 |" in text


def test_render_markdown_handles_old_slots_without_history_or_fallback_fields():
    payload = _sample_payload()
    for slot in payload["slots"]:
        slot.pop("history_context", None)
        slot.pop("fallback", None)
        slot.pop("normalization_shadow", None)

    text = render_markdown(payload)

    assert "### History and cooldown fallback" in text
    assert "| 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a / n/a | n/a | n/a | n/a | n/a | n/a |" in text


def test_main_writes_github_summary_file(tmp_path: Path):
    payload_path = tmp_path / "recommendation-observability.json"
    summary_path = tmp_path / "summary.md"
    payload_path.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    rc = main(["--path", str(payload_path), "--github-summary", "--summary-file", str(summary_path)])

    assert rc == 0
    assert "Recommendation Observability" in summary_path.read_text(encoding="utf-8")


def test_main_classifies_missing_artifact_without_changing_soft_github_policy(tmp_path: Path, capsys):
    missing = tmp_path / "missing.json"
    summary_path = tmp_path / "summary.md"

    assert main(["--path", str(missing)]) == 1
    assert main(
        ["--path", str(missing), "--github-summary", "--summary-file", str(summary_path)]
    ) == 0
    assert "Not available" in summary_path.read_text(encoding="utf-8")
    assert "was not found" in capsys.readouterr().out


def test_legacy_and_empty_artifacts_are_compatible_outcomes():
    legacy = _sample_payload()
    for key in ("generation_mode", "normalization_shadow", "final_pick_metadata_coverage"):
        legacy.pop(key, None)

    assert render_result(legacy).outcome.code == OutcomeCode.UNAVAILABLE
    assert render_result({}).outcome.code == OutcomeCode.LEGITIMATE_EMPTY
    assert render_result({}).value is not None


def test_main_classifies_corrupt_and_invalid_artifacts(tmp_path: Path, capsys):
    corrupt = tmp_path / "corrupt.json"
    invalid = tmp_path / "invalid.json"
    corrupt.write_text("not json", encoding="utf-8")
    invalid.write_text(json.dumps({"slots": {"wrong": True}}), encoding="utf-8")

    assert main(["--path", str(corrupt)]) == 1
    assert "code=corrupt" in capsys.readouterr().err
    assert main(["--path", str(invalid)]) == 1
    assert "code=invalid_schema" in capsys.readouterr().err


def test_main_classifies_summary_output_unavailable(tmp_path: Path, capsys):
    payload_path = tmp_path / "recommendation-observability.json"
    unavailable = tmp_path / "summary-directory"
    payload_path.write_text(json.dumps(_sample_payload()), encoding="utf-8")
    unavailable.mkdir()

    rc = main(
        ["--path", str(payload_path), "--github-summary", "--summary-file", str(unavailable)]
    )

    assert rc == 1
    assert "code=unavailable" in capsys.readouterr().err


def test_main_classifies_render_failure_without_raw_exception(tmp_path: Path, monkeypatch, capsys):
    payload_path = tmp_path / "recommendation-observability.json"
    payload_path.write_text(json.dumps(_sample_payload()), encoding="utf-8")
    monkeypatch.setattr(
        summary,
        "render_markdown",
        lambda _payload: (_ for _ in ()).throw(RuntimeError("raw secret should not render")),
    )

    assert main(["--path", str(payload_path)]) == 1
    error = capsys.readouterr().err
    assert "code=render_failed" in error
    assert "raw secret" not in error
