#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from daily3albums.config import load_config, load_env
from daily3albums.dry_run import run_dry_run
from daily3albums.request_broker import RequestBroker


def _summary(out: dict[str, Any], tag: str) -> dict[str, Any]:
    candidates = [
        {
            "rank": c.lastfm_rank,
            "artist": c.artist,
            "title": c.title,
            "mbid": c.lastfm_mbid,
        }
        for c in out.get("candidates", [])
    ]

    def summarize_scored(s) -> dict[str, Any]:
        rg_id = s.n.mb_release_group_id if s.n else None
        return {
            "rg_mbid": rg_id,
            "score": s.score,
            "artist": s.c.artist,
            "title": s.c.title,
        }

    top = [summarize_scored(s) for s in out.get("top", [])]
    slots_out: dict[str, Any] = {}
    for name, scored in (out.get("slots") or {}).items():
        slots_out[name] = summarize_scored(scored) if scored else None

    return {
        "schema_version": 1,
        "tag": tag,
        "candidates": candidates,
        "top": top,
        "slots": slots_out,
    }


def _validate_summary(payload: dict[str, Any]) -> None:
    required_keys = {"schema_version", "tag", "candidates", "top", "slots"}
    missing = required_keys - payload.keys()
    if missing:
        raise RuntimeError(f"Missing keys in summary: {sorted(missing)}")
    if not isinstance(payload.get("candidates"), list):
        raise RuntimeError("Summary candidates must be list")
    if not isinstance(payload.get("top"), list):
        raise RuntimeError("Summary top must be list")
    if not isinstance(payload.get("slots"), dict):
        raise RuntimeError("Summary slots must be object")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate/check golden dry-run summary")
    parser.add_argument("--fixtures", default="tests/fixtures/http")
    parser.add_argument("--golden", default="tests/golden/dry_run.json")
    parser.add_argument("--tag", default="fixture")
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--topk", type=int, default=3)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    os.environ["DAILY3ALBUMS_FIXTURES_DIR"] = args.fixtures
    os.environ["DAILY3ALBUMS_FIXTURES_STRICT"] = "1"
    os.environ["LASTFM_API_KEY"] = "fixture-key"
    os.environ["MB_USER_AGENT"] = "fixture-agent"

    repo_root = Path(__file__).resolve().parents[1]
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=None)
    try:
        out = run_dry_run(
            broker,
            env,
            tag=args.tag,
            n=args.n,
            topk=args.topk,
            split_slots=True,
            mb_search_limit=10,
            min_confidence=0.8,
            ambiguity_gap=0.06,
            mb_debug=False,
            quarantine_out=None,
        )
    finally:
        broker.close()

    summary = _summary(out, args.tag)
    _validate_summary(summary)

    golden_path = Path(args.golden)
    if args.update:
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Golden updated: {golden_path}")
        return 0

    if not golden_path.exists():
        raise RuntimeError(f"Golden file missing: {golden_path}")

    golden = _load_json(golden_path)
    _validate_summary(golden)

    if golden != summary:
        expected = json.dumps(golden, ensure_ascii=False, indent=2)
        actual = json.dumps(summary, ensure_ascii=False, indent=2)
        print("Golden mismatch. Expected:")
        print(expected)
        print("Actual:")
        print(actual)
        return 1

    print("GOLDEN CHECK OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"GOLDEN CHECK FAILED: {exc}")
        raise SystemExit(1)
