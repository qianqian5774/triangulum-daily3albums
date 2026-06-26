#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


class SelfCheckError(RuntimeError):
    pass


BJT = timezone(timedelta(hours=8), "Asia/Shanghai")


def _current_bjt_date_key() -> str:
    return datetime.now(BJT).date().isoformat()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SelfCheckError(f"JSON parse failed: {path} ({exc})") from exc


def _ensure_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise SelfCheckError(f"Missing or empty file: {path}")


def _ensure_str(value: Any, field: str, path: Path) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SelfCheckError(f"Invalid or missing '{field}' in {path}")


def _validate_today(payload: Any, path: Path) -> None:
    if not isinstance(payload, dict):
        raise SelfCheckError(f"Today payload must be object: {path}")
    _ensure_str(payload.get("output_schema_version"), "output_schema_version", path)
    _ensure_str(payload.get("date"), "date", path)
    _ensure_str(payload.get("run_id"), "run_id", path)
    _ensure_str(payload.get("theme_of_day"), "theme_of_day", path)

    slots = payload.get("slots")
    if not isinstance(slots, list) or len(slots) != 3:
        raise SelfCheckError(f"today.json must contain exactly 3 slots: {path}")

    slot_ids = [slot.get("slot_id") if isinstance(slot, dict) else None for slot in slots]
    if slot_ids != [0, 1, 2]:
        raise SelfCheckError(f"today.json slots must be ordered [0, 1, 2], got {slot_ids}: {path}")

    top_picks = payload.get("picks")
    if not isinstance(top_picks, list) or len(top_picks) != 3:
        raise SelfCheckError(f"today.json top-level picks must contain exactly 3 items: {path}")

    for idx, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise SelfCheckError(f"Today slot[{idx}] must be object: {path}")
        if not isinstance(slot.get("slot_id"), int):
            raise SelfCheckError(f"slot[{idx}].slot_id missing: {path}")
        _ensure_str(slot.get("window_label"), f"slot[{idx}].window_label", path)
        picks = slot.get("picks")
        if not isinstance(picks, list) or len(picks) != 3:
            raise SelfCheckError(f"slot[{idx}].picks must contain exactly 3 items: {path}")
        for jdx, pick in enumerate(picks):
            if not isinstance(pick, dict):
                raise SelfCheckError(f"slot[{idx}].pick[{jdx}] must be object: {path}")
            _ensure_str(pick.get("slot"), f"slot[{idx}].picks[{jdx}].slot", path)
            _ensure_str(pick.get("title"), f"slot[{idx}].picks[{jdx}].title", path)
            cover = pick.get("cover")
            if not isinstance(cover, dict) or not isinstance(cover.get("optimized_cover_url"), str):
                raise SelfCheckError(f"slot[{idx}].picks[{jdx}].cover.optimized_cover_url missing: {path}")


def _validate_index(payload: Any, path: Path) -> None:
    if not isinstance(payload, dict):
        raise SelfCheckError(f"Index payload must be object: {path}")
    _ensure_str(payload.get("output_schema_version"), "output_schema_version", path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise SelfCheckError(f"Index items must be list: {path}")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise SelfCheckError(f"Index item[{idx}] must be object: {path}")
        _ensure_str(item.get("date"), f"items[{idx}].date", path)
        _ensure_str(item.get("run_id"), f"items[{idx}].run_id", path)
        run_id = item.get("run_id")
        if isinstance(run_id, str) and run_id.startswith("dev-seed"):
            raise SelfCheckError(f"Index item[{idx}] contains dev seed run_id '{run_id}': {path}")


def _validate_today_date(payload: dict[str, Any], path: Path) -> None:
    expected = _current_bjt_date_key()
    actual = payload.get("date")
    if actual != expected:
        raise SelfCheckError(
            f"today.json date mismatch: expected current Asia/Shanghai date {expected}, got {actual!r}: {path}"
        )


def _validate_archive_consistency(today_payload: dict[str, Any], today_path: Path, out_dir: Path) -> None:
    archive_date = today_payload.get("date")
    if not isinstance(archive_date, str) or not archive_date.strip():
        raise SelfCheckError("today.json missing date for archive lookup")

    run_id = today_payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise SelfCheckError("today.json missing run_id for archive lookup")

    archive_paths = [
        out_dir / "data" / "archive" / archive_date / f"{run_id}.json",
        out_dir / "data" / "archive" / f"{archive_date}.json",
    ]
    for archive_path in archive_paths:
        _ensure_file(archive_path)
        archive_payload = _read_json(archive_path)
        _validate_today(archive_payload, archive_path)
        if archive_payload != today_payload:
            raise SelfCheckError(
                f"Archive JSON mismatch: {archive_path} does not match {today_path} "
                f"for date={archive_date} run_id={run_id}"
            )


def _validate_index_contains_today(index_payload: Any, path: Path, today_payload: dict[str, Any]) -> None:
    items = index_payload.get("items") if isinstance(index_payload, dict) else None
    if not isinstance(items, list):
        raise SelfCheckError(f"Index items must be list: {path}")
    date_key = today_payload.get("date")
    run_id = today_payload.get("run_id")
    for item in items:
        if isinstance(item, dict) and item.get("date") == date_key and item.get("run_id") == run_id:
            return
    raise SelfCheckError(f"Index missing current today entry date={date_key} run_id={run_id}: {path}")


def _validate_recommendation_observability(payload: Any, path: Path) -> None:
    if not isinstance(payload, dict):
        raise SelfCheckError(f"Recommendation observability payload must be object: {path}")
    if payload.get("schema_version") != 1:
        raise SelfCheckError(f"recommendation-observability.json schema_version must be 1: {path}")
    slots = payload.get("slots")
    if not isinstance(slots, list) or len(slots) != 3:
        raise SelfCheckError(f"recommendation-observability.json must contain exactly 3 slots: {path}")
    coverage = payload.get("final_pick_coverage")
    if not isinstance(coverage, dict) or coverage.get("total") != 9:
        raise SelfCheckError(f"recommendation-observability.json final_pick_coverage.total must be 9: {path}")
    for idx, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise SelfCheckError(f"recommendation-observability slot[{idx}] must be object: {path}")
        counts = slot.get("candidate_counts")
        if not isinstance(counts, dict):
            raise SelfCheckError(f"recommendation-observability slot[{idx}].candidate_counts missing: {path}")
        if counts.get("final_picks") != 3:
            raise SelfCheckError(f"recommendation-observability slot[{idx}].candidate_counts.final_picks must be 3: {path}")


def _scan_for_absolute_assets(paths: Iterable[Path]) -> list[str]:
    problems: list[str] = []
    fetch_http = re.compile(r"fetch\(\s*['\"]https?://", re.IGNORECASE)
    fetch_proto = re.compile(r"fetch\(\s*['\"]//", re.IGNORECASE)
    fetch_root = re.compile(r"fetch\(\s*['\"]/", re.IGNORECASE)
    absolute_assets = [
        re.compile(r"['\"]/assets/", re.IGNORECASE),
        re.compile(r"['\"]/data/", re.IGNORECASE),
        re.compile(r"['\"]/index\.html", re.IGNORECASE),
        re.compile(r"['\"]/archive\.html", re.IGNORECASE),
    ]
    http_asset = re.compile(r"https?://[^\"']*/(assets|data)/", re.IGNORECASE)

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            problems.append(f"Failed to read {path}: {exc}")
            continue

        if fetch_http.search(text) or fetch_proto.search(text) or fetch_root.search(text):
            problems.append(f"Absolute fetch path detected in {path}")

        for pattern in absolute_assets:
            if pattern.search(text):
                problems.append(f"Absolute asset path detected in {path}")
                break

        if http_asset.search(text):
            problems.append(f"Absolute http(s) asset path detected in {path}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-check build outputs in _build/public")
    parser.add_argument("--path", default="_build/public", help="Output public directory to validate")
    args = parser.parse_args()

    out_dir = Path(args.path)
    if not out_dir.exists():
        raise SelfCheckError(f"Output directory missing: {out_dir}")

    index_html = out_dir / "index.html"
    archive_html = out_dir / "archive.html"
    _ensure_file(index_html)
    _ensure_file(archive_html)

    today_path = out_dir / "data" / "today.json"
    index_path = out_dir / "data" / "index.json"
    _ensure_file(today_path)
    _ensure_file(index_path)

    today_payload = _read_json(today_path)
    _validate_today(today_payload, today_path)
    _validate_today_date(today_payload, today_path)
    _validate_archive_consistency(today_payload, today_path, out_dir)

    index_payload = _read_json(index_path)
    _validate_index(index_payload, index_path)
    _validate_index_contains_today(index_payload, index_path, today_payload)

    observability_path = out_dir / "data" / "recommendation-observability.json"
    if observability_path.exists():
        _validate_recommendation_observability(_read_json(observability_path), observability_path)

    scan_paths = list(out_dir.rglob("*.html")) + list(out_dir.rglob("*.js"))
    problems = _scan_for_absolute_assets(scan_paths)
    if problems:
        raise SelfCheckError("; ".join(problems))

    print("SELF_CHECK OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SelfCheckError as exc:
        print(f"SELF_CHECK FAILED: {exc}")
        raise SystemExit(1)
