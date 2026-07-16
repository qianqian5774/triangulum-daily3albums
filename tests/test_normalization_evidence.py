from __future__ import annotations

from scripts.normalization_evidence import sanitize_observability


def test_candidate_evidence_is_allowlisted_and_sanitized():
    payload = {
        "date": "2026-07-16",
        "run_id": "run-1",
        "commit_sha": "abc123",
        "generation_mode": "generated",
        "candidate_funnel_rerun": True,
        "normalization_policy_enforced": True,
        "normalization_shadow": {
            "production_sample_eligible": True,
            "authority": "config.normalizer",
            "policy_version": "td02b-v1",
            "min_confidence": 0.82,
        },
        "slots": [
            {
                "slot_id": 0,
                "theme": "ambient",
                "fallback": {
                    "stage": 0,
                    "candidate_scope_expanded": False,
                    "additional_requests": 0,
                    "unsafe_internal": "must not leak",
                },
                "normalization_shadow": {
                    "status": "enforced",
                    "tier_counts": {"strict": 2, "borderline": 1, "hard_reject": 1},
                    "candidates": [
                        {
                            "candidate_key": "rg:one",
                            "release_group_mbid": "one",
                            "artist_keys": ["artist:one"],
                            "score": 101.0,
                            "policy_tier": "strict",
                            "policy_reason": "text_identity_confident",
                            "in_final_picks": True,
                            "title": "must not leak",
                            "artist": "must not leak",
                            "query": "must not leak",
                            "image_url": "https://example.invalid/secret",
                            "debug": {"raw_response": "must not leak"},
                        }
                    ],
                },
            }
        ],
    }

    evidence = sanitize_observability(payload)

    assert evidence["artifact_kind"] == "td02b_normalization_candidate_evidence"
    assert evidence["production_sample_eligible"] is True
    row = evidence["slots"][0]["candidates"][0]
    assert evidence["slots"][0]["fallback"] == {
        "stage": 0,
        "candidate_scope_expanded": False,
        "additional_requests": 0,
    }
    artist_ref = row.pop("artist_keys")[0]
    assert artist_ref.startswith("sha256:")
    assert row == {
        "candidate_key": "rg:one",
        "release_group_mbid": "one",
        "score": 101.0,
        "policy_tier": "strict",
        "policy_reason": "text_identity_confident",
        "in_final_picks": True,
    }
    serialized = str(evidence)
    for forbidden in ("must not leak", "example.invalid", "raw_response"):
        assert forbidden not in serialized
