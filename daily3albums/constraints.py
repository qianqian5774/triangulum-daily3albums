from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ARTIST_COOLDOWN_DAYS = 7
THEME_COOLDOWN_DAYS = 3


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


def theme_key_from_tag(tag: str) -> str:
    return normalize_text(tag) or "unknown"


def style_key_from_parts(primary_tag: str, primary_type: str | None, first_release_year: int | None) -> str:
    del primary_type, first_release_year
    return theme_key_from_tag(primary_tag)


def _parse_decade_theme(value: str) -> tuple[int, int] | None:
    m = re.match(r"^\s*(\d{3})0s\s*$", str(value or ""), flags=re.IGNORECASE)
    if not m:
        return None
    start = int(m.group(1)) * 10
    return start, start + 9


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
            slot_theme_key = theme_key_from_tag(slot.get("theme_key") or slot.get("theme") or "")
            for pick in slot.get("picks") or []:
                album_key = pick.get("album_key") or album_key_from_parts(
                    pick.get("rg_mbid", ""), pick.get("title", ""), pick.get("artist_credit", ""), pick.get("first_release_year")
                )
                if album_key:
                    album_keys.add(album_key)
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
    decade_theme = issue.get("decade_theme") or issue.get("theme_of_day")
    decade_range = _parse_decade_theme(decade_theme)
    known_year_count = 0
    in_decade_count = 0
    unknown_year_count = 0

    for pick in picks:
        artist_keys = set(pick.get("artist_keys") or [])
        overlap = seen_artists.intersection(artist_keys)
        if overlap:
            errors.append(f"duplicate artist in same day: {sorted(overlap)}")
        seen_artists.update(artist_keys)

        style_key = pick.get("style_key", "")

        for key in artist_keys:
            last = history.artist_last_seen.get(key)
            if not last:
                continue
            if _date_delta_days(date_key, last) <= ARTIST_COOLDOWN_DAYS:
                errors.append(f"artist cooldown violation: {key} seen at {last}")

        last_style = history.style_last_seen.get(style_key)
        if style_key and last_style and _date_delta_days(date_key, last_style) <= THEME_COOLDOWN_DAYS:
            errors.append(f"theme cooldown violation: {style_key} seen at {last_style}")

        year = pick.get("first_release_year")
        if isinstance(year, int):
            known_year_count += 1
            if decade_range and decade_range[0] <= year <= decade_range[1]:
                in_decade_count += 1
        else:
            unknown_year_count += 1

    if decade_range:
        min_in_decade = int(issue.get("constraints", {}).get("min_in_decade", 6))
        max_unknown = int(issue.get("constraints", {}).get("max_unknown_year", 2))
        if in_decade_count < min_in_decade:
            errors.append(
                f"decade coverage violation: in_decade={in_decade_count} < required={min_in_decade} for {decade_theme}"
            )
        if unknown_year_count > max_unknown:
            errors.append(f"unknown year violation: unknown={unknown_year_count} > allowed={max_unknown}")

    return errors
