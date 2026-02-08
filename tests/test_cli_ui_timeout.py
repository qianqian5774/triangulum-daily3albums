from types import SimpleNamespace
from pathlib import Path
import subprocess

from daily3albums import cli


def _fake_scored(i: int):
    c = SimpleNamespace(title=f"Album {i}", artist=f"Artist {i}")
    n = SimpleNamespace(
        mb_release_group_id="",
        first_release_date="2000-01-01",
        primary_type="Album",
        artist_mbids=[f"artist-{i}"],
        confidence=1.0,
    )
    return SimpleNamespace(c=c, n=n, score=100 - i, reason="ok")


def test_cmd_build_ui_timeout_returns_nonzero(monkeypatch, tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    (repo_root / "ui").mkdir(exist_ok=True)

    monkeypatch.setattr(cli, "load_env", lambda _root: SimpleNamespace(lastfm_api_key="k", mb_user_agent="ua", discogs_token=None))
    cfg = cli.load_config(repo_root)
    cfg.ui_build_timeout_s = 1
    monkeypatch.setattr(cli, "load_config", lambda _root: cfg)

    fake_out = {
        "prefilter_total": 3,
        "prefilter_topn": 3,
        "normalized_count": 3,
        "top": [_fake_scored(1), _fake_scored(2), _fake_scored(3)],
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
    monkeypatch.setattr(cli, "run_dry_run", lambda *args, **kwargs: fake_out)

    monkeypatch.setattr(cli, "validate_today_constraints", lambda *args, **kwargs: [])

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
    )

    assert rc == 2
