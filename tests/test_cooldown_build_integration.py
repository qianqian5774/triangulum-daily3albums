from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from daily3albums import cli
from scripts import self_check

from test_history_cooldown_pipeline import _issue, _write_history


class FakeBroker:
    def __init__(self) -> None:
        self.requests = 0

    def bump(self, count: int = 1) -> None:
        self.requests += count

    def get_stats_snapshot(self) -> dict[str, dict[str, int]]:
        return {
            "LastFmAdapter": {
                "requests": self.requests,
                "timeouts": 0,
                "retries": 0,
            }
        }

    def close(self) -> None:
        return None


def _scored(rg_mbid: str, artist_key: str, *, score: float = 100.0) -> Any:
    return SimpleNamespace(
        c=SimpleNamespace(
            title=f"Album {rg_mbid}",
            artist=f"Artist {artist_key}",
            sources={"lastfm"},
            source_ranks={"lastfm": 1},
            image_url=None,
        ),
        n=SimpleNamespace(
            mb_release_group_id=rg_mbid,
            first_release_date="2000-01-01",
            primary_type="Album",
            artist_mbids=[artist_key],
            confidence=1.0,
        ),
        score=score,
        reason="fixture",
        debug={
            "normalization_shadow": {
                "path": "musicbrainz_text_search",
                "query_strategy": "strict",
                "best_confidence": 0.9,
                "second_best_confidence": 0.7,
                "has_second_best": True,
                "ambiguity_gap": 0.2,
                "references": {
                    "cli_reference": {
                        "min_confidence": 0.8,
                        "ambiguity_gap": 0.06,
                        "status": "evaluated",
                        "rejected": False,
                        "reason": "accepted",
                        "low_confidence": False,
                        "ambiguous": False,
                    },
                    "config_reference": {
                        "min_confidence": 0.72,
                        "ambiguity_gap": 0.08,
                        "status": "evaluated",
                        "rejected": False,
                        "reason": "accepted",
                        "low_confidence": False,
                        "ambiguous": False,
                    },
                },
            }
        },
    )


def _dry_result(candidates: list[Any], *, requested: int = 200, lastfm_pages: int = 1) -> dict:
    count = len(candidates)
    return {
        "requested_candidate_count": requested,
        "raw_candidate_count": count,
        "merged_candidate_count": count,
        "source_counts": {
            "lastfm": count,
            "discogs": 0,
            "listenbrainz": 0,
            "multi_source": 0,
        },
        "prefilter_total": count,
        "prefilter_topn": count,
        "normalized_count": count,
        "normalization_success_count": count,
        "normalization_failed_count": 0,
        "top": candidates,
        "lastfm_pages_fetched": lastfm_pages,
        "lastfm_pages_planned": lastfm_pages,
        "mb_candidates_considered": count,
        "mb_candidates_normalized": count,
        "mb_queries_attempted_total": 0,
        "mb_search_queries_attempted_total": 0,
        "mb_http_calls_total": 0,
        "mb_budget_exceeded": False,
        "mb_cap_hit": False,
        "mb_time_spent_s": 0.01,
        "discogs_enabled": False,
        "discogs_attempted": False,
        "discogs_pages_fetched": 0,
        "discogs_page_cap_hit": False,
        "discogs_failed_status": None,
        "discogs_cached_negative_used": False,
        "listenbrainz_attempted": False,
        "listenbrainz_failed": False,
        "listenbrainz_candidates": 0,
    }


def _prepare_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "ui" / "dist").mkdir(parents=True)
    (repo_root / "ui" / "dist" / "index.html").write_text("<div>fixture</div>", encoding="utf-8")
    (repo_root / "ui" / "dist" / "archive.html").write_text("<div>archive fixture</div>", encoding="utf-8")
    (repo_root / "web").mkdir()
    return repo_root


def _configure_build(
    monkeypatch,
    repo_root: Path,
    seed_dir: Path,
    tags: list[str],
    factory: Callable[[dict[str, Any]], list[Any]],
    config: Any | None = None,
) -> tuple[FakeBroker, list[dict[str, Any]]]:
    source_root = Path(__file__).resolve().parents[1]
    cfg = config or cli.load_config(source_root)
    cfg.raw["tag_pool"] = list(tags)
    cfg.max_tag_tries_per_slot = len(tags)
    cfg.dedupe_same_rg_days = 7
    cfg.dedupe_same_artist_days = 7
    monkeypatch.setattr(cli, "load_config", lambda _root: cfg)
    monkeypatch.setattr(
        cli,
        "load_env",
        lambda _root: SimpleNamespace(
            lastfm_api_key="fixture-key",
            mb_user_agent="fixture-agent",
            discogs_token=None,
        ),
    )
    monkeypatch.setenv("DAILY3ALBUMS_HISTORY_SEED_DIR", str(seed_dir))
    monkeypatch.setattr(cli, "_beijing_now", lambda: datetime.fromisoformat("2026-07-12T06:00:00+08:00"))
    broker = FakeBroker()
    monkeypatch.setattr(cli, "RequestBroker", lambda **_kwargs: broker)
    calls: list[dict[str, Any]] = []

    def fake_run_dry_run(*_args, **kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("lastfm_only"):
            broker.bump()
        candidates = factory(kwargs)
        return _dry_result(
            candidates,
            requested=int(kwargs.get("n", 200)),
            lastfm_pages=int(kwargs.get("lastfm_max_pages", 1)),
        )

    monkeypatch.setattr(cli, "run_dry_run", fake_run_dry_run)
    monkeypatch.setattr(cli.CoverArtArchiveAdapter, "fetch_cover", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "musicbrainz_get_release_group_details", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_wikipedia_overview_from_url", lambda *_args, **_kwargs: None)
    return broker, calls


def _output_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _run_build(repo_root: Path, out_dir: Path) -> int:
    return cli.cmd_build(
        repo_root=repo_root,
        tag="auto",
        n=30,
        topk=10,
        verbose=False,
        split_slots=True,
        mb_search_limit=10,
        min_confidence=0.8,
        ambiguity_gap=0.06,
        mb_debug=False,
        quarantine_out="",
        out_dir=str(out_dir),
        date_override="2026-07-12",
        theme="",
        diagnostics=False,
        skip_ui_build=True,
    )


def _history_issue_with_tags(date_key: str, run_id: str, tags: list[str]) -> dict:
    issue = _issue(date_key, run_id, target_in_slot=2)
    flat_picks = [pick for slot in issue["slots"] for pick in slot["picks"]]
    for index, tag in enumerate(tags):
        flat_picks[index]["artist_mbids"] = [f"artist-cool-{tag}"]
        flat_picks[index]["artist_keys"] = [f"artist-cool-{tag}"]
        flat_picks[index]["artist_credit"] = f"Artist cool {tag}"
        flat_picks[index]["rg_mbid"] = f"rg-old-{tag}"
    for slot in issue["slots"]:
        slot["theme"] = "historical-theme"
        slot["theme_key"] = "historical-theme"
        for pick in slot["picks"]:
            pick["style_key"] = "historical-theme"
    issue["picks"] = issue["slots"][0]["picks"]
    return issue


def test_clean_runner_loads_external_seed_before_selection_and_uses_full_history(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "seed" / "data"
    tags = ["tag-a", "tag-b", "tag-c", "tag-d"]
    history_theme = tags[cli._hash_index("2026-07-12:0", len(tags))]
    issue = _issue("2026-07-11", "published", target_in_slot=2)
    issue["slots"][2]["theme"] = history_theme
    issue["slots"][2]["theme_key"] = history_theme
    for pick in issue["slots"][2]["picks"]:
        pick["style_key"] = history_theme
    snapshots = _write_history(seed_dir, [issue])

    def factory(kwargs: dict[str, Any]) -> list[Any]:
        tag = str(kwargs["tag"])
        return [
            _scored("rg-target", f"album-conflict-artist-{tag}", score=110),
            _scored(f"rg-artist-conflict-{tag}", "artist-7", score=109),
            _scored(f"rg-safe-{tag}-1", f"artist-safe-{tag}-1", score=108),
            _scored(f"rg-safe-{tag}-2", f"artist-safe-{tag}-2", score=107),
            _scored(f"rg-safe-{tag}-3", f"artist-safe-{tag}-3", score=106),
        ]

    _broker, calls = _configure_build(monkeypatch, repo_root, seed_dir, tags, factory)
    out_one = tmp_path / "public-one"

    assert _run_build(repo_root, out_one) == 0
    monkeypatch.setattr(self_check, "_current_bjt_date_key", lambda: "2026-07-12")
    monkeypatch.setattr(sys, "argv", ["self_check.py", "--path", str(out_one)])
    assert self_check.main() == 0
    assert all(not call.get("lastfm_only", False) for call in calls)
    assert all(path.read_bytes() == before for path, before in snapshots.items())

    observability = json.loads(
        (out_one / "data" / "recommendation-observability.json").read_text(encoding="utf-8")
    )
    assert all(slot["history_context"]["source"] == "external_seed" for slot in observability["slots"])
    assert all(slot["history_context"]["archive_count"] == 1 for slot in observability["slots"])
    assert all(slot["history_context"]["picks_loaded"] == 9 for slot in observability["slots"])
    assert all(slot["fallback"]["stage"] == 0 for slot in observability["slots"])
    assert all(slot["fallback"]["candidate_scope_expanded"] is False for slot in observability["slots"])
    assert sum(slot["rejection_reasons"]["album_cooldown"] for slot in observability["slots"]) > 0
    assert sum(slot["rejection_reasons"]["album_cooldown_rg_mbid"] for slot in observability["slots"]) > 0
    assert sum(slot["rejection_reasons"]["artist_cooldown"] for slot in observability["slots"]) > 0
    assert sum(slot["rejection_reasons"]["theme_cooldown"] for slot in observability["slots"]) > 0

    calls.clear()
    out_two = tmp_path / "public-two"
    assert _run_build(repo_root, out_two) == 0
    today_one = json.loads((out_one / "data" / "today.json").read_text(encoding="utf-8"))
    today_two = json.loads((out_two / "data" / "today.json").read_text(encoding="utf-8"))
    assert [slot["picks"] for slot in today_one["slots"]] == [slot["picks"] for slot in today_two["slots"]]
    observability_two = json.loads(
        (out_two / "data" / "recommendation-observability.json").read_text(encoding="utf-8")
    )
    assert [slot["history_context"] for slot in observability["slots"]] == [
        slot["history_context"] for slot in observability_two["slots"]
    ]
    assert [slot["fallback"] for slot in observability["slots"]] == [
        slot["fallback"] for slot in observability_two["slots"]
    ]
    assert [slot["rejection_reasons"] for slot in observability["slots"]] == [
        slot["rejection_reasons"] for slot in observability_two["slots"]
    ]


def test_invalid_external_seed_fails_before_candidate_generation(monkeypatch, tmp_path: Path):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "invalid-seed" / "data"
    seed_dir.mkdir(parents=True)
    (seed_dir / "index.json").write_text('{"items":[{"date":"future","run_id":"bad"}]}', encoding="utf-8")

    def should_not_run(_kwargs: dict[str, Any]) -> list[Any]:
        raise AssertionError("candidate generation ran before history validation")

    _broker, calls = _configure_build(
        monkeypatch,
        repo_root,
        seed_dir,
        ["tag-a", "tag-b", "tag-c"],
        should_not_run,
    )

    assert _run_build(repo_root, tmp_path / "public") == 2
    assert calls == []


def test_r2_removed_config_surfaces_leave_requests_picks_shadow_and_public_artifacts_identical(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "seed" / "data"
    _write_history(seed_dir, [])
    source_root = Path(__file__).resolve().parents[1]
    truthful_config = cli.load_config(source_root)
    pre_r2_config = deepcopy(truthful_config)
    pre_r2_config.raw.update(
        {
            "schema_version": "1.0",
            "output_schema_version": "1.0",
            "timezone": "Asia/Shanghai",
            "random_seed_strategy": "date",
            "decade_mode": "off",
            "global_exclusions": {
                "allow_primary_types": ["Album", "EP"],
                "exclude_secondary_types": ["Compilation", "Live"],
            },
            "slots": {
                "Headliner": {"require_cover": True, "weights": {"Q": 0.4}},
                "Lineage": {"require_cover": True, "weights": {"T": 0.35}},
                "DeepCut": {"require_cover": True, "weights": {"D": 0.35}},
            },
            "themes": {
                "rotation": "daily",
                "items": [{"name": "Unused", "seed_tags": ["unused"], "adjacent_tags": ["unused-2"]}],
            },
        }
    )
    pre_r2_config.raw["normalizer"].update(
        {"top_k": 5, "weights": {"title": 0.3, "artist": 0.3}}
    )
    pre_r2_config.raw["candidates"]["lastfm"].update(
        {"per_page": 50, "pages_per_call": 2, "deepcut_min_page": 3}
    )
    pre_r2_config.raw["candidates"]["discogs"].update(
        {"per_page": 100, "deepcut_min_page": 3}
    )
    pre_r2_config.raw["candidates"]["listenbrainz"] = {
        "count": 200,
        "deepcut_min_offset": 200,
    }
    pre_r2_config.raw["scoring"].update(
        {
            "multi_source_bonus": 6.0,
            "head_keep_max_rank": 18,
            "tail_boost_start_rank": 60,
            "deepcut_head_penalty_rank": 25,
            "temperature_by_slot": {"0": 9.0, "1": 10.0, "2": 14.0},
            "mb_normalize_budget_cap": 140,
            "mb_prefilter_topn": 120,
        }
    )
    pre_r2_config.raw["build"]["lastfm_max_pages"] = 6

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls.fromisoformat("2026-07-12T06:00:00+08:00")
            return value if tz is None else value.astimezone(tz)

    monkeypatch.setattr(cli, "datetime", FixedDateTime)
    monkeypatch.setattr(cli.uuid, "uuid4", lambda: SimpleNamespace(hex="abcdef123456"))
    tags = ["tag-a", "tag-b", "tag-c"]

    def factory(kwargs: dict[str, Any]) -> list[Any]:
        tag = str(kwargs["tag"])
        return [
            _scored(f"rg-{tag}-{index}", f"artist-{tag}-{index}", score=110 - index)
            for index in range(1, 5)
        ]

    before_broker, before_calls = _configure_build(
        monkeypatch,
        repo_root,
        seed_dir,
        tags,
        factory,
        config=pre_r2_config,
    )
    before_out = tmp_path / "before"
    assert _run_build(repo_root, before_out) == 0
    before_ledger = deepcopy(before_calls)
    before_requests = before_broker.requests

    after_broker, after_calls = _configure_build(
        monkeypatch,
        repo_root,
        seed_dir,
        tags,
        factory,
        config=truthful_config,
    )
    after_out = tmp_path / "after"
    assert _run_build(repo_root, after_out) == 0

    assert after_calls == before_ledger
    assert after_broker.requests == before_requests
    assert _output_tree(after_out) == _output_tree(before_out)

    observability = json.loads(
        (after_out / "data" / "recommendation-observability.json").read_text(encoding="utf-8")
    )
    assert all(slot["attempted_tags"] for slot in observability["slots"])
    assert all(slot["candidate_counts"]["final_picks"] == 3 for slot in observability["slots"])
    assert all(slot["fallback"]["stage"] == 0 for slot in observability["slots"])
    assert all(slot["normalization_shadow"]["candidates"] for slot in observability["slots"])
    assert all(
        row["references"]["cli_reference"]["reason"] == "accepted"
        and row["references"]["config_reference"]["reason"] == "accepted"
        for slot in observability["slots"]
        for row in slot["normalization_shadow"]["candidates"]
    )


def test_stage1_adds_exactly_one_lastfm_page_per_unfilled_slot(monkeypatch, tmp_path: Path):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "seed" / "data"
    _write_history(seed_dir, [])
    tags = ["tag-a", "tag-b", "tag-c"]

    def factory(kwargs: dict[str, Any]) -> list[Any]:
        tag = str(kwargs["tag"])
        if kwargs.get("lastfm_only"):
            return [_scored(f"rg-{tag}-expanded", f"artist-{tag}-expanded", score=98)]
        return [
            _scored(f"rg-{tag}-1", f"artist-{tag}-1", score=100),
            _scored(f"rg-{tag}-2", f"artist-{tag}-2", score=99),
        ]

    broker, calls = _configure_build(monkeypatch, repo_root, seed_dir, tags, factory)
    out_dir = tmp_path / "public"

    assert _run_build(repo_root, out_dir) == 0
    expansion_calls = [call for call in calls if call.get("lastfm_only")]
    assert len(expansion_calls) == 3
    assert all(call["lastfm_max_pages"] == 1 for call in expansion_calls)
    assert broker.requests == 3
    observability = json.loads(
        (out_dir / "data" / "recommendation-observability.json").read_text(encoding="utf-8")
    )
    assert [slot["fallback"]["stage"] for slot in observability["slots"]] == [1, 1, 1]
    assert [slot["fallback"]["additional_requests"] for slot in observability["slots"]] == [1, 1, 1]


def test_stage2_relaxes_artist_to_three_days_without_relaxing_album(monkeypatch, tmp_path: Path):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "seed" / "data"
    tags = ["tag-a", "tag-b", "tag-c"]
    _write_history(seed_dir, [_history_issue_with_tags("2026-07-08", "history", tags)])

    def factory(kwargs: dict[str, Any]) -> list[Any]:
        if kwargs.get("lastfm_only"):
            return []
        tag = str(kwargs["tag"])
        return [
            _scored(f"rg-new-{tag}-1", f"artist-new-{tag}-1", score=100),
            _scored(f"rg-new-{tag}-2", f"artist-new-{tag}-2", score=99),
            _scored(f"rg-new-{tag}-3", f"artist-cool-{tag}", score=98),
            _scored(f"rg-old-{tag}", f"artist-other-{tag}", score=97),
        ]

    _broker, _calls = _configure_build(monkeypatch, repo_root, seed_dir, tags, factory)
    out_dir = tmp_path / "public"

    assert _run_build(repo_root, out_dir) == 0
    observability = json.loads(
        (out_dir / "data" / "recommendation-observability.json").read_text(encoding="utf-8")
    )
    assert [slot["fallback"]["stage"] for slot in observability["slots"]] == [2, 2, 2]
    assert all(slot["fallback"]["artist_cooldown_days"] == 3 for slot in observability["slots"])
    assert all(slot["fallback"]["album_cooldown_days"] == 7 for slot in observability["slots"])
    today = json.loads((out_dir / "data" / "today.json").read_text(encoding="utf-8"))
    assert all(
        not pick["rg_mbid"].startswith("rg-old-")
        for slot in today["slots"]
        for pick in slot["picks"]
    )


def test_stage3_allows_one_four_day_album_but_never_three_day_album(monkeypatch, tmp_path: Path):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "seed" / "data"
    tags = ["tag-a", "tag-b", "tag-c"]
    old_issue = _history_issue_with_tags("2026-07-08", "old", tags)
    recent_issue = _history_issue_with_tags("2026-07-09", "recent", tags)
    for tag, pick in zip(tags, [pick for slot in recent_issue["slots"] for pick in slot["picks"]]):
        pick["rg_mbid"] = f"rg-recent-{tag}"
        pick["artist_mbids"] = [f"artist-recent-{tag}"]
        pick["artist_keys"] = [f"artist-recent-{tag}"]
    _write_history(seed_dir, [old_issue, recent_issue])

    def factory(kwargs: dict[str, Any]) -> list[Any]:
        if kwargs.get("lastfm_only"):
            return []
        tag = str(kwargs["tag"])
        slot_id = int(str(kwargs["seed_key"]).split(":")[1])
        base = [
            _scored(f"rg-new-{tag}-1", f"artist-new-{tag}-1", score=100),
            _scored(f"rg-new-{tag}-2", f"artist-new-{tag}-2", score=99),
        ]
        if slot_id > 0:
            base.append(_scored(f"rg-new-{tag}-3", f"artist-new-{tag}-3", score=98))
            return base
        return [
            *base,
            _scored(f"rg-old-{tag}", f"artist-cool-{tag}", score=98),
            _scored(f"rg-recent-{tag}", f"artist-recent-{tag}", score=97),
        ]

    _broker, _calls = _configure_build(monkeypatch, repo_root, seed_dir, tags, factory)
    out_dir = tmp_path / "public"

    assert _run_build(repo_root, out_dir) == 0
    observability = json.loads(
        (out_dir / "data" / "recommendation-observability.json").read_text(encoding="utf-8")
    )
    assert observability["slots"][0]["fallback"]["stage"] == 3
    assert observability["slots"][0]["fallback"]["stage3_used"] is True
    assert observability["slots"][0]["fallback"]["stage3_pick"]["history_date"] == "2026-07-08"
    assert sum(int(slot["fallback"]["stage3_used"]) for slot in observability["slots"]) == 1
    today_text = (out_dir / "data" / "today.json").read_text(encoding="utf-8")
    assert "rg-recent-" not in today_text


def test_second_stage3_request_is_blocked_by_daily_cap(monkeypatch, tmp_path: Path, capsys):
    repo_root = _prepare_repo(tmp_path)
    seed_dir = tmp_path / "seed" / "data"
    tags = ["tag-a", "tag-b", "tag-c"]
    _write_history(seed_dir, [_history_issue_with_tags("2026-07-08", "history", tags)])

    def factory(kwargs: dict[str, Any]) -> list[Any]:
        if kwargs.get("lastfm_only"):
            return []
        tag = str(kwargs["tag"])
        return [
            _scored(f"rg-new-{tag}-1", f"artist-new-{tag}-1", score=100),
            _scored(f"rg-new-{tag}-2", f"artist-new-{tag}-2", score=99),
            _scored(f"rg-old-{tag}", f"artist-cool-{tag}", score=98),
        ]

    _broker, _calls = _configure_build(monkeypatch, repo_root, seed_dir, tags, factory)

    assert _run_build(repo_root, tmp_path / "public") == 2
    output = capsys.readouterr().out
    assert "stage3_daily_cap" in output
    assert "exhausted_after_stage3" in output
