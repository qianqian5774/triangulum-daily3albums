from types import SimpleNamespace
from pathlib import Path
import subprocess

from daily3albums import cli


def _fake_scored(i: int):
    c = SimpleNamespace(title=f"Album {i}", artist=f"Artist {i}")
    n = SimpleNamespace(
        mb_release_group_id=f"rg-{i}",
        first_release_date="2000-01-01",
        primary_type="Album",
        artist_mbids=[f"artist-{i}"],
        confidence=1.0,
    )
    return SimpleNamespace(c=c, n=n, score=100 - i, reason="ok")


def _fake_dry_run_result(offset: int = 0):
    return {
        "prefilter_total": 3,
        "prefilter_topn": 3,
        "normalized_count": 3,
        "top": [_fake_scored(offset + 1), _fake_scored(offset + 2), _fake_scored(offset + 3)],
        "lastfm_pages_fetched": 1,
        "lastfm_pages_planned": 1,
        "mb_candidates_considered": 3,
        "mb_candidates_normalized": 3,
        "mb_queries_attempted_total": 0,
        "mb_search_queries_attempted_total": 0,
        "mb_http_calls_total": 0,
        "mb_budget_exceeded": False,
        "mb_cap_hit": False,
        "mb_time_spent_s": 0.01,
        "discogs_enabled": False,
        "discogs_pages_fetched": 0,
        "discogs_page_cap_hit": False,
        "discogs_failed_status": None,
        "discogs_cached_negative_used": False,
    }


def test_cmd_build_ui_timeout_returns_nonzero(monkeypatch, tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    (repo_root / "ui").mkdir(exist_ok=True)

    monkeypatch.setattr(cli, "load_env", lambda _root: SimpleNamespace(lastfm_api_key="k", mb_user_agent="ua", discogs_token=None))
    cfg = cli.load_config(repo_root)
    cfg.ui_build_timeout_s = 1
    monkeypatch.setattr(cli, "load_config", lambda _root: cfg)

    monkeypatch.setattr(cli, "run_dry_run", lambda *args, **kwargs: _fake_dry_run_result())

    monkeypatch.setattr(cli, "validate_today_constraints", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "musicbrainz_get_release_group_details", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_wikipedia_overview_from_url", lambda *args, **kwargs: None)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", args[0]), timeout=1)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    rc = cli.cmd_build(
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
        out_dir="_build/public",
        date_override="",
        theme="",
        diagnostics=False,
        skip_ui_build=False,
    )

    assert rc == 2


def test_cmd_build_skip_ui_build_reuses_existing_dist(monkeypatch, tmp_path: Path):
    repo_root = tmp_path
    (repo_root / "ui" / "dist").mkdir(parents=True)
    (repo_root / "ui" / "dist" / "index.html").write_text("<div>built</div>", encoding="utf-8")
    (repo_root / "web").mkdir()

    monkeypatch.setattr(cli, "load_env", lambda _root: SimpleNamespace(lastfm_api_key="k", mb_user_agent="ua", discogs_token=None))
    cfg = cli.load_config(Path(__file__).resolve().parents[1])
    cfg.raw["tag_pool"] = ["fixture-a", "fixture-b", "fixture-c"]
    cfg.max_tag_tries_per_slot = 3
    monkeypatch.setattr(cli, "load_config", lambda _root: cfg)

    calls = {"count": 0}

    def fake_run_dry_run(*args, **kwargs):
        calls["count"] += 1
        return _fake_dry_run_result(calls["count"] * 10)

    monkeypatch.setattr(cli, "run_dry_run", fake_run_dry_run)
    monkeypatch.setattr(cli, "validate_today_constraints", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "musicbrainz_get_release_group_details", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_wikipedia_overview_from_url", lambda *args, **kwargs: None)

    def fail_if_npm_runs(*args, **kwargs):
        raise AssertionError("npm should not run when --skip-ui-build is set")

    monkeypatch.setattr(cli.subprocess, "run", fail_if_npm_runs)

    rc = cli.cmd_build(
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
        out_dir=str(tmp_path / "public"),
        date_override="",
        theme="",
        diagnostics=False,
        skip_ui_build=True,
    )

    assert rc == 0
    assert (tmp_path / "public" / "index.html").exists()
    assert (tmp_path / "public" / "data" / "today.json").exists()
