#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell(value: Any) -> str:
    text = str(value if value is not None else "n/a")
    return text.replace("|", "\\|").replace("\n", " ")


def _ratio(success: Any, attempted: Any) -> str:
    try:
        success_i = int(success or 0)
        attempted_i = int(attempted or 0)
    except (TypeError, ValueError):
        return "n/a"
    if attempted_i <= 0:
        return f"{success_i}/0"
    pct = success_i / attempted_i * 100
    return f"{success_i}/{attempted_i} ({pct:.0f}%)"


def _yes_no(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"


def _generation_mode(payload: dict[str, Any]) -> str | None:
    mode = payload.get("generation_mode")
    if isinstance(mode, str) and mode.strip():
        return mode.strip()
    archive_lock = payload.get("archive_lock") if isinstance(payload.get("archive_lock"), dict) else {}
    if archive_lock.get("reused_published_date") is True:
        return "reused_published_archive"
    return None


def _render_generation_mode(payload: dict[str, Any]) -> list[str]:
    has_generation_metadata = any(
        key in payload
        for key in (
            "generation_mode",
            "candidate_funnel_rerun",
            "reused_archive_seed",
            "reused_archive_date",
            "reused_archive_run_id",
            "final_picks_source",
            "archive_lock",
        )
    )
    if not has_generation_metadata:
        return []

    mode = _generation_mode(payload)
    archive_lock = payload.get("archive_lock") if isinstance(payload.get("archive_lock"), dict) else {}
    candidate_funnel_rerun = payload.get("candidate_funnel_rerun")
    if not isinstance(candidate_funnel_rerun, bool) and mode == "reused_published_archive":
        candidate_funnel_rerun = False

    reused_archive_seed = payload.get("reused_archive_seed")
    if not isinstance(reused_archive_seed, bool) and mode == "reused_published_archive":
        reused_archive_seed = True

    final_picks_source = payload.get("final_picks_source")
    if not isinstance(final_picks_source, str) and mode == "reused_published_archive":
        final_picks_source = "published_archive_seed"

    reused_archive_date = payload.get("reused_archive_date") or archive_lock.get("published_date") or payload.get("date")
    reused_archive_run_id = (
        payload.get("reused_archive_run_id")
        or archive_lock.get("published_run_id")
        or payload.get("run_id")
    )

    lines = [
        "",
        "### Generation mode",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Generation mode | {_cell(mode or 'unknown')} |",
        f"| Candidate funnel rerun | {_yes_no(candidate_funnel_rerun)} |",
        f"| Final picks source | {_cell(final_picks_source or 'n/a')} |",
    ]
    if mode == "reused_published_archive" or reused_archive_seed is True:
        lines.extend([
            f"| Reused archive seed | {_yes_no(reused_archive_seed)} |",
            f"| Reused archive date | {_cell(reused_archive_date)} |",
            f"| Reused archive run | {_cell(reused_archive_run_id)} |",
            "",
            "Candidate funnel: not rerun; final picks were restored from the published archive seed.",
        ])
    return lines


def _aggregate_rejections(slots: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for slot in slots:
        reasons = slot.get("rejection_reasons")
        if not isinstance(reasons, dict):
            continue
        for reason, value in reasons.items():
            try:
                out[str(reason)] = out.get(str(reason), 0) + int(value or 0)
            except (TypeError, ValueError):
                continue
    return out


def _render_normalization_shadow(payload: dict[str, Any], slots: list[dict[str, Any]]) -> list[str]:
    metadata = payload.get("normalization_shadow")
    slot_shadows = [
        (slot.get("slot_id"), slot.get("normalization_shadow"))
        for slot in slots
        if isinstance(slot.get("normalization_shadow"), dict)
    ]
    if not isinstance(metadata, dict) and not slot_shadows:
        return []

    status = metadata.get("status") if isinstance(metadata, dict) else None
    lines = ["", "### Normalization shadow observation", ""]
    if status == "not_available_reused_published_archive":
        lines.extend(
            [
                "Normalization shadow data is not available for this reused published archive.",
                "Final picks and public observability came from the published archive seed; any internal candidate funnel data was discarded, so this artifact is excluded from generated-run sampling.",
            ]
        )
        return lines

    lines.extend(
        [
            "Shadow thresholds are observed only; they are not enforced and do not alter filtering, scoring, sampling, or final picks.",
            "",
            "| Slot | Reference | Min confidence | Ambiguity gap | Text search evaluated | Rejected | Low confidence | Ambiguous | Normalized remaining | Eligible remaining | Final picks impacted | Possible higher fallback |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    rendered = 0
    for slot_id, shadow in slot_shadows:
        references = shadow.get("references") if isinstance(shadow, dict) else None
        if not isinstance(references, dict):
            continue
        for name in ("cli_reference", "config_reference"):
            impact = references.get(name)
            if not isinstance(impact, dict):
                continue
            rendered += 1
            lines.append(
                "| {slot} | {name} | {minimum} | {gap} | {evaluated} | {rejected} | {low} | {ambiguous} | {normalized} | {eligible} | {final} | {fallback} |".format(
                    slot=_cell(slot_id),
                    name=_cell(name),
                    minimum=_cell(impact.get("min_confidence")),
                    gap=_cell(impact.get("ambiguity_gap")),
                    evaluated=_cell(impact.get("text_search_evaluated", 0)),
                    rejected=_cell(impact.get("rejected_total", 0)),
                    low=_cell(impact.get("rejected_low_confidence", 0)),
                    ambiguous=_cell(impact.get("rejected_ambiguous", 0)),
                    normalized=_cell(impact.get("normalized_remaining", 0)),
                    eligible=_cell(impact.get("eligible_remaining", 0)),
                    final=_cell(impact.get("final_picks_impacted", 0)),
                    fallback=_yes_no(impact.get("possible_higher_fallback")),
                )
            )
    if rendered == 0:
        lines.append("| n/a | n/a | n/a | n/a | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |")
    return lines


def render_markdown(payload: dict[str, Any]) -> str:
    slots = [slot for slot in payload.get("slots", []) if isinstance(slot, dict)]
    coverage = payload.get("final_pick_coverage") if isinstance(payload.get("final_pick_coverage"), dict) else {}
    metadata = (
        payload.get("final_pick_metadata_coverage")
        if isinstance(payload.get("final_pick_metadata_coverage"), dict)
        else {}
    )
    enrichment = payload.get("enrichment") if isinstance(payload.get("enrichment"), dict) else {}

    lines = [
        "## Recommendation Observability",
        "",
        f"- Date: `{_cell(payload.get('date'))}`",
        f"- Run: `{_cell(payload.get('run_id'))}`",
        "- These metrics are observability only; recommendation weights and final-pick selection logic are not changed by them.",
    ]
    lines.extend(_render_generation_mode(payload))
    lines.extend(_render_normalization_shadow(payload, slots))
    lines.extend([
        "",
        "### Candidate counts",
        "",
        "| Slot | Window | Theme | Raw | Merged | MB attempted | MB normalized | Eligible | Final picks |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for slot in slots:
        counts = slot.get("candidate_counts") if isinstance(slot.get("candidate_counts"), dict) else {}
        lines.append(
            "| {slot} | {window} | {theme} | {raw} | {merged} | {attempted} | {normalized} | {eligible} | {final} |".format(
                slot=_cell(slot.get("slot_id")),
                window=_cell(slot.get("window")),
                theme=_cell(slot.get("theme")),
                raw=_cell(counts.get("raw", 0)),
                merged=_cell(counts.get("merged", 0)),
                attempted=_cell(counts.get("normalization_attempted", 0)),
                normalized=_cell(counts.get("normalized", 0)),
                eligible=_cell(counts.get("eligible", 0)),
                final=_cell(counts.get("final_picks", 0)),
            )
        )

    lines.extend([
        "",
        "### History and cooldown fallback",
        "",
        "| Slot | History source | Dates | Archives | History picks | Stage | Scope expanded | Expansion before / after | Additional requests | Album days | Artist days | Theme days | Stage 3 pick |",
        "|---:|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ])
    for slot in slots:
        history = slot.get("history_context") if isinstance(slot.get("history_context"), dict) else {}
        fallback = slot.get("fallback") if isinstance(slot.get("fallback"), dict) else {}
        dates = history.get("dates_loaded")
        date_text = ", ".join(str(value) for value in dates) if isinstance(dates, list) and dates else "n/a"
        lines.append(
            "| {slot} | {source} | {dates} | {archives} | {picks} | {stage} | {expanded} | {before} / {after} | {requests} | {album_days} | {artist_days} | {theme_days} | {stage3} |".format(
                slot=_cell(slot.get("slot_id")),
                source=_cell(history.get("source")),
                dates=_cell(date_text),
                archives=_cell(history.get("archive_count")),
                picks=_cell(history.get("picks_loaded")),
                stage=_cell(fallback.get("stage")),
                expanded=_yes_no(fallback.get("candidate_scope_expanded")),
                before=_cell(fallback.get("expansion_before")),
                after=_cell(fallback.get("expansion_after")),
                requests=_cell(fallback.get("additional_requests")),
                album_days=_cell(fallback.get("album_cooldown_days")),
                artist_days=_cell(fallback.get("artist_cooldown_days")),
                theme_days=_cell(fallback.get("theme_cooldown_days")),
                stage3=_yes_no(fallback.get("stage3_used")),
            )
        )
        stage3_pick = fallback.get("stage3_pick")
        if isinstance(stage3_pick, dict):
            lines.append(
                "|  | Stage 3 detail | {detail} |  |  |  |  |  |  |  |  |  |  |".format(
                    detail=_cell(
                        "slot={slot} rg={rg} identity={identity} history_date={history_date}".format(
                            slot=stage3_pick.get("slot_id"),
                            rg=stage3_pick.get("release_group_mbid") or "n/a",
                            identity=stage3_pick.get("identity_kind") or "n/a",
                            history_date=stage3_pick.get("history_date") or "n/a",
                        )
                    )
                )
            )

    lines.extend([
        "",
        "### Source share",
        "",
        "| Slot | Last.fm candidates | Discogs candidates | ListenBrainz candidates | Multi-source candidates | Final Last.fm | Final Discogs | Final ListenBrainz |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for slot in slots:
        share = slot.get("source_share") if isinstance(slot.get("source_share"), dict) else {}
        final = slot.get("final_picks_by_source") if isinstance(slot.get("final_picks_by_source"), dict) else {}
        lines.append(
            "| {slot} | {lastfm} | {discogs} | {listenbrainz} | {multi} | {flastfm} | {fdiscogs} | {flistenbrainz} |".format(
                slot=_cell(slot.get("slot_id")),
                lastfm=_cell(share.get("lastfm", 0)),
                discogs=_cell(share.get("discogs", 0)),
                listenbrainz=_cell(share.get("listenbrainz", 0)),
                multi=_cell(share.get("multi_source", 0)),
                flastfm=_cell(final.get("lastfm", 0)),
                fdiscogs=_cell(final.get("discogs", 0)),
                flistenbrainz=_cell(final.get("listenbrainz", 0)),
            )
        )

    rejections = _aggregate_rejections(slots)
    lines.extend(["", "### Rejection reasons", "", "| Reason | Count |", "|---|---:|"])
    for reason, count in sorted(rejections.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {_cell(reason)} | {count} |")
    if not rejections:
        lines.append("| none | 0 |")

    lines.extend([
        "",
        "### Final 9 picks metadata coverage",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total final picks | {_cell(coverage.get('total', metadata.get('total', 0)))} |",
        f"| Year present | {_cell(coverage.get('year_present', 0))} |",
        f"| Year missing | {_cell(coverage.get('year_missing', 0))} |",
        f"| MusicBrainz rating present | {_cell(metadata.get('rating_present', 0))} |",
        f"| MusicBrainz tags present | {_cell(metadata.get('tags_present', 0))} |",
        f"| Wikipedia overview present | {_cell(metadata.get('wikipedia_overview_present', 0))} |",
        f"| Cover present | {_cell(metadata.get('cover_present', 0))} |",
        f"| MusicBrainz release-group MBID present | {_cell(metadata.get('musicbrainz_rg_mbid_present', 0))} |",
        f"| Artist MBIDs present | {_cell(metadata.get('artist_mbids_present', 0))} |",
        f"| YouTube search link present | {_cell(metadata.get('youtube_search_url_present', 0))} |",
        f"| MusicBrainz link present | {_cell(metadata.get('musicbrainz_url_present', 0))} |",
        f"| Region/country | {_cell(coverage.get('region_status', 'unavailable'))} |",
        f"| Language | {_cell(coverage.get('language_status', 'unavailable'))} |",
    ])

    cover_dist = metadata.get("cover_source_distribution")
    if isinstance(cover_dist, dict) and cover_dist:
        lines.extend(["", "Cover source distribution:"])
        for source, count in sorted(cover_dist.items()):
            lines.append(f"- `{_cell(source)}`: {count}")

    lines.extend([
        "",
        "### Enrichment success rate",
        "",
        "| Stage | Success / attempted |",
        "|---|---:|",
        f"| MusicBrainz normalization | {_ratio(enrichment.get('musicbrainz_normalization_success'), enrichment.get('musicbrainz_normalization_attempted'))} |",
        f"| MusicBrainz detail | {_ratio(enrichment.get('musicbrainz_detail_success'), enrichment.get('musicbrainz_detail_attempted'))} |",
        f"| Cover Art Archive | {_ratio(enrichment.get('cover_success'), enrichment.get('cover_attempted'))} |",
        f"| Wikipedia overview | {_ratio(enrichment.get('wikipedia_overview_success'), enrichment.get('wikipedia_overview_attempted'))} |",
        f"| Discogs candidate source | {'attempted' if enrichment.get('discogs_candidate_source_attempted') else 'disabled/not attempted'} |",
        f"| ListenBrainz candidate source | {'failed' if enrichment.get('listenbrainz_candidate_source_failed') else ('attempted' if enrichment.get('listenbrainz_candidate_source_attempted') else 'not attempted')} |",
    ])

    notes = payload.get("notes")
    if isinstance(notes, list) and notes:
        lines.extend(["", "### Notes", ""])
        for note in notes:
            lines.append(f"- {_cell(note)}")

    return "\n".join(lines) + "\n"


def _write_summary(text: str, summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render recommendation observability JSON as Markdown.")
    parser.add_argument("--path", type=Path, default=Path("_build/public/data/recommendation-observability.json"))
    parser.add_argument("--github-summary", action="store_true", help="Append Markdown to $GITHUB_STEP_SUMMARY.")
    parser.add_argument("--summary-file", type=Path, default=None, help="Override GitHub summary file path.")
    args = parser.parse_args(argv)

    if not args.path.exists():
        text = f"## Recommendation Observability\n\nNot available: `{args.path}` was not found.\n"
        if args.github_summary:
            target = args.summary_file or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.getenv("GITHUB_STEP_SUMMARY") else None)
            if target is not None:
                _write_summary(text, target)
            print(text, end="")
            return 0
        print(text, file=sys.stderr, end="")
        return 1

    payload = _read_json(args.path)
    if not isinstance(payload, dict):
        print(f"Recommendation observability JSON must be an object: {args.path}", file=sys.stderr)
        return 1
    text = render_markdown(payload)
    if args.github_summary:
        target = args.summary_file or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.getenv("GITHUB_STEP_SUMMARY") else None)
        if target is None:
            print("GITHUB_STEP_SUMMARY is not set; printing to stdout.", file=sys.stderr)
        else:
            _write_summary(text, target)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
