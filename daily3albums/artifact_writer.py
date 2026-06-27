from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class OutputValidationError(RuntimeError):
    pass


DEFAULT_ARCHIVE_RETENTION_DAYS = 7


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    payload = _to_jsonable(obj)
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
        f.write("\n")

    # Windows 下 os.replace 是原子语义（同盘同目录）
    os.replace(tmp, path)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def validate_today(issue: dict) -> None:
    # 顶层必填
    for k in ["output_schema_version", "date", "run_id", "theme_of_day", "slots"]:
        if k not in issue:
            raise OutputValidationError(f"missing top-level field: {k}")

    slots = issue["slots"]
    if not isinstance(slots, list) or len(slots) != 3:
        raise OutputValidationError("slots must be a list of 3 items")

    slot_ids = [slot.get("slot_id") for slot in slots if isinstance(slot, dict)]
    if len(slot_ids) != 3 or len(set(slot_ids)) != 3:
        raise OutputValidationError(f"slot_id must be unique: {slot_ids}")
    if slot_ids != [0, 1, 2]:
        raise OutputValidationError(f"slots must be ordered [0,1,2]: {slot_ids}")

    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise OutputValidationError(f"slot[{i}] is not an object")
        if "window_label" not in slot:
            raise OutputValidationError(f"slot[{i}].window_label is missing")
        picks = slot.get("picks")
        if not isinstance(picks, list) or len(picks) != 3:
            raise OutputValidationError(f"slot[{i}].picks must be a list of 3 items")
        for j, pick in enumerate(picks):
            if not isinstance(pick, dict) or not pick.get("rg_mbid"):
                raise OutputValidationError(f"slot[{i}].pick[{j}].rg_mbid is empty")
            cover = pick.get("cover") or {}
            if not cover.get("optimized_cover_url"):
                raise OutputValidationError(f"slot[{i}].pick[{j}].cover.optimized_cover_url is empty")

    picks = issue.get("picks")
    if isinstance(picks, list) and picks:
        slots_seen = [p.get("slot") for p in picks if isinstance(p, dict)]
        if len(set(slots_seen)) != len(slots_seen):
            raise OutputValidationError(f"duplicate slot names in picks: {slots_seen}")


def _is_dev_seed_item(item: dict[str, Any]) -> bool:
    run_id = item.get("run_id")
    return isinstance(run_id, str) and run_id.startswith("dev-seed")


def _sort_key(item: dict[str, Any]) -> str:
    run_at = item.get("run_at")
    if isinstance(run_at, str):
        return run_at
    return f"{item.get('date','')}-{item.get('run_id','')}"


def _is_date_key(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _archive_file_date_key(archive_dir: Path, path: Path) -> str | None:
    try:
        rel = path.relative_to(archive_dir)
    except ValueError:
        return None
    if len(rel.parts) == 1:
        candidate = path.stem
    elif len(rel.parts) >= 2:
        candidate = rel.parts[0]
    else:
        return None
    return candidate if _is_date_key(candidate) else None


def _snapshot_historical_archive_json(
    archive_dir: Path,
    current_date_key: str,
) -> dict[Path, bytes]:
    if not archive_dir.exists() or not archive_dir.is_dir():
        return {}
    snapshot: dict[Path, bytes] = {}
    for path in archive_dir.rglob("*.json"):
        date_key = _archive_file_date_key(archive_dir, path)
        if not date_key or date_key >= current_date_key:
            continue
        snapshot[path] = path.read_bytes()
    return snapshot


def _assert_historical_archive_json_unchanged(
    archive_dir: Path,
    snapshot: dict[Path, bytes],
    keep_dates: set[str],
    current_date_key: str,
) -> None:
    for path, before in snapshot.items():
        date_key = _archive_file_date_key(archive_dir, path)
        if not date_key or date_key >= current_date_key or date_key not in keep_dates:
            continue
        if not path.exists():
            raise OutputValidationError(
                f"historical archive JSON disappeared unexpectedly: date={date_key} path={path}"
            )
        after = path.read_bytes()
        if after != before:
            raise OutputValidationError(
                f"historical archive JSON changed unexpectedly: date={date_key} path={path}"
            )


def _load_index(index_path: Path, output_schema_version: str) -> dict[str, Any]:
    if not index_path.exists():
        return {"output_schema_version": output_schema_version, "items": []}
    try:
        text = index_path.read_text(encoding="utf-8-sig")
        index_obj = json.loads(text) if text.strip() else {}
        if not isinstance(index_obj, dict) or not isinstance(index_obj.get("items", []), list):
            raise ValueError("bad index schema")
        return index_obj
    except Exception:
        return {"output_schema_version": output_schema_version, "items": []}


def _archive_paths_for_item(archive_dir: Path, item: dict[str, Any]) -> list[Path]:
    date_key = item.get("date")
    if not isinstance(date_key, str) or not date_key:
        return []
    run_id = item.get("run_id")
    candidates: list[Path] = []
    if isinstance(run_id, str) and run_id.strip():
        candidates.append(archive_dir / date_key / f"{run_id}.json")
    candidates.append(archive_dir / f"{date_key}.json")
    return candidates


def _select_existing_date_item(items: list[Any], date_key: str) -> dict[str, Any] | None:
    candidates = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("date") == date_key
        and isinstance(item.get("run_id"), str)
        and item.get("run_id")
        and not _is_dev_seed_item(item)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=_sort_key, reverse=True)[0]


def _load_locked_archive_issue(
    archive_dir: Path,
    item: dict[str, Any],
) -> tuple[dict[str, Any], bytes, Path]:
    paths = _archive_paths_for_item(archive_dir, item)
    existing = [path for path in paths if path.exists()]
    if not existing:
        date_key = item.get("date")
        run_id = item.get("run_id")
        raise OutputValidationError(
            f"published archive index already has date={date_key} run_id={run_id}, "
            "but no matching archive JSON was restored"
        )

    source_path = existing[0]
    source_bytes = source_path.read_bytes()
    for path in existing[1:]:
        if path.read_bytes() != source_bytes:
            raise OutputValidationError(
                f"published archive JSON paths disagree for date={item.get('date')} "
                f"run_id={item.get('run_id')}: {source_path} vs {path}"
            )

    try:
        payload = json.loads(source_bytes.decode("utf-8-sig"))
    except Exception as exc:
        raise OutputValidationError(
            f"published archive JSON is not valid: {source_path} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise OutputValidationError(f"published archive JSON must be an object: {source_path}")
    if payload.get("date") != item.get("date"):
        index_date = item.get("date")
        payload_date = payload.get("date")
        raise OutputValidationError(
            f"published archive date mismatch: index={index_date} payload={payload_date}"
        )
    if payload.get("run_id") != item.get("run_id"):
        index_run_id = item.get("run_id")
        payload_run_id = payload.get("run_id")
        raise OutputValidationError(
            f"published archive run_id mismatch: index={index_run_id} payload={payload_run_id}"
        )
    validate_today(payload)
    return payload, source_bytes, source_path


def _canonical_index_item(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": issue["date"],
        "run_id": issue["run_id"],
        "theme_of_day": issue["theme_of_day"],
        "slot": issue.get("slot"),
        "run_at": issue.get("run_at"),
    }


def _ensure_locked_archive_path(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise OutputValidationError(f"locked archive path has conflicting bytes: {path}")
        return
    atomic_write_bytes(path, data)


def _prune_archive_files(archive_dir: Path, keep_dates: set[str]) -> None:
    if not archive_dir.exists() or not archive_dir.is_dir():
        return
    for path in archive_dir.iterdir():
        if path.is_dir():
            if path.name not in keep_dates:
                shutil.rmtree(path)
            continue
        if path.is_file() and path.suffix == ".json" and path.stem not in keep_dates:
            path.unlink()


def write_daily_artifacts(
    issue: dict,
    out_public_dir: Path,
    quarantine_rows: list[dict] | None = None,
    archive_retention_days: int = DEFAULT_ARCHIVE_RETENTION_DAYS,
    force_archive_rewrite: bool = False,
) -> dict[str, Path]:
    data_dir = out_public_dir / "data"
    archive_dir = data_dir / "archive"
    quarantine_dir = data_dir / "quarantine"

    date_key = issue["date"]
    today_path = data_dir / "today.json"
    index_path = data_dir / "index.json"
    quarantine_path = quarantine_dir / f"{date_key}.json"
    retention_days = max(1, int(archive_retention_days))
    historical_snapshot = _snapshot_historical_archive_json(archive_dir, date_key)

    index_obj = _load_index(index_path, str(issue["output_schema_version"]))
    items = index_obj.get("items") or []
    locked_bytes: bytes | None = None
    existing_item = _select_existing_date_item(items, date_key)
    if existing_item is not None and not force_archive_rewrite:
        locked_issue, locked_bytes, _source_path = _load_locked_archive_issue(
            archive_dir,
            existing_item,
        )
        issue.clear()
        issue.update(locked_issue)

    date_key = issue["date"]
    archive_path = archive_dir / date_key / f"{issue['run_id']}.json"
    archive_flat_path = archive_dir / f"{date_key}.json"

    if locked_bytes is None:
        atomic_write_json(today_path, issue)
        atomic_write_json(archive_path, issue)
        atomic_write_json(archive_flat_path, issue)
    else:
        atomic_write_bytes(today_path, locked_bytes)
        _ensure_locked_archive_path(archive_path, locked_bytes)
        _ensure_locked_archive_path(archive_flat_path, locked_bytes)

    items = [
        x
        for x in items
        if isinstance(x, dict)
        and not _is_dev_seed_item(x)
        and x.get("date") != date_key
        and x.get("run_id") != issue["run_id"]
    ]
    if locked_bytes is not None and existing_item is not None:
        items.append(existing_item)
    else:
        items.append(_canonical_index_item(issue))

    items.sort(key=_sort_key, reverse=True)
    recent_items: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for item in items:
        item_date = item.get("date")
        if not isinstance(item_date, str) or item_date in seen_dates:
            continue
        seen_dates.add(item_date)
        recent_items.append(item)
        if len(recent_items) >= retention_days:
            break
    index_obj["archive_retention_days"] = retention_days
    index_obj["items"] = recent_items
    _prune_archive_files(archive_dir, seen_dates)
    _assert_historical_archive_json_unchanged(
        archive_dir,
        snapshot=historical_snapshot,
        keep_dates=seen_dates,
        current_date_key=date_key,
    )

    atomic_write_json(index_path, index_obj)

    quarantine_written = bool(quarantine_rows and locked_bytes is None)
    if quarantine_written:
        atomic_write_json(
            quarantine_path,
            {"date": date_key, "run_id": issue["run_id"], "items": quarantine_rows},
        )

    return {
        "today": today_path,
        "archive": archive_path,
        "archive_flat": archive_flat_path,
        "index": index_path,
        **({"quarantine": quarantine_path} if quarantine_written else {}),
    }
