from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from daily3albums import cli
from daily3albums import dry_run as dr
from daily3albums.adapters import LastFmTopAlbum, MbReleaseGroupSummary
from daily3albums.config import load_config


@dataclass
class _Env:
    lastfm_api_key: str = "key"
    mb_user_agent: str = "agent"
    discogs_token: str | None = None


class _Broker:
    def get_stats_snapshot(self):
        return {"MusicBrainzAdapter": {"requests": 0}}


def _rg(rg_id: str = "rg-1") -> MbReleaseGroupSummary:
    return MbReleaseGroupSummary(
        id=rg_id,
        artist_mbids=[f"artist-{rg_id}"],
        first_release_date="2000-01-01",
        primary_type="Album",
    )


@pytest.mark.parametrize(
    ("source", "expected_path"),
    [
        ("mbid:release-group", "direct_release_group_mbid"),
        ("mbid:release->rg", "release_mbid_to_release_group"),
    ],
)
def test_mbid_normalization_paths_are_classified(monkeypatch, source: str, expected_path: str):
    monkeypatch.setattr(dr, "musicbrainz_normalize_mbid_to_release_group", lambda *_args, **_kwargs: (_rg(), source))

    norm, diagnostics = dr._normalize_candidate(
        _Broker(),
        _Env(),
        dr.Candidate(title="Album", artist="Artist", lastfm_mbid="input-mbid"),
    )

    assert norm is not None
    assert diagnostics["normalization_trace"] == {
        "path": expected_path,
        "query_strategy": None,
        "best_confidence": 1.0,
        "second_best_confidence": None,
        "has_second_best": False,
        "ambiguity_gap": None,
        "shadow_comparison_applicable": False,
    }


def test_external_release_group_hint_path_is_classified(monkeypatch):
    monkeypatch.setattr(dr, "musicbrainz_get_release_group", lambda *_args, **_kwargs: _rg("hint-rg"))

    norm, diagnostics = dr._normalize_candidate(
        _Broker(),
        _Env(),
        dr.Candidate(title="Album", artist="Artist", rg_mbid_hint="hint-rg"),
    )

    assert norm is not None
    assert diagnostics["normalization_trace"]["path"] == "external_release_group_hint"
    assert diagnostics["normalization_trace"]["second_best_confidence"] is None
    assert diagnostics["normalization_trace"]["ambiguity_gap"] is None


@pytest.mark.parametrize(
    ("method", "strategy"),
    [
        ("search:strict", "strict"),
        ("search:clean_strict", "cleaned_strict"),
        ("search:clean_loose", "cleaned_loose"),
        ("search:title_only", "title_only"),
    ],
)
def test_text_search_query_strategies_and_runner_up_are_recorded(monkeypatch, method: str, strategy: str):
    match = SimpleNamespace(rg=_rg("search-rg"), confidence=0.81, method=method)
    monkeypatch.setattr(
        dr,
        "musicbrainz_best_release_group_match_debug",
        lambda *_args, **_kwargs: (match, 0.74, ["search:queries_attempted=1 query_cap_hit=false max=3"]),
    )

    norm, diagnostics = dr._normalize_candidate(_Broker(), _Env(), dr.Candidate(title="Album", artist="Artist"))

    assert norm is not None
    trace = diagnostics["normalization_trace"]
    assert trace["path"] == "musicbrainz_text_search"
    assert trace["query_strategy"] == strategy
    assert trace["best_confidence"] == 0.81
    assert trace["second_best_confidence"] == 0.74
    assert trace["has_second_best"] is True
    assert trace["ambiguity_gap"] == 0.07


def test_two_shadow_references_classify_low_confidence_and_ambiguity_without_enforcement():
    diagnostics = {
        "normalization_trace": dr._normalization_trace(
            source="search:strict",
            best_confidence=0.75,
            second_best_confidence=0.70,
        )
    }

    dr._attach_shadow_results(
        diagnostics,
        cli_min_confidence=0.80,
        cli_ambiguity_gap=0.06,
        config_min_confidence=0.72,
        config_ambiguity_gap=0.08,
    )

    references = diagnostics["normalization_shadow"]["references"]
    assert references["cli_reference"]["rejected"] is True
    assert references["cli_reference"]["reason"] == "low_confidence"
    assert references["config_reference"]["rejected"] is True
    assert references["config_reference"]["reason"] == "ambiguous"


def test_missing_runner_up_is_explicit_na_and_cannot_be_ambiguous():
    trace = dr._normalization_trace(source="search:title_only", best_confidence=0.75)
    result = dr._shadow_reference_result(trace, min_confidence=0.72, ambiguity_gap=0.08)

    assert trace["has_second_best"] is False
    assert trace["second_best_confidence"] is None
    assert trace["ambiguity_gap"] is None
    assert result == {
        "status": "evaluated",
        "rejected": False,
        "reason": "accepted",
        "low_confidence": False,
        "ambiguous": False,
    }


def _scored(rg_id: str, *, confidence: float, runner: float | None, path: str = "search:strict") -> dr.ScoredCandidate:
    candidate = dr.Candidate(title=f"Album {rg_id}", artist=f"Artist {rg_id}")
    normalized = dr.NormalizedCandidate(
        title=candidate.title,
        artist=candidate.artist,
        mb_release_group_id=rg_id,
        artist_mbids=[f"artist-{rg_id}"],
        first_release_date="2000-01-01",
    )
    diagnostics = {"normalization_trace": dr._normalization_trace(source=path, best_confidence=confidence, second_best_confidence=runner)}
    dr._attach_shadow_results(
        diagnostics,
        cli_min_confidence=0.80,
        cli_ambiguity_gap=0.06,
        config_min_confidence=0.72,
        config_ambiguity_gap=0.08,
    )
    return dr.ScoredCandidate(score=1.0, c=candidate, n=normalized, debug=diagnostics)


def test_slot_shadow_reports_pool_and_final_pick_impact_deterministically():
    direct = _scored("rg-direct", confidence=1.0, runner=None, path="mbid:release-group")
    low = _scored("rg-low", confidence=0.70, runner=0.50)
    ambiguous = _scored("rg-ambiguous", confidence=0.81, runner=0.77)
    accepted = _scored("rg-accepted", confidence=0.90, runner=0.70)
    candidates = [direct, low, ambiguous, accepted]
    kwargs = {
        "candidates": candidates,
        "eligible": candidates,
        "final_picks": [low, ambiguous, accepted],
        "cli_min_confidence": 0.80,
        "cli_ambiguity_gap": 0.06,
        "config_min_confidence": 0.72,
        "config_ambiguity_gap": 0.08,
    }

    first = cli._normalization_shadow_slot_payload(**kwargs)
    second = cli._normalization_shadow_slot_payload(**kwargs)

    assert first == second
    assert first["path_counts"] == {"direct_release_group_mbid": 1, "musicbrainz_text_search": 3}
    cli_impact = first["references"]["cli_reference"]
    assert cli_impact["rejected_total"] == 2
    assert cli_impact["rejected_low_confidence"] == 1
    assert cli_impact["rejected_ambiguous"] == 1
    assert cli_impact["normalized_remaining"] == 2
    assert cli_impact["eligible_remaining"] == 2
    assert cli_impact["final_picks_impacted"] == 2
    assert cli_impact["possible_higher_fallback"] is True
    direct_row = next(row for row in first["candidates"] if row["release_group_mbid"] == "rg-direct")
    assert direct_row["references"]["cli_reference"]["status"] == "not_applicable"


def test_shadow_reference_values_do_not_change_ranked_results_or_request_count(monkeypatch):
    requests = {"lastfm": 0, "normalization": 0}

    def fake_lastfm(*_args, **_kwargs):
        requests["lastfm"] += 1
        return [
            LastFmTopAlbum(
                name=f"Album {index}",
                artist=f"Artist {index}",
                mbid=None,
                playcount=None,
                url=None,
                rank=index,
                image_extralarge=None,
            )
            for index in range(1, 5)
        ]

    def fake_normalize(_broker, _env, candidate, **_kwargs):
        requests["normalization"] += 1
        index = int(candidate.title.rsplit(" ", 1)[1])
        normalized = dr.NormalizedCandidate(
            title=candidate.title,
            artist=candidate.artist,
            mb_release_group_id=f"rg-{index}",
            confidence=0.70 + index / 20,
            source="search:strict",
        )
        return normalized, {
            "mb_debug": [],
            "mb_queries_attempted": 1,
            "normalization_trace": dr._normalization_trace(
                source="search:strict",
                best_confidence=normalized.confidence,
                second_best_confidence=normalized.confidence - 0.10,
            ),
        }

    monkeypatch.setattr(dr, "lastfm_tag_top_albums", fake_lastfm)
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(dr, "_normalize_candidate", fake_normalize)

    first = dr.run_dry_run(
        _Broker(),
        _Env(),
        tag="ambient",
        lastfm_max_pages=1,
        discogs_enabled=False,
        min_confidence=0.80,
        ambiguity_gap=0.06,
        config_reference_min_confidence=0.72,
        config_reference_ambiguity_gap=0.08,
    )
    first_requests = dict(requests)
    second = dr.run_dry_run(
        _Broker(),
        _Env(),
        tag="ambient",
        lastfm_max_pages=1,
        discogs_enabled=False,
        min_confidence=0.99,
        ambiguity_gap=0.50,
        config_reference_min_confidence=0.10,
        config_reference_ambiguity_gap=0.0,
    )
    second_requests = {key: requests[key] - first_requests[key] for key in requests}

    assert [item.n.mb_release_group_id for item in first["top"]] == [item.n.mb_release_group_id for item in second["top"]]
    assert second_requests == first_requests


def test_config_reference_values_parse_from_declared_normalizer_section():
    repo_root = Path(__file__).resolve().parents[1]
    config = load_config(repo_root)

    assert float(config.raw["normalizer"]["min_confidence"]) == 0.72
    assert float(config.raw["normalizer"]["ambiguity_gap"]) == 0.08
