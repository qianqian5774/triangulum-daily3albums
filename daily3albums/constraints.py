from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


ARTIST_COOLDOWN_DAYS = 7
THEME_COOLDOWN_DAYS = 3
FALLBACK_COOLDOWN_DAYS = 3
STAGE3_DAILY_PICK_CAP = 1


class HistoryLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class CooldownPolicy:
    album_days: int = 7
    artist_days: int = ARTIST_COOLDOWN_DAYS
    theme_days: int = THEME_COOLDOWN_DAYS
    fallback_days: int = FALLBACK_COOLDOWN_DAYS
    stage3_daily_pick_cap: int = STAGE3_DAILY_PICK_CAP


@dataclass
class HistoryIndex:
    album_keys: set[str]
    artist_last_seen: dict[str, str]
    style_last_seen: dict[str, str]
    album_last_seen: dict[str, str] = field(default_factory=dict)
    album_identity_kind: dict[str, str] = field(default_factory=dict)
    dates: tuple[str, ...] = ()
    archive_count: int = 0
    picks_loaded: int = 0
    source: str = "empty"

    def album_identity_counts(self) -> dict[str, int]:
        counts = {"rg_mbid": 0, "fallback": 0}
        for kind in self.album_identity_kind.values():
            normalized = kind if kind in counts else "fallback"
            counts[normalized] += 1
        return counts


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _date_delta_days(current_date_key: str, past_date_key: str) -> int:
    cur = date.fromisoformat(current_date_key)
    past = date.fromisoformat(past_date_key)
    return (cur - past).days


def within_cooldown(current_date_key: str, past_date_key: str | None, days: int) -> bool:
    if not past_date_key:
        return False
    delta = _date_delta_days(current_date_key, past_date_key)
    return 0 < delta <= max(0, int(days))


def album_key_from_parts(rg_mbid: str, title: str, artist: str, year: int | None) -> str:
    if (rg_mbid or "").strip():
        return rg_mbid.strip()
    payload = f"{normalize_text(title)}|{normalize_text(artist)}|{year or 0}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"fallback:{digest[:20]}"


def artist_keys_from_parts(artist_mbids: list[str] | None, artist_credit: str) -> list[str]:
    keys = sorted({(x or "").strip() for x in (artist_mbids or []) if (x or "").strip()})
    if keys:
        return keys
    fallback = normalize_text(artist_credit)
    return [fallback] if fallback else []


def theme_key_from_tag(tag: str) -> str:
    return normalize_text(tag) or "unknown"


def style_key_from_parts(primary_tag: str, primary_type: str | None, first_release_year: int | None) -> str:
    del primary_type, first_release_year
    return theme_key_from_tag(primary_tag)


def _empty_history(source: str) -> HistoryIndex:
    return HistoryIndex(
        album_keys=set(),
        artist_last_seen={},
        style_last_seen={},
        source=source,
    )


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise HistoryLoadError(f"history {label} JSON is invalid: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise HistoryLoadError(f"history {label} must be an object: {path}")
    return payload


def _archive_paths(data_dir: Path, item: dict[str, Any]) -> list[Path]:
    date_key = str(item.get("date") or "")
    run_id = str(item.get("run_id") or "")
    paths: list[Path] = []
    if run_id:
        paths.append(data_dir / "archive" / date_key / f"{run_id}.json")
    paths.append(data_dir / "archive" / f"{date_key}.json")
    return paths


def load_history_index(
    data_dir: Path | None,
    current_date_key: str,
    max_lookback_days: int = 7,
    *,
    source: str = "local_output",
) -> HistoryIndex:
    album_keys: set[str] = set()
    album_last_seen: dict[str, str] = {}
    album_identity_kind: dict[str, str] = {}
    artist_last_seen: dict[str, str] = {}
    style_last_seen: dict[str, str] = {}
    if data_dir is None:
        return _empty_history("empty")
    if not data_dir.exists() or not data_dir.is_dir():
        raise HistoryLoadError(f"history source directory is missing: source={source} path={data_dir}")

    index_path = data_dir / "index.json"
    if not index_path.exists():
        raise HistoryLoadError(f"history index is missing: source={source} path={index_path}")
    index = _read_json_object(index_path, "index")
    items = index.get("items")
    if not isinstance(items, list):
        raise HistoryLoadError(f"history index items must be a list: {index_path}")

    current = date.fromisoformat(current_date_key)
    selected_by_date: dict[str, dict[str, Any]] = {}
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise HistoryLoadError(f"history index item must be an object: {index_path}")
        day = raw_item.get("date")
        run_id = raw_item.get("run_id")
        if not isinstance(day, str) or not isinstance(run_id, str) or not run_id.strip():
            raise HistoryLoadError(f"history index item requires date/run_id: {index_path}")
        try:
            archive_date = date.fromisoformat(day)
        except ValueError as exc:
            raise HistoryLoadError(f"history index contains invalid date: {day!r}") from exc
        delta_days = (current - archive_date).days
        if delta_days < 0:
            raise HistoryLoadError(f"history index contains future date: {day}")
        if delta_days == 0 or delta_days > max_lookback_days:
            continue
        previous = selected_by_date.get(day)
        if previous is None or str(raw_item.get("run_at") or "") > str(previous.get("run_at") or ""):
            selected_by_date[day] = raw_item

    dates = tuple(sorted(selected_by_date, reverse=True))
    picks_loaded = 0
    for day in dates:
        item = selected_by_date[day]
        candidates = [path for path in _archive_paths(data_dir, item) if path.exists()]
        if not candidates:
            raise HistoryLoadError(
                f"history archive is missing: date={day} run_id={item.get('run_id')} source={source}"
            )
        if len(candidates) > 1 and candidates[0].read_bytes() != candidates[1].read_bytes():
            raise HistoryLoadError(
                f"history archive aliases differ: date={day} run_id={item.get('run_id')} source={source}"
            )
        payload = _read_json_object(candidates[0], "archive")
        if payload.get("date") != day or payload.get("run_id") != item.get("run_id"):
            raise HistoryLoadError(
                f"history archive identity mismatch: date={day} run_id={item.get('run_id')} source={source}"
            )
        slots = payload.get("slots")
        if not isinstance(slots, list):
            raise HistoryLoadError(f"history archive slots must be a list: {candidates[0]}")
        for slot in slots:
            if not isinstance(slot, dict):
                raise HistoryLoadError(f"history archive slot must be an object: {candidates[0]}")
            slot_theme_key = theme_key_from_tag(slot.get("theme_key") or slot.get("theme") or "")
            picks = slot.get("picks")
            if not isinstance(picks, list):
                raise HistoryLoadError(f"history archive slot picks must be a list: {candidates[0]}")
            for pick in picks:
                if not isinstance(pick, dict):
                    raise HistoryLoadError(f"history archive pick must be an object: {candidates[0]}")
                picks_loaded += 1
                rg_mbid = str(pick.get("rg_mbid") or "").strip()
                fallback_key = str(pick.get("album_key") or "").strip()
                album_key = rg_mbid or fallback_key or album_key_from_parts(
                    "",
                    str(pick.get("title") or ""),
                    str(pick.get("artist_credit") or ""),
                    pick.get("first_release_year"),
                )
                if album_key:
                    album_keys.add(album_key)
                    if album_key not in album_last_seen:
                        album_last_seen[album_key] = day
                        album_identity_kind[album_key] = "rg_mbid" if rg_mbid else "fallback"
                for artist_key in (pick.get("artist_keys") or artist_keys_from_parts(pick.get("artist_mbids") or [], pick.get("artist_credit", ""))):
                    if artist_key and artist_key not in artist_last_seen:
                        artist_last_seen[artist_key] = day
                style_key = (
                    pick.get("style_key")
                    or pick.get("theme_key")
                    or slot_theme_key
                    or style_key_from_parts(((pick.get("tags") or [{}])[0] or {}).get("name", ""), None, None)
                )
                if style_key and style_key not in style_last_seen:
                    style_last_seen[style_key] = day

    return HistoryIndex(
        album_keys=album_keys,
        album_last_seen=album_last_seen,
        album_identity_kind=album_identity_kind,
        artist_last_seen=artist_last_seen,
        style_last_seen=style_last_seen,
        dates=dates,
        archive_count=len(dates),
        picks_loaded=picks_loaded,
        source=source,
    )


def validate_today_constraints(
    issue: dict[str, Any],
    history: HistoryIndex,
    *,
    policy: CooldownPolicy | None = None,
    slot_windows: dict[int, tuple[int, int]] | None = None,
    stage3_pick_count: int = 0,
) -> list[str]:
    policy = policy or CooldownPolicy()
    slot_windows = slot_windows or {}
    errors: list[str] = []
    date_key = issue.get("date", "")
    picks = [pick for slot in issue.get("slots", []) for pick in slot.get("picks", [])]
    if len(picks) != 9:
        errors.append(f"expected 9 picks, got {len(picks)}")

    album_keys = [pick.get("album_key", "") for pick in picks]
    if len({k for k in album_keys if k}) != len(album_keys):
        errors.append("duplicate album_key in same day")

    seen_artists: set[str] = set()
    for slot in issue.get("slots", []):
        slot_id = int(slot.get("slot_id", 0) or 0)
        album_days, artist_days = slot_windows.get(slot_id, (policy.album_days, policy.artist_days))
        for pick in slot.get("picks", []):
            artist_keys = set(pick.get("artist_keys") or [])
            overlap = seen_artists.intersection(artist_keys)
            if overlap:
                errors.append(f"duplicate artist in same day: {sorted(overlap)}")
            seen_artists.update(artist_keys)

            album_key = pick.get("album_key", "")
            last_album = history.album_last_seen.get(album_key)
            if album_key and within_cooldown(date_key, last_album, album_days):
                errors.append(f"album cooldown violation: {album_key} seen at {last_album}")

            style_key = pick.get("style_key", "")

            for key in artist_keys:
                last = history.artist_last_seen.get(key)
                if not last:
                    continue
                if within_cooldown(date_key, last, artist_days):
                    errors.append(f"artist cooldown violation: {key} seen at {last}")

            last_style = history.style_last_seen.get(style_key)
            if style_key and within_cooldown(date_key, last_style, policy.theme_days):
                errors.append(f"theme cooldown violation: {style_key} seen at {last_style}")

    if stage3_pick_count > policy.stage3_daily_pick_cap:
        errors.append(
            f"stage3 daily cap exceeded: {stage3_pick_count} > {policy.stage3_daily_pick_cap}"
        )

    return errors
