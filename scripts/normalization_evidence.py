from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any


_CANDIDATE_FIELDS = (
    "candidate_key",
    "release_group_mbid",
    "artist_keys",
    "score",
    "path",
    "query_strategy",
    "best_confidence",
    "second_best_confidence",
    "has_second_best",
    "ambiguity_gap",
    "identity_title_similarity",
    "identity_artist_similarity",
    "runner_release_group_mbid",
    "runner_same_work",
    "policy_tier",
    "policy_reason",
    "in_normalized_pool",
    "in_eligible_pool",
    "in_final_picks",
)


def _safe_artist_keys(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    safe: list[str] = []
    for item in value:
        key = str(item or "").strip()
        if not key:
            continue
        try:
            safe.append(str(uuid.UUID(key)))
        except ValueError:
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            safe.append(f"sha256:{digest}")
    return safe


def _sanitize_candidate(row: dict[str, Any]) -> dict[str, Any]:
    sanitized = {key: row.get(key) for key in _CANDIDATE_FIELDS if key in row}
    if "artist_keys" in sanitized:
        sanitized["artist_keys"] = _safe_artist_keys(sanitized["artist_keys"])
    return sanitized


def sanitize_observability(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("normalization_shadow")
    metadata = metadata if isinstance(metadata, dict) else {}
    slots: list[dict[str, Any]] = []
    for slot in payload.get("slots", []):
        if not isinstance(slot, dict):
            continue
        raw = slot.get("normalization_shadow")
        raw = raw if isinstance(raw, dict) else {}
        fallback = slot.get("fallback")
        fallback = fallback if isinstance(fallback, dict) else {}
        candidates = raw.get("candidates")
        candidates = candidates if isinstance(candidates, list) else []
        slots.append(
            {
                "slot_id": slot.get("slot_id"),
                "theme": slot.get("theme"),
                "status": raw.get("status"),
                "tier_counts": dict(raw.get("tier_counts") or {}),
                "strict_eligible": raw.get("strict_eligible"),
                "strict_pool_insufficient": raw.get("strict_pool_insufficient"),
                "borderline_admitted": raw.get("borderline_admitted"),
                "borderline_final_picks": raw.get("borderline_final_picks"),
                "hard_reject_count": raw.get("hard_reject_count"),
                "fallback": {
                    key: fallback.get(key)
                    for key in (
                        "stage",
                        "candidate_scope_expanded",
                        "expansion_before",
                        "expansion_after",
                        "additional_requests",
                    )
                    if key in fallback
                },
                "candidates": [
                    _sanitize_candidate(row)
                    for row in candidates
                    if isinstance(row, dict)
                ],
            }
        )

    return {
        "schema_version": 1,
        "artifact_kind": "td02b_normalization_candidate_evidence",
        "date": payload.get("date"),
        "run_id": payload.get("run_id"),
        "commit_sha": payload.get("commit_sha"),
        "generation_mode": payload.get("generation_mode"),
        "candidate_funnel_rerun": payload.get("candidate_funnel_rerun"),
        "production_sample_eligible": metadata.get("production_sample_eligible") is True,
        "normalization_policy_enforced": payload.get("normalization_policy_enforced") is True,
        "policy": {
            key: metadata.get(key)
            for key in (
                "authority",
                "policy_version",
                "min_confidence",
                "hard_confidence_floor",
                "ambiguity_gap",
                "identity_title_floor",
                "identity_artist_floor",
                "hard_ambiguity_policy",
            )
            if key in metadata
        },
        "slots": slots,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a sanitized TD-02B candidate-level normalization evidence artifact."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("normalization evidence input must be a JSON object")
    evidence = sanitize_observability(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
