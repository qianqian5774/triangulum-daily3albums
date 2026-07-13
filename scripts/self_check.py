#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from daily3albums.public_contract import (
    PublicContractError,
    canonical_archive_paths,
    require_byte_identical,
    validate_archive,
    validate_archive_identity,
    validate_index,
    validate_issue,
)


class SelfCheckError(RuntimeError):
    pass


BJT = timezone(timedelta(hours=8), "Asia/Shanghai")


def _current_bjt_date_key() -> str:
    return datetime.now(BJT).date().isoformat()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SelfCheckError(f"INVALID_JSON: JSON parse failed: {path} ({exc})") from exc


def _ensure_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise SelfCheckError(f"Missing or empty file: {path}")


def _ensure_str(value: Any, field: str, path: Path) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SelfCheckError(f"Invalid or missing '{field}' in {path}")


def _validate_today(payload: Any, path: Path) -> None:
    try:
        validate_issue(payload, artifact_kind="today", profile="current")
    except PublicContractError as exc:
        raise SelfCheckError(f"Today contract invalid: {path} ({exc})") from exc


def _validate_index(payload: Any, path: Path) -> None:
    try:
        validated = validate_index(payload)
    except PublicContractError as exc:
        raise SelfCheckError(f"Index contract invalid: {path} ({exc})") from exc
    for idx, item in enumerate(validated["items"]):
        run_id = item["run_id"]
        if run_id.startswith("dev-seed"):
            raise SelfCheckError(f"Index item[{idx}] contains dev seed run_id '{run_id}': {path}")


def _validate_archive_payload(payload: Any, path: Path) -> dict[str, Any]:
    try:
        validated, _profile = validate_archive(payload)
        return validated
    except PublicContractError as exc:
        raise SelfCheckError(f"Archive contract invalid: {path} ({exc})") from exc


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
    archive_bytes: list[bytes] = []
    today_bytes = today_path.read_bytes()
    for archive_path in archive_paths:
        _ensure_file(archive_path)
        archive_bytes.append(archive_path.read_bytes())
        archive_payload = _read_json(archive_path)
        try:
            validate_issue(archive_payload, artifact_kind="archive", profile="current")
        except PublicContractError as exc:
            raise SelfCheckError(f"Current archive contract invalid: {archive_path} ({exc})") from exc
        if archive_payload != today_payload:
            raise SelfCheckError(
                f"Archive JSON mismatch: {archive_path} does not match {today_path} "
                f"for date={archive_date} run_id={run_id}"
            )
        if archive_bytes[-1] != today_bytes:
            raise SelfCheckError(
                f"Archive JSON bytes mismatch: {archive_path} does not match {today_path} "
                f"for date={archive_date} run_id={run_id}"
            )
    try:
        require_byte_identical(archive_bytes[0], archive_bytes[1])
    except PublicContractError as exc:
        raise SelfCheckError(f"Current archive alias bytes mismatch: {exc}") from exc


def _validate_index_archives(index_payload: dict[str, Any], path: Path, out_dir: Path) -> None:
    for item_index, item in enumerate(index_payload["items"]):
        date = item["date"]
        run_id = item["run_id"]
        relative_paths = canonical_archive_paths(date, run_id)
        candidates = [out_dir / relative for relative in relative_paths]
        existing = [candidate for candidate in candidates if candidate.is_file()]
        if not existing:
            raise SelfCheckError(
                f"ARCHIVE_MISSING: Index item[{item_index}] points to missing archive "
                f"date={date} run_id={run_id}: {path}"
            )
        bytes_by_path = [(candidate.read_bytes(), candidate) for candidate in existing]
        if len(bytes_by_path) == 2:
            try:
                require_byte_identical(bytes_by_path[0][0], bytes_by_path[1][0])
            except PublicContractError as exc:
                raise SelfCheckError(
                    f"Index item[{item_index}] archive aliases disagree date={date} run_id={run_id}: {exc}"
                ) from exc
        archive_path = bytes_by_path[0][1]
        archive_payload = _read_json(archive_path)
        validated = _validate_archive_payload(archive_payload, archive_path)
        try:
            validate_archive_identity(validated, date=date, run_id=run_id)
        except PublicContractError as exc:
            raise SelfCheckError(
                f"Index item[{item_index}] archive contract invalid: {archive_path} ({exc})"
            ) from exc


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


def _scan_for_legacy_project_site_paths(paths: Iterable[Path]) -> list[str]:
    problems: list[str] = []
    legacy_patterns = [
        re.compile(
            r"https?://qianqian5774\.github\.io/triangulum-daily3albums(?:/|$)",
            re.IGNORECASE,
        ),
        re.compile(r"(?<![A-Za-z0-9_.-])/triangulum-daily3albums/", re.IGNORECASE),
    ]

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            problems.append(f"Failed to read {path}: {exc}")
            continue

        if any(pattern.search(text) for pattern in legacy_patterns):
            problems.append(f"Legacy GitHub Pages project-site path detected in {path}")

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
    _validate_index_archives(index_payload, index_path, out_dir)

    observability_path = out_dir / "data" / "recommendation-observability.json"
    if observability_path.exists():
        _validate_recommendation_observability(_read_json(observability_path), observability_path)

    scan_paths = (
        list(out_dir.rglob("*.html"))
        + list(out_dir.rglob("*.js"))
        + list(out_dir.rglob("*.css"))
        + list(out_dir.rglob("*.json"))
        + list(out_dir.rglob("*.webmanifest"))
    )
    problems = _scan_for_absolute_assets(scan_paths)
    problems.extend(_scan_for_legacy_project_site_paths(scan_paths))
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
