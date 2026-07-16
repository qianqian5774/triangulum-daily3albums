from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from daily3albums.normalization_policy import (
    BORDERLINE,
    HARD_REJECT,
    STRICT,
    NormalizationPolicy,
    evaluate_normalization_trace,
)


def _trace(**overrides):
    trace = {
        "path": "musicbrainz_text_search",
        "query_strategy": "strict",
        "best_confidence": 0.90,
        "second_best_confidence": None,
        "has_second_best": False,
        "ambiguity_gap": None,
        "identity_title_similarity": 0.95,
        "identity_artist_similarity": 0.95,
        "runner_same_work": None,
    }
    trace.update(overrides)
    return trace


@pytest.mark.parametrize(
    ("trace", "tier", "reason"),
    [
        (_trace(), STRICT, "text_identity_confident"),
        (_trace(best_confidence=0.80), BORDERLINE, "below_strict_confidence"),
        (_trace(best_confidence=0.77), HARD_REJECT, "below_hard_confidence_floor"),
        (_trace(query_strategy="cleaned_loose"), BORDERLINE, "riskier_query_strategy:cleaned_loose"),
        (
            _trace(has_second_best=True, ambiguity_gap=0.02, runner_same_work=True),
            BORDERLINE,
            "ambiguous_equivalent_work",
        ),
        (
            _trace(has_second_best=True, ambiguity_gap=0.02, runner_same_work=False),
            HARD_REJECT,
            "ambiguous_distinct_work",
        ),
        (
            _trace(identity_artist_similarity=0.30),
            HARD_REJECT,
            "identity_artist_mismatch",
        ),
        (
            _trace(
                path="direct_release_group_mbid",
                query_strategy=None,
                best_confidence=1.0,
            ),
            STRICT,
            "entity_and_identity_verified",
        ),
    ],
)
def test_policy_tiers(trace, tier, reason):
    decision = evaluate_normalization_trace(trace, NormalizationPolicy.defaults())
    assert (decision.tier, decision.reason) == (tier, reason)


def test_production_sample_replays_all_candidates_and_final_pick_impact():
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "normalization"
        / "r6-production-sample-29454605202.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    policy = NormalizationPolicy.defaults()
    total = 0
    slot_results = []

    for slot in fixture["slots"]:
        evaluated = []
        for key, strategy, best, second, eligible, final, runner_same_work in slot["rows"]:
            trace = {
                "path": "musicbrainz_text_search",
                "query_strategy": strategy,
                "best_confidence": best,
                "second_best_confidence": second,
                "has_second_best": second is not None,
                "ambiguity_gap": round(best - second, 6) if second is not None else None,
                "identity_prevalidated": True,
                "runner_same_work": runner_same_work,
            }
            evaluated.append(
                {
                    "key": key,
                    "eligible": eligible,
                    "final": final,
                    "decision": evaluate_normalization_trace(trace, policy),
                }
            )
        total += len(evaluated)
        eligible_rows = [row for row in evaluated if row["eligible"]]
        strict = [row for row in eligible_rows if row["decision"].tier == STRICT]
        borderline = [row for row in eligible_rows if row["decision"].tier == BORDERLINE]
        admitted = strict if len(strict) >= 3 else [*strict, *borderline[: 3 - len(strict)]]
        previous_final = {row["key"] for row in evaluated if row["final"]}
        admitted_keys = {row["key"] for row in admitted}
        slot_results.append(
            {
                "slot_id": slot["slot_id"],
                "tiers": Counter(row["decision"].tier for row in evaluated),
                "previous_final": previous_final,
                "admitted": admitted_keys,
            }
        )

    assert total == 54
    slot0 = slot_results[0]
    assert slot0["tiers"][HARD_REJECT] == 1
    assert slot0["admitted"] == {
        "4748ad7f-7973-4e98-bd76-a09de7885fd5",
        "ac6330e4-da62-4c2b-b3b0-c2266bb4bdd2",
        "baaa6aae-78b8-4a40-800c-475a4ed60701",
    }
    assert "29ff1628-8523-4a82-ab6a-823e792174d4" in slot0["previous_final"]
    for result in slot_results[1:]:
        assert result["previous_final"] <= result["admitted"]
        assert result["tiers"][HARD_REJECT] == 0
    assert fixture["additional_requests"] == 0
    assert fixture["fallback_stage"] == 0
