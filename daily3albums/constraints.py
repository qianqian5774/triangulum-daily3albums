from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ARTIST_COOLDOWN_DAYS = 7
STYLE_COOLDOWN_DAYS = 3


@dataclass
class HistoryIndex:
    album_keys: set[str]
    artist_last_seen: dict[str, str]
    style_last_seen: dict[str, str]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _date_delta_days(current_date_key: str, past_date_key: str) -> int:
    cur = date.fromisoformat(current_date_key)
    past = date.fromisoformat(past_date_key)
    return (cur - past).days


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


def style_key_from_parts(primary_tag: str, primary_type: str | None, first_release_year: int | None) -> str:
    tag = normalize_text(primary_tag) or "unknown"
    ptype = normalize_text(primary_type or "") or "unknown"
    decade = "unknown"
    if first_release_year:
        decade = f"{(int(first_release_year) // 10) * 10}s"
    return f"{tag}:{ptype}:{decade}"


def load_history_index(archive_dir: Path, current_date_key: str, max_lookback_days: int = 14) -> HistoryIndex:
    album_keys: set[str] = set()
    artist_last_seen: dict[str, str] = {}
    style_last_seen: dict[str, str] = {}
    if not archive_dir.exists():
        return HistoryIndex(album_keys=album_keys, artist_last_seen=artist_last_seen, style_last_seen=style_last_seen)

    for file in sorted(archive_dir.glob("*.json"), reverse=True):
        day = file.stem
        try:
            delta_days = _date_delta_days(current_date_key, day)
        except Exception:
            continue
        if delta_days <= 0 or delta_days > max_lookback_days:
            continue
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            continue
        slots = payload.get("slots") or []
        for slot in slots:
            for pick in slot.get("picks") or []:
                album_key = pick.get("album_key") or album_key_from_parts(
                    pick.get("rg_mbid", ""), pick.get("title", ""), pick.get("artist_credit", ""), pick.get("first_release_year")
                )
                if album_key:
                    album_keys.add(album_key)
                for artist_key in (pick.get("artist_keys") or artist_keys_from_parts(pick.get("artist_mbids") or [], pick.get("artist_credit", ""))):
                    if artist_key and artist_key not in artist_last_seen:
                        artist_last_seen[artist_key] = day
                style_key = pick.get("style_key") or style_key_from_parts(
                    ((pick.get("tags") or [{}])[0] or {}).get("name", ""),
                    pick.get("primary_type"),
                    pick.get("first_release_year"),
                )
                if style_key and style_key not in style_last_seen:
                    style_last_seen[style_key] = day

    return HistoryIndex(album_keys=album_keys, artist_last_seen=artist_last_seen, style_last_seen=style_last_seen)


def validate_today_constraints(issue: dict[str, Any], history: HistoryIndex) -> list[str]:
    errors: list[str] = []
    date_key = issue.get("date", "")
    picks = [pick for slot in issue.get("slots", []) for pick in slot.get("picks", [])]
    if len(picks) != 9:
        errors.append(f"expected 9 picks, got {len(picks)}")

    album_keys = [pick.get("album_key", "") for pick in picks]
    if len({k for k in album_keys if k}) != len(album_keys):
        errors.append("duplicate album_key in same day")

    seen_artists: set[str] = set()
    seen_styles: set[str] = set()
    for pick in picks:
        artist_keys = set(pick.get("artist_keys") or [])
        overlap = seen_artists.intersection(artist_keys)
        if overlap:
            errors.append(f"duplicate artist in same day: {sorted(overlap)}")
        seen_artists.update(artist_keys)

        style_key = pick.get("style_key", "")
        if style_key in seen_styles:
            errors.append(f"duplicate style_key in same day: {style_key}")
        seen_styles.add(style_key)

        for key in artist_keys:
            last = history.artist_last_seen.get(key)
            if not last:
                continue
            if _date_delta_days(date_key, last) <= ARTIST_COOLDOWN_DAYS:
                errors.append(f"artist cooldown violation: {key} seen at {last}")

        last_style = history.style_last_seen.get(style_key)
        if last_style and _date_delta_days(date_key, last_style) <= STYLE_COOLDOWN_DAYS:
            errors.append(f"style cooldown violation: {style_key} seen at {last_style}")

    return errors
