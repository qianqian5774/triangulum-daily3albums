#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 12


def _pages_base_url() -> str:
    explicit = os.getenv("DAILY3ALBUMS_PAGES_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"

    repository = os.getenv("GITHUB_REPOSITORY", "qianqian5774/triangulum-daily3albums")
    owner, _, repo = repository.partition("/")
    if owner and repo:
        return f"https://{owner}.github.io/{repo}/"
    return "https://qianqian5774.github.io/triangulum-daily3albums/"


def _fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url, path)
    with urllib.request.urlopen(url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_bytes(base_url: str, path: str) -> bytes | None:
    url = urllib.parse.urljoin(base_url, path)
    try:
        with urllib.request.urlopen(url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            return response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(f"archive_seed fetch=skip path={path} error={exc}", file=sys.stderr)
        return None


def _sort_key(item: dict[str, Any]) -> str:
    run_at = item.get("run_at")
    if isinstance(run_at, str):
        return run_at
    return f"{item.get('date','')}-{item.get('run_id','')}"


def _select_recent_unique_dates(items: list[Any], max_days: int) -> list[dict[str, Any]]:
    valid_items = [
        item for item in items if isinstance(item, dict) and isinstance(item.get("date"), str)
    ]
    sorted_items = sorted(valid_items, key=_sort_key, reverse=True)
    selected: list[dict[str, Any]] = []
    seen_dates: set[str] = set()

    for item in sorted_items:
        date = item["date"]
        if date in seen_dates:
            continue
        seen_dates.add(date)
        selected.append(item)
        if len(selected) >= max_days:
            break

    return selected


def restore_static_archive_seed(out_dir: Path, max_days: int) -> int:
    base_url = _pages_base_url()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        index = _fetch_json(base_url, "data/index.json")
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        print(f"archive_seed status=unavailable base_url={base_url} error={exc}", file=sys.stderr)
        return 0

    items = index.get("items") if isinstance(index, dict) else None
    if not isinstance(items, list):
        print(f"archive_seed status=invalid_index base_url={base_url}", file=sys.stderr)
        return 0

    selected = _select_recent_unique_dates(items, max_days=max_days)
    archive_dir = out_dir / "archive"
    fetched_paths = 0

    for item in selected:
        date = item["date"]
        run_id = item.get("run_id")
        candidate_paths: list[tuple[str, Path]] = []
        if isinstance(run_id, str) and run_id.strip():
            candidate_paths.append(
                (f"data/archive/{date}/{run_id}.json", archive_dir / date / f"{run_id}.json")
            )
        candidate_paths.append((f"data/archive/{date}.json", archive_dir / f"{date}.json"))

        for remote_path, local_path in candidate_paths:
            payload = _fetch_bytes(base_url, remote_path)
            if payload is None:
                continue
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payload)
            fetched_paths += 1

    seed_index = {
        "output_schema_version": str(index.get("output_schema_version") or "1"),
        "items": selected,
    }
    (out_dir / "index.json").write_text(
        json.dumps(seed_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "archive_seed status=ok "
        f"base_url={base_url} days={len(selected)} files={fetched_paths} out={out_dir}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore recent published archive JSON as a static build seed."
    )
    parser.add_argument(
        "--out",
        default=".state/pages-history-seed/data",
        help="Output data directory for seed files",
    )
    parser.add_argument(
        "--max-days",
        type=int,
        default=3,
        help="Recent unique archive dates to restore",
    )
    args = parser.parse_args()

    max_days = max(0, args.max_days)
    if max_days == 0:
        print("archive_seed status=skip max_days=0")
        return 0
    return restore_static_archive_seed(Path(args.out), max_days=max_days)


if __name__ == "__main__":
    raise SystemExit(main())
