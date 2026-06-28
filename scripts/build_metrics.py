#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_METRICS_DIR = Path(".state/build-metrics")
METRICS_DIR_ENV = "DAILY3ALBUMS_BUILD_METRICS_DIR"
METRICS_SCHEMA_VERSION = 1
RUN_ID_KEYS = ("run_id", "run_attempt")
RESET_FILES = ("start.json", "steps.jsonl", "build-metrics.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _now_ms() -> int:
    return int(time.time() * 1000)


def default_metrics_dir() -> Path:
    configured = os.getenv(METRICS_DIR_ENV)
    if configured:
        return Path(configured)
    runner_temp = os.getenv("RUNNER_TEMP")
    run_id = os.getenv("GITHUB_RUN_ID")
    if runner_temp and run_id:
        run_attempt = os.getenv("GITHUB_RUN_ATTEMPT") or "1"
        return Path(runner_temp) / "daily3albums-build-metrics" / f"{run_id}-{run_attempt}"
    return DEFAULT_METRICS_DIR


def _current_run_identity() -> dict[str, str | None]:
    return {
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
    }


def _has_github_run_identity(run: dict[str, Any]) -> bool:
    return any(run.get(key) for key in RUN_ID_KEYS)


def _run_identity_matches(recorded: Any, current: dict[str, str | None]) -> bool:
    if not _has_github_run_identity(current):
        return True
    if not isinstance(recorded, dict):
        return False
    for key in RUN_ID_KEYS:
        expected = current.get(key)
        if expected and recorded.get(key) != expected:
            return False
    return True


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                out.append(payload)
    return out


def format_bytes(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def _directory_size(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    total = 0
    for file in path.rglob("*"):
        if file.is_file():
            try:
                total += file.stat().st_size
            except OSError:
                continue
    return total


def _count_issue_picks(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    slots = payload.get("slots")
    if isinstance(slots, list):
        total = 0
        for slot in slots:
            if isinstance(slot, dict) and isinstance(slot.get("picks"), list):
                total += len(slot["picks"])
        if total:
            return total
    picks = payload.get("picks")
    return len(picks) if isinstance(picks, list) else 0


def _archive_issue_path(public_dir: Path, item: dict[str, Any]) -> Path | None:
    date = item.get("date")
    run_id = item.get("run_id")
    if not isinstance(date, str) or not date:
        return None
    candidates: list[Path] = []
    if isinstance(run_id, str) and run_id:
        candidates.append(public_dir / "data" / "archive" / date / f"{run_id}.json")
    candidates.append(public_dir / "data" / "archive" / f"{date}.json")
    for path in candidates:
        if path.exists():
            return path
    return candidates[0] if candidates else None


def collect_public_metrics(public_dir: Path) -> dict[str, Any]:
    public_dir = public_dir.resolve()
    metrics: dict[str, Any] = {
        "public_path": str(public_dir),
        "public_exists": public_dir.exists(),
        "public_size_bytes": _directory_size(public_dir),
        "public_size_human": format_bytes(_directory_size(public_dir)),
        "archive_day_count": 0,
        "archive_album_count": 0,
        "today_album_count": 0,
        "archive_retention_days": None,
        "archive_missing_days": [],
        "generated_at": _now_iso(),
    }

    data_dir = public_dir / "data"
    today_path = data_dir / "today.json"
    if today_path.exists():
        try:
            metrics["today_album_count"] = _count_issue_picks(_read_json(today_path))
        except (OSError, json.JSONDecodeError):
            metrics["today_album_count"] = 0

    index_path = data_dir / "index.json"
    if not index_path.exists():
        return metrics

    try:
        index = _read_json(index_path)
    except (OSError, json.JSONDecodeError):
        return metrics
    if not isinstance(index, dict):
        return metrics

    retention = index.get("archive_retention_days")
    if isinstance(retention, int):
        metrics["archive_retention_days"] = retention

    items = index.get("items")
    if not isinstance(items, list):
        return metrics

    seen_dates: set[str] = set()
    archive_album_count = 0
    missing_days: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        date = item.get("date")
        if not isinstance(date, str) or date in seen_dates:
            continue
        seen_dates.add(date)
        issue_path = _archive_issue_path(public_dir, item)
        if issue_path is None or not issue_path.exists():
            missing_days.append(date)
            continue
        try:
            archive_album_count += _count_issue_picks(_read_json(issue_path))
        except (OSError, json.JSONDecodeError):
            missing_days.append(date)

    metrics["archive_day_count"] = len(seen_dates)
    metrics["archive_album_count"] = archive_album_count
    metrics["archive_missing_days"] = missing_days
    return metrics


def _reset_metrics_files(metrics_dir: Path) -> None:
    metrics_dir.mkdir(parents=True, exist_ok=True)
    for name in RESET_FILES:
        path = metrics_dir / name
        try:
            if path.is_file():
                path.unlink()
        except OSError as exc:
            print(f"build_metrics warning: could not reset {path}: {exc}", file=sys.stderr)


def start_metrics(metrics_dir: Path) -> int:
    _reset_metrics_files(metrics_dir)
    _write_json(
        metrics_dir / "start.json",
        {
            "schema_version": METRICS_SCHEMA_VERSION,
            "started_at": _now_iso(),
            "started_at_ms": _now_ms(),
            "run": _current_run_identity(),
        },
    )
    return 0


def run_timed_step(metrics_dir: Path, name: str, command: list[str]) -> int:
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("build_metrics run requires a command after --", file=sys.stderr)
        return 2

    started_ms = _now_ms()
    started = time.perf_counter()
    exit_code = 127
    try:
        completed = subprocess.run(command, check=False)
        exit_code = int(completed.returncode)
    except FileNotFoundError as exc:
        print(f"build_metrics command not found: {exc}", file=sys.stderr)
        exit_code = 127
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _append_jsonl(
            metrics_dir / "steps.jsonl",
            {
                "name": name,
                "command": command,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "started_at_ms": started_ms,
                "finished_at_ms": _now_ms(),
                "run": _current_run_identity(),
            },
        )
    return exit_code


def _load_start(metrics_dir: Path) -> dict[str, Any] | None:
    start_path = metrics_dir / "start.json"
    if not start_path.exists():
        return None
    try:
        start = _read_json(start_path)
    except (OSError, json.JSONDecodeError):
        return None
    return start if isinstance(start, dict) else None


def _load_total_duration(metrics_dir: Path, warnings: list[str]) -> int | None:
    start = _load_start(metrics_dir)
    if start is None:
        return None
    current = _current_run_identity()
    if not _run_identity_matches(start.get("run"), current):
        warnings.append(
            "Ignored stale build metrics start.json because it does not match "
            f"GITHUB_RUN_ID={current.get('run_id') or 'n/a'} "
            f"GITHUB_RUN_ATTEMPT={current.get('run_attempt') or 'n/a'}."
        )
        return None
    started_at_ms = start.get("started_at_ms")
    if not isinstance(started_at_ms, int):
        return None
    return max(0, _now_ms() - started_at_ms)


def _current_run_steps(
    steps: list[dict[str, Any]], warnings: list[str]
) -> list[dict[str, Any]]:
    current = _current_run_identity()
    if not _has_github_run_identity(current):
        return steps
    filtered: list[dict[str, Any]] = []
    stale_count = 0
    for step in steps:
        if _run_identity_matches(step.get("run"), current):
            filtered.append(step)
        else:
            stale_count += 1
    if stale_count:
        warnings.append(
            f"Ignored {stale_count} stale build metric step row(s) because they do not match "
            f"GITHUB_RUN_ID={current.get('run_id') or 'n/a'} "
            f"GITHUB_RUN_ATTEMPT={current.get('run_attempt') or 'n/a'}."
        )
    return filtered


def _markdown_summary(metrics: dict[str, Any]) -> str:
    public = metrics["public"]
    lines = [
        "## Daily3Albums build metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Public size | {public.get('public_size_human')} |",
        f"| Public size bytes | {public.get('public_size_bytes')} |",
        f"| Archive retention days | {public.get('archive_retention_days') or 'n/a'} |",
        f"| Archive dates in index | {public.get('archive_day_count')} |",
        f"| Archive visible albums | {public.get('archive_album_count')} |",
        f"| Today albums | {public.get('today_album_count')} |",
    ]
    run = metrics.get("run")
    if isinstance(run, dict) and (run.get("run_id") or run.get("run_attempt")):
        run_value = f"{run.get('run_id') or 'n/a'} / {run.get('run_attempt') or 'n/a'}"
        lines.append(f"| GitHub run | {run_value} |")
    total = metrics.get("total_duration_ms")
    if isinstance(total, int):
        lines.append(f"| Total measured duration | {total} ms |")
    lines.extend(["", "### Step timings", "", "| Step | Exit | Duration |", "|---|---:|---:|"])
    for step in metrics.get("steps", []):
        if not isinstance(step, dict):
            continue
        lines.append(f"| {step.get('name')} | {step.get('exit_code')} | {step.get('duration_ms')} ms |")
    missing = public.get("archive_missing_days")
    if missing:
        lines.extend(["", f"Archive days missing JSON: `{', '.join(missing)}`"])
    warnings = metrics.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.extend(["", "### Build metrics warnings"])
        for warning in warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def summarize(metrics_dir: Path, public_dir: Path, out: Path | None, summary_path: Path | None) -> int:
    warnings: list[str] = []
    steps = _current_run_steps(_read_jsonl(metrics_dir / "steps.jsonl"), warnings)
    metrics = {
        "schema_version": METRICS_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "metrics_dir": str(metrics_dir),
        "run": _current_run_identity(),
        "warnings": warnings,
        "total_duration_ms": _load_total_duration(metrics_dir, warnings),
        "steps": steps,
        "public": collect_public_metrics(public_dir),
    }
    if out is not None:
        _write_json(out, metrics)
    text = _markdown_summary(metrics)
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record CI step timings and static build metrics.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start_parser = sub.add_parser("start")
    start_parser.add_argument("--metrics-dir", type=Path, default=default_metrics_dir())

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--metrics-dir", type=Path, default=default_metrics_dir())
    run_parser.add_argument("--name", required=True)
    run_parser.add_argument("command", nargs=argparse.REMAINDER)

    summary_parser = sub.add_parser("summarize")
    summary_parser.add_argument("--metrics-dir", type=Path, default=default_metrics_dir())
    summary_parser.add_argument("--public", type=Path, default=Path("_build/public"))
    summary_parser.add_argument("--out", type=Path, default=None)
    summary_parser.add_argument("--summary", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.cmd == "start":
        return start_metrics(args.metrics_dir)
    if args.cmd == "run":
        return run_timed_step(args.metrics_dir, args.name, args.command)
    if args.cmd == "summarize":
        summary_path = args.summary
        if summary_path is None and os.getenv("GITHUB_STEP_SUMMARY"):
            summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])
        out = args.out if args.out is not None else args.metrics_dir / "build-metrics.json"
        return summarize(args.metrics_dir, args.public, out, summary_path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
