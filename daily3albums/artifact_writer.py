from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class OutputValidationError(RuntimeError):
    pass


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


def validate_today(issue: dict) -> None:
    # 顶层必填
    for k in ["output_schema_version", "date", "run_id", "theme_of_day", "picks"]:
        if k not in issue:
            raise OutputValidationError(f"missing top-level field: {k}")

    picks = issue["picks"]
    if not isinstance(picks, list) or len(picks) != 3:
        raise OutputValidationError("picks must be a list of 3 items")

    # 槽位唯一 + rg_mbid 不空
    slots = [p.get("slot") for p in picks]
    if len(set(slots)) != 3:
        raise OutputValidationError(f"slots must be unique: {slots}")

    for i, p in enumerate(picks):
        if not p.get("rg_mbid"):
            raise OutputValidationError(f"pick[{i}].rg_mbid is empty")
        cover = p.get("cover") or {}
        if not cover.get("optimized_cover_url"):
            raise OutputValidationError(f"pick[{i}].cover.optimized_cover_url is empty")

    # 同日不重复 rg_mbid
    rg_ids = [p["rg_mbid"] for p in picks]
    if len(set(rg_ids)) != 3:
        raise OutputValidationError("duplicate rg_mbid in picks")


def write_daily_artifacts(
    issue: dict,
    out_public_dir: Path,
    quarantine_rows: list[dict] | None = None,
) -> dict[str, Path]:
    # ...（这里是你原来函数里已经存在的：data_dir/archive_dir/quarantine_dir/date_key/today_path/...）
    data_dir = out_public_dir / "data"
    archive_dir = data_dir / "archive"
    quarantine_dir = data_dir / "quarantine"

    date_key = issue["date"]
    today_path = data_dir / "today.json"
    archive_path = archive_dir / f"{date_key}.json"
    index_path = data_dir / "index.json"
    quarantine_path = quarantine_dir / f"{date_key}.json"

    # 1) today + archive
    atomic_write_json(today_path, issue)
    atomic_write_json(archive_path, issue)

    # 2) index：读旧的（不存在就新建），追加一条（带兜底）
    index_obj: dict[str, Any]
    if index_path.exists():
        try:
            text = index_path.read_text(encoding="utf-8-sig")
            # 允许空文件：当作坏文件直接重建
            index_obj = json.loads(text) if text.strip() else {}
            # 结构防御：不是 dict 或 items 不是 list，都视为坏文件
            if not isinstance(index_obj, dict) or not isinstance(index_obj.get("items", []), list):
                raise ValueError("bad index schema")
        except Exception:
            index_obj = {"output_schema_version": issue["output_schema_version"], "items": []}
    else:
        index_obj = {"output_schema_version": issue["output_schema_version"], "items": []}

    items = index_obj.get("items") or []
    items = [x for x in items if x.get("date") != date_key]
    items.append({"date": date_key, "run_id": issue["run_id"], "theme_of_day": issue["theme_of_day"]})
    items.sort(key=lambda x: x["date"], reverse=True)
    index_obj["items"] = items

    atomic_write_json(index_path, index_obj)

    # 3) quarantine：有才写；没有就不生成
    if quarantine_rows:
        atomic_write_json(quarantine_path, {"date": date_key, "run_id": issue["run_id"], "items": quarantine_rows})

    return {
        "today": today_path,
        "archive": archive_path,
        "index": index_path,
        **({"quarantine": quarantine_path} if quarantine_rows else {}),
    }