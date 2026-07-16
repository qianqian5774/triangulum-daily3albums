from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


STRICT = "strict"
BORDERLINE = "borderline"
HARD_REJECT = "hard_reject"


@dataclass(frozen=True)
class NormalizationPolicy:
    policy_version: str
    min_confidence: float
    hard_confidence_floor: float
    ambiguity_gap: float
    identity_title_floor: float
    identity_artist_floor: float
    hard_ambiguity_policy: str

    @classmethod
    def defaults(cls) -> "NormalizationPolicy":
        return cls(
            policy_version="td02b-v1",
            min_confidence=0.82,
            hard_confidence_floor=0.78,
            ambiguity_gap=0.08,
            identity_title_floor=0.60,
            identity_artist_floor=0.50,
            hard_ambiguity_policy="reject_distinct",
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "NormalizationPolicy":
        raw = value or {}
        default = cls.defaults()
        policy = cls(
            policy_version=str(raw.get("policy_version", default.policy_version)).strip(),
            min_confidence=float(raw.get("min_confidence", default.min_confidence)),
            hard_confidence_floor=float(
                raw.get("hard_confidence_floor", default.hard_confidence_floor)
            ),
            ambiguity_gap=float(raw.get("ambiguity_gap", default.ambiguity_gap)),
            identity_title_floor=float(
                raw.get("identity_title_floor", default.identity_title_floor)
            ),
            identity_artist_floor=float(
                raw.get("identity_artist_floor", default.identity_artist_floor)
            ),
            hard_ambiguity_policy=str(
                raw.get("hard_ambiguity_policy", default.hard_ambiguity_policy)
            ).strip(),
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        if not self.policy_version:
            raise ValueError("normalizer.policy_version must not be empty")
        for name in (
            "min_confidence",
            "hard_confidence_floor",
            "ambiguity_gap",
            "identity_title_floor",
            "identity_artist_floor",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"normalizer.{name} must be between 0 and 1")
        if self.hard_confidence_floor > self.min_confidence:
            raise ValueError(
                "normalizer.hard_confidence_floor must not exceed min_confidence"
            )
        if self.hard_ambiguity_policy != "reject_distinct":
            raise ValueError(
                "normalizer.hard_ambiguity_policy must be 'reject_distinct'"
            )

    def public_thresholds(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "min_confidence": self.min_confidence,
            "hard_confidence_floor": self.hard_confidence_floor,
            "ambiguity_gap": self.ambiguity_gap,
            "identity_title_floor": self.identity_title_floor,
            "identity_artist_floor": self.identity_artist_floor,
            "hard_ambiguity_policy": self.hard_ambiguity_policy,
        }


@dataclass(frozen=True)
class NormalizationDecision:
    tier: str
    reason: str

    @property
    def admitted(self) -> bool:
        return self.tier != HARD_REJECT

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "reason": self.reason,
            "admitted": self.admitted,
        }


def _number(trace: Mapping[str, Any], key: str) -> float | None:
    value = trace.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_normalization_trace(
    trace: Mapping[str, Any] | None,
    policy: NormalizationPolicy,
) -> NormalizationDecision:
    if not isinstance(trace, Mapping):
        return NormalizationDecision(HARD_REJECT, "missing_normalization_trace")

    title_similarity = _number(trace, "identity_title_similarity")
    artist_similarity = _number(trace, "identity_artist_similarity")
    identity_prevalidated = trace.get("identity_prevalidated") is True
    if not identity_prevalidated:
        if title_similarity is None or title_similarity < policy.identity_title_floor:
            return NormalizationDecision(HARD_REJECT, "identity_title_mismatch")
        if artist_similarity is None or artist_similarity < policy.identity_artist_floor:
            return NormalizationDecision(HARD_REJECT, "identity_artist_mismatch")

    path = str(trace.get("path") or "")
    if path in {
        "direct_release_group_mbid",
        "release_mbid_to_release_group",
        "external_release_group_hint",
    }:
        return NormalizationDecision(STRICT, "entity_and_identity_verified")

    if path != "musicbrainz_text_search":
        return NormalizationDecision(HARD_REJECT, "unsupported_normalization_path")

    confidence = _number(trace, "best_confidence") or 0.0
    if confidence < policy.hard_confidence_floor:
        return NormalizationDecision(HARD_REJECT, "below_hard_confidence_floor")

    gap = _number(trace, "ambiguity_gap")
    has_runner = trace.get("has_second_best") is True
    if has_runner and gap is not None and gap < policy.ambiguity_gap:
        if trace.get("runner_same_work") is True:
            return NormalizationDecision(BORDERLINE, "ambiguous_equivalent_work")
        return NormalizationDecision(HARD_REJECT, "ambiguous_distinct_work")

    strategy = str(trace.get("query_strategy") or "")
    if strategy in {"cleaned_loose", "title_only"}:
        return NormalizationDecision(BORDERLINE, f"riskier_query_strategy:{strategy}")
    if strategy not in {"strict", "cleaned_strict"}:
        return NormalizationDecision(HARD_REJECT, "unknown_query_strategy")
    if confidence < policy.min_confidence:
        return NormalizationDecision(BORDERLINE, "below_strict_confidence")
    return NormalizationDecision(STRICT, "text_identity_confident")
