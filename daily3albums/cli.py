from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import random
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from daily3albums.config import load_env, load_config
from daily3albums.request_broker import BrokerRequestError, RequestBroker
from daily3albums.adapters import CoverArtArchiveAdapter, CoverArtResult, lastfm_tag_top_albums, musicbrainz_search_release_group
from daily3albums.constraints import (
    ARTIST_COOLDOWN_DAYS,
    THEME_COOLDOWN_DAYS,
    album_key_from_parts,
    artist_keys_from_parts,
    load_history_index,
    style_key_from_parts,
    theme_key_from_tag,
    validate_today_constraints,
)
from daily3albums.dry_run import run_dry_run


# ----------------------------
# doctor / probes / dry-run
# ----------------------------

def cmd_doctor(repo_root: Path) -> int:
    _ = load_env(repo_root)
    cfg = load_config(repo_root)
    print("DOCTOR")
    print(f"timezone={cfg.timezone}")
    print("config=OK")
    print("env=OK")
    return 0


def cmd_probe_lastfm(repo_root: Path, tag: str, limit: int, verbose: bool, raw: bool) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    try:
        if raw:
            from urllib.parse import urlencode

            params = {
                "method": "tag.getTopAlbums",
                "tag": tag,
                "limit": str(limit),
                "page": "1",
                "api_key": env.lastfm_api_key,
                "format": "json",
            }
            url = "https://ws.audioscrobbler.com/2.0/?" + urlencode(params)
            j = broker.get_json(url, adapter_name="LastfmAdapter")
            print(json.dumps(j, ensure_ascii=False, indent=2))
            return 0

        albums = lastfm_tag_top_albums(broker, lastfm_api_key=env.lastfm_api_key, tag=tag, limit=limit)
        print(json.dumps([a.__dict__ for a in albums[:limit]], ensure_ascii=False, indent=2))
        return 0
    finally:
        broker.close()


def cmd_probe_mb(repo_root: Path, artist: str, title: str, limit: int, verbose: bool) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    try:
        rgs = musicbrainz_search_release_group(
            broker,
            mb_user_agent=env.mb_user_agent,
            title=title,
            artist=artist,
            limit=limit,
        )
        print(json.dumps([rg.__dict__ for rg in rgs], ensure_ascii=False, indent=2))
        return 0
    finally:
        broker.close()


def cmd_dry_run(
    repo_root: Path,
    tag: str,
    n: int,
    topk: int,
    verbose: bool,
    split_slots: bool,
    mb_search_limit: int,
    min_confidence: float,
    ambiguity_gap: float,
    mb_debug: bool,
    quarantine_out: str,
) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    mb_search_limit = int(mb_search_limit)
    min_confidence = float(min_confidence)
    ambiguity_gap = float(ambiguity_gap)
    quarantine_out = (quarantine_out or "").strip() or None
    prefilter_topn = int((cfg.raw.get("scoring", {}) or {}).get("mb_prefilter_topn", 120))

    try:
        out = run_dry_run(
            broker,
            env,
            tag=tag,
            n=n,
            topk=topk,
            split_slots=split_slots,
            mb_search_limit=mb_search_limit,
            min_confidence=min_confidence,
            ambiguity_gap=ambiguity_gap,
            mb_debug=mb_debug,
            quarantine_out=quarantine_out,
            prefilter_topn=prefilter_topn,
        )

        print("\n== Candidates ==")
        for c in out["candidates"]:
            print(
                f"rank={c.lastfm_rank} | artist={c.artist} | title={c.title} | "
                f"lastfm_mbid={c.lastfm_mbid} | image_url={c.image_url}"
            )

        print("\n== Normalized (per candidate) ==")
        for s in out["scored"]:
            if s.n is None:
                print(
                    f"rank={s.c.lastfm_rank} | {s.c.artist} - {s.c.title} | "
                    f"mb_release_group_id=<none> | first_release_date=<none> | primary_type=<none>"
                )
            else:
                print(
                    f"rank={s.c.lastfm_rank} | {s.c.artist} - {s.c.title} | "
                    f"mb_release_group_id={s.n.mb_release_group_id} | "
                    f"first_release_date={s.n.first_release_date} | primary_type={s.n.primary_type} | "
                    f"source={s.n.source} | confidence={s.n.confidence:.2f}"
                )

            if mb_debug and s.mb_debug:
                for line in s.mb_debug[:30]:
                    print(f"  mb_debug: {line}")

        print(f"\n== Top {topk} ==")
        for s in out["top"]:
            rg = s.n.mb_release_group_id if s.n else ""
            dt = s.n.first_release_date if s.n else ""
            pt = s.n.primary_type if s.n else ""
            print(
                f"score={s.score} | rg_id={rg} | date={dt} | type={pt} | "
                f"rank={s.c.lastfm_rank} | {s.c.artist} - {s.c.title} | {s.reason}"
            )

        if split_slots:
            slots = out.get("slots") or {}
            print("\n== Slots ==")
            for name in ("Headliner", "Lineage", "DeepCut"):
                ss = slots.get(name)
                if ss is None:
                    print(f"{name}: <none>")
                    continue
                rg = ss.n.mb_release_group_id if ss.n else ""
                dt = ss.n.first_release_date if ss.n else ""
                pt = ss.n.primary_type if ss.n else ""
                print(f"{name}: score={ss.score} | {dt} | {pt} | {rg} | {ss.c.artist} - {ss.c.title}")

        if quarantine_out:
            print("\n== Quarantine ==")
            print(f"written_to={quarantine_out}")

        return 0
    finally:
        broker.close()


# ----------------------------
# helpers (build)
# ----------------------------

MAX_TAG_TRIES_PER_SLOT = 8

_DEFAULT_TAG_POOL = [
    "ambient",
    "drone",
    "electronic",
    "experimental",
    "fourth world",
    "idm",
    "jazz",
    "minimalism",
    "new age",
    "post-rock",
    "soundscape",
    "techno",
]


def _now_date_in_tz(tz_name: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.now(ZoneInfo(tz_name))
    except Exception:
        dt = datetime.now()
    return dt.date().isoformat()


def _beijing_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        return datetime.now()


def _beijing_slot(dt: datetime) -> int:
    hour = dt.hour
    if hour < 12:
        return 0
    if hour < 18:
        return 1
    return 2


def _slot_label(slot_id: int) -> str:
    if slot_id == 0:
        return "06:00-11:59"
    if slot_id == 1:
        return "12:00-17:59"
    return "18:00-23:59"


def _hash_index(seed: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def _get_tag_pool(cfg: Any) -> list[str]:
    pool = cfg.raw.get("tag_pool") if hasattr(cfg, "raw") else None
    if isinstance(pool, list):
        cleaned = [str(x).strip() for x in pool if str(x).strip()]
        if cleaned:
            return cleaned
    return list(_DEFAULT_TAG_POOL)


def _get_build_logger(repo_root: Path) -> logging.Logger:
    logger = logging.getLogger("build")
    if logger.handlers:
        return logger
    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "build.log"
    log_path.touch(exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _select_tag(tag_arg: str | None, cfg: Any, beijing_now: datetime, log_line: callable) -> tuple[str, int, str, list[str]]:
    raw = (tag_arg or "").strip()
    slot = _beijing_slot(beijing_now)
    if raw and raw.lower() not in {"auto", "all"}:
        log_line(f"tag_mode=manual beijing_now={beijing_now.isoformat()} slot={slot} selected_tag={raw}")
        return raw, slot, "", []
    pool = _get_tag_pool(cfg)
    if not pool:
        raise RuntimeError("TAG_POOL is empty; configure config.yaml tag_pool.")
    seed = f"{beijing_now.date().isoformat()}:{slot}"
    selected = pool[_hash_index(seed, len(pool))]
    log_line(
        "tag_mode=auto "
        f"beijing_now={beijing_now.isoformat()} slot={slot} seed={seed} selected_tag={selected}"
    )
    return selected, slot, seed, pool


def _select_tag_for_slot(tag_arg: str | None, cfg: Any, date_key: str, slot_id: int, log_line: callable) -> str:
    raw = (tag_arg or "").strip()
    if raw and raw.lower() not in {"auto", "all"}:
        log_line(f"tag_mode=manual slot={slot_id} selected_tag={raw}")
        return raw
    pool = _get_tag_pool(cfg)
    if not pool:
        raise RuntimeError("TAG_POOL is empty; configure config.yaml tag_pool.")
    seed = f"{date_key}:{slot_id}"
    selected = pool[_hash_index(seed, len(pool))]
    log_line(f"tag_mode=auto slot={slot_id} seed={seed} selected_tag={selected}")
    return selected


def _load_recent_stable_ids(out_public_dir: Path, max_runs: int) -> list[str]:
    index_path = out_public_dir / "data" / "index.json"
    if not index_path.exists():
        return []
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    def sort_key(item: dict[str, Any]) -> str:
        run_at = item.get("run_at")
        if isinstance(run_at, str):
            return run_at
        return f"{item.get('date','')}-{item.get('run_id','')}"

    items_sorted = sorted(
        [x for x in items if isinstance(x, dict)],
        key=sort_key,
        reverse=True,
    )
    recent_ids: list[str] = []
    runs_checked = 0
    for item in items_sorted:
        if runs_checked >= max_runs:
            break
        date = item.get("date")
        run_id = item.get("run_id")
        if not isinstance(date, str) or not date:
            continue
        archive_path = (
            out_public_dir / "data" / "archive" / date / f"{run_id}.json"
            if isinstance(run_id, str) and run_id
            else out_public_dir / "data" / "archive" / f"{date}.json"
        )
        if not archive_path.exists():
            continue
        try:
            issue = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        picks = issue.get("picks") if isinstance(issue, dict) else None
        if not isinstance(picks, list):
            continue
        for pick in picks:
            if isinstance(pick, dict) and isinstance(pick.get("rg_mbid"), str) and pick["rg_mbid"]:
                recent_ids.append(pick["rg_mbid"])
        runs_checked += 1
    return recent_ids


def _softmax_weights(scores: list[float], temperature: float = 10.0) -> list[float]:
    if not scores:
        return []
    max_score = max(scores)
    exp_scores = [math.exp((s - max_score) / temperature) for s in scores]
    total = sum(exp_scores)
    if total <= 0:
        return [1.0 / len(scores)] * len(scores)
    return [s / total for s in exp_scores]


def _weighted_sample(
    items: list[Any],
    count: int,
    rng: random.Random,
    recent_ids: set[str],
    cooling_penalty: float | None,
    temperature: float = 10.0,
) -> tuple[list[Any], int]:
    unique_items: list[tuple[Any, float, bool]] = []
    seen_rg: set[str] = set()
    cooling_hits = 0
    for item in items:
        rg_id = getattr(getattr(item, "n", None), "mb_release_group_id", "") or ""
        if not rg_id or rg_id in seen_rg:
            continue
        seen_rg.add(rg_id)
        is_recent = rg_id in recent_ids
        if is_recent:
            cooling_hits += 1
        score = float(getattr(item, "score", 0.0))
        unique_items.append((item, score, is_recent))

    scores = [s for _, s, _ in unique_items]
    weights = _softmax_weights(scores, temperature=temperature)

    if cooling_penalty is not None:
        adjusted = []
        for (item, score, is_recent), weight in zip(unique_items, weights):
            if is_recent:
                weight *= max(cooling_penalty, 0.0)
            adjusted.append((item, weight))
    else:
        adjusted = [(item, weight) for (item, _score, _), weight in zip(unique_items, weights)]

    picks: list[Any] = []
    candidates = adjusted[:]
    while candidates and len(picks) < count:
        total = sum(weight for _, weight in candidates)
        if total <= 0:
            break
        r = rng.random() * total
        upto = 0.0
        chosen_idx = None
        for idx, (_item, weight) in enumerate(candidates):
            upto += weight
            if upto >= r:
                chosen_idx = idx
                break
        if chosen_idx is None:
            break
        item, _weight = candidates.pop(chosen_idx)
        picks.append(item)
    return picks, cooling_hits


def _threshold_steps(min_confidence: float, ambiguity_gap: float) -> list[tuple[float, float]]:
    steps: list[tuple[float, float]] = []
    min_steps = [0.0, -0.05, -0.10, -0.15]
    gap_steps = [0.0, -0.02, -0.04, -0.06]
    for d_conf, d_gap in zip(min_steps, gap_steps):
        new_conf = max(0.50, min_confidence + d_conf)
        new_gap = max(0.0, ambiguity_gap + d_gap)
        steps.append((round(new_conf, 3), round(new_gap, 3)))
    seen = set()
    unique_steps = []
    for conf, gap in steps:
        if (conf, gap) in seen:
            continue
        seen.add((conf, gap))
        unique_steps.append((conf, gap))
    return unique_steps


def _normalize_artist_credit(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+(feat\.|featuring|ft\.)\s+.*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _artist_identity(s: Any) -> tuple[set[str], str]:
    n = getattr(s, "n", None)
    mbids = []
    if n is not None:
        mbids = [str(x).strip() for x in (getattr(n, "artist_mbids", None) or []) if str(x).strip()]
    fallback = _normalize_artist_credit(getattr(getattr(s, "c", None), "artist", "") or "")
    return set(mbids), fallback


def _weighted_sample_unique_artists(
    items: list[Any],
    count: int,
    rng: random.Random,
    recent_ids: set[str],
    cooling_penalty: float | None,
    log_line: callable,
    temperature: float = 10.0,
) -> tuple[list[Any], int]:
    unique_items: list[tuple[Any, float, bool]] = []
    seen_rg: set[str] = set()
    cooling_hits = 0
    for item in items:
        rg_id = getattr(getattr(item, "n", None), "mb_release_group_id", "") or ""
        if not rg_id or rg_id in seen_rg:
            continue
        seen_rg.add(rg_id)
        is_recent = rg_id in recent_ids
        if is_recent:
            cooling_hits += 1
        score = float(getattr(item, "score", 0.0))
        unique_items.append((item, score, is_recent))

    scores = [s for _, s, _ in unique_items]
    weights = _softmax_weights(scores, temperature=temperature)

    if cooling_penalty is not None:
        adjusted = []
        for (item, score, is_recent), weight in zip(unique_items, weights):
            if is_recent:
                weight *= max(cooling_penalty, 0.0)
            adjusted.append((item, weight))
    else:
        adjusted = [(item, weight) for (item, _score, _), weight in zip(unique_items, weights)]

    picks: list[Any] = []
    used_mbids: set[str] = set()
    used_fallbacks: set[str] = set()
    candidates = adjusted[:]
    attempts = 0
    max_attempts = len(candidates) * 2 if candidates else 0
    while candidates and len(picks) < count and attempts <= max_attempts:
        attempts += 1
        total = sum(weight for _, weight in candidates)
        if total <= 0:
            break
        r = rng.random() * total
        upto = 0.0
        chosen_idx = None
        for idx, (_item, weight) in enumerate(candidates):
            upto += weight
            if upto >= r:
                chosen_idx = idx
                break
        if chosen_idx is None:
            break
        item, _weight = candidates.pop(chosen_idx)
        mbids, fallback = _artist_identity(item)
        conflict = False
        if mbids and used_mbids.intersection(mbids):
            conflict = True
        if fallback and fallback in used_fallbacks:
            conflict = True
        if conflict:
            log_line(
                "artist_conflict "
                f"slot_index={len(picks)} "
                f"candidate_rg={getattr(getattr(item, 'n', None), 'mb_release_group_id', '') or ''} "
                f"candidate_mbids={sorted(mbids)} candidate_fallback={fallback or 'n/a'} "
                f"used_mbids={sorted(used_mbids)} used_fallbacks={sorted(used_fallbacks)}"
            )
            continue
        picks.append(item)
        used_mbids.update(mbids)
        if fallback:
            used_fallbacks.add(fallback)
    return picks, cooling_hits


def _assign_slots(items: list[Any]) -> dict[str, Any]:
    if not items:
        return {"Headliner": None, "Lineage": None, "DeepCut": None}

    headliner = items[0]

    def year_key(s: Any) -> int:
        n = getattr(s, "n", None)
        if not n or not getattr(n, "first_release_date", None):
            return 999999
        y = str(n.first_release_date)[:4]
        return int(y) if y.isdigit() else 999999

    lineage = min(items, key=year_key)

    deepcut = None
    for s in items:
        if s is headliner or s is lineage:
            continue
        deepcut = s
        break

    return {"Headliner": headliner, "Lineage": lineage, "DeepCut": deepcut}


def _safe_year(first_release_date: str | None) -> int | None:
    if not first_release_date:
        return None
    s = str(first_release_date).strip()
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return None


def _youtube_search_url(artist: str, title: str) -> str:
    from urllib.parse import quote_plus
    q = quote_plus(f"{artist} {title} full album")
    return f"https://www.youtube.com/results?search_query={q}"


def _copy_tree_overwrite(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        out_dir = dst / rel
        out_dir.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (out_dir / d).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = Path(root) / f
            t = out_dir / f
            shutil.copy2(s, t)


def _read_quarantine_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items


def _pick_to_issue_item(
    tag: str,
    slot: str,
    s: Any,
    cover_version: str | None = None,
    cover_result: CoverArtResult | None = None,
) -> dict[str, Any]:
    c = s.c
    n = s.n

    rg_id = getattr(n, "mb_release_group_id", "") if n else ""
    frd = getattr(n, "first_release_date", None) if n else None
    ptype = getattr(n, "primary_type", None) if n else None
    conf = float(getattr(n, "confidence", 0.0)) if n else 0.0

    artist = getattr(c, "artist", "")
    title = getattr(c, "title", "")
    fallback_image = getattr(c, "image_url", "") or ""

    cover_url = cover_result.optimized_cover_url if cover_result and cover_result.has_cover else fallback_image
    optimized_cover_url = cover_url or "assets/placeholder.svg"

    artist_mbids = list(getattr(n, "artist_mbids", []) or []) if n else []
    first_release_year = _safe_year(frd)
    album_key = album_key_from_parts(rg_id, title, artist, first_release_year)
    artist_keys = artist_keys_from_parts(artist_mbids, artist)
    style_key = style_key_from_parts(tag, ptype, first_release_year)

    return {
        "slot": slot,
        "rg_mbid": rg_id,
        "title": title,
        "artist_credit": artist,
        "artist_mbids": artist_mbids,
        "first_release_year": first_release_year,
        "primary_type": ptype,
        "album_key": album_key,
        "artist_keys": artist_keys,
        "style_key": style_key,
        "secondary_types": [],
        "tags": [{"name": tag, "source": "lastfm"}],
        "popularity": None,
        "cover": {
            "has_cover": bool(cover_url),
            "optimized_cover_url": optimized_cover_url,
            "cover_version": cover_version,
            "source_release_mbid": cover_result.release_mbid if cover_result else None,
            "original_cover_url": cover_result.original_cover_url if cover_result else (fallback_image or None),
        },
        "links": {
            "musicbrainz": f"https://musicbrainz.org/release-group/{rg_id}" if rg_id else None,
            "lastfm": None,
            "youtube_search": _youtube_search_url(artist, title) if (artist and title) else None,
        },
        "facts": [],
        "blurb": "",
        "evidence": {"from_sources": ["lastfm", "musicbrainz"], "mapping_confidence": conf},
        "score": float(getattr(s, "score", 0.0)),
        "reason": getattr(s, "reason", ""),
    }


def _write_text_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def _builtin_min_index_html() -> str:
    # ASCII-only to avoid PowerShell encoding pitfalls.
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Daily 3 Albums</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
    header { margin-bottom: 18px; }
    .meta { color: #666; font-size: 14px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
    .card { border: 1px solid #ddd; border-radius: 12px; overflow: hidden; }
    .cover { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: #f2f2f2; display:block; }
    .content { padding: 12px 12px 14px; }
    .slot { font-size: 12px; color: #666; letter-spacing: .5px; }
    .title { margin: 6px 0 2px; font-weight: 700; }
    .artist { margin: 0; color: #333; }
    .sub { margin-top: 8px; font-size: 12px; color: #666; line-height: 1.4; }
    .err { color: #b00020; white-space: pre-wrap; }
  </style>
</head>
<body>
  <header>
    <h1 style="margin:0;">Daily 3 Albums</h1>
    <div class="meta" id="meta">loading...</div>
  </header>

  <div id="app"></div>

  <script>
    async function main() {
      const app = document.getElementById('app');
      try {
        const res = await fetch('data/today.json', { cache: 'no-store' });
        if (!res.ok) throw new Error('fetch data/today.json failed: ' + res.status);
        const j = await res.json();

        document.getElementById('meta').textContent =
          j.date + ' | theme: ' + j.theme_of_day + ' | run: ' + j.run_id;

        const picks = j.picks || [];
        const grid = document.createElement('div');
        grid.className = 'grid';

        for (const p of picks) {
          const card = document.createElement('div');
          card.className = 'card';

          const img = document.createElement('img');
          img.className = 'cover';
          img.src = (p.cover && p.cover.optimized_cover_url) ? p.cover.optimized_cover_url : 'assets/placeholder.svg';
          img.alt = (p.artist_credit || '') + ' - ' + (p.title || '');
          card.appendChild(img);

          const content = document.createElement('div');
          content.className = 'content';

          const slot = document.createElement('div');
          slot.className = 'slot';
          slot.textContent = p.slot || '';
          content.appendChild(slot);

          const title = document.createElement('div');
          title.className = 'title';
          title.textContent = p.title || '';
          content.appendChild(title);

          const artist = document.createElement('p');
          artist.className = 'artist';
          artist.textContent = p.artist_credit || '';
          content.appendChild(artist);

          const sub = document.createElement('div');
          sub.className = 'sub';
          const y = p.first_release_year ? String(p.first_release_year) : '';
          const t = p.primary_type ? String(p.primary_type) : '';
          sub.textContent = [y, t, p.rg_mbid].filter(Boolean).join(' | ');
          content.appendChild(sub);

          card.appendChild(content);
          grid.appendChild(card);
        }

        app.innerHTML = '';
        app.appendChild(grid);
      } catch (e) {
        app.innerHTML = '<div class="err">' + String(e) + '</div>';
        console.error(e);
      }
    }
    main();
  </script>
</body>
</html>
"""


def _ensure_nonblank_index_html(out_public_dir: Path, web_dir: Path) -> None:
    """
    Strategy:
      - Copy web/ to out dir if web exists.
      - If out/index.html is missing or empty, write a built-in minimal index.html to out dir.
    This avoids "200 but blank page" failure mode.
    """
    out_index = out_public_dir / "index.html"
    if out_index.exists() and out_index.stat().st_size > 0:
        return
    # if web/index.html exists but got copied as empty, also protect
    _write_text_utf8(out_index, _builtin_min_index_html())


# ----------------------------
# build
# ----------------------------


def _type_flags_from_cfg(cfg: Any) -> dict[str, bool]:
    defaults = {"album": True, "compilation": False, "live": False, "ep": False, "single": False}
    node = cfg.raw.get("allow_types") if hasattr(cfg, "raw") else None
    if isinstance(node, dict):
        for k in defaults:
            if k in node:
                defaults[k] = bool(node.get(k))
    return defaults


def _is_various_artists_name(name: str) -> bool:
    n = (name or "").strip().lower()
    return n in {"various artists", "various", "v/a", "va"}


def _primary_type_allowed(primary_type: str | None, flags: dict[str, bool]) -> bool:
    if not primary_type:
        return True
    key = str(primary_type).strip().lower()
    if key == "album":
        return flags.get("album", True)
    if key in {"compilation", "live", "ep", "single"}:
        return bool(flags.get(key, False))
    return True


def _deterministic_decade_theme(date_key: str) -> str:
    decades = [f"{y}s" for y in range(1960, 2020, 10)]
    return decades[_hash_index(f"{date_key}:decade", len(decades))]


def cmd_build(
    repo_root: Path,
    tag: str,
    n: int,
    topk: int,
    verbose: bool,
    split_slots: bool,
    mb_search_limit: int,
    min_confidence: float,
    ambiguity_gap: float,
    mb_debug: bool,
    quarantine_out: str,
    out_dir: str,
    date_override: str,
    theme: str,
) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)
    build_logger = _get_build_logger(repo_root)

    def log_line(msg: str) -> None:
        if verbose:
            print(msg)
        build_logger.info(msg)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    cover_adapter = CoverArtArchiveAdapter(broker)
    type_flags = _type_flags_from_cfg(cfg)

    mb_search_limit = int(mb_search_limit)
    prefilter_topn = int((cfg.raw.get("scoring", {}) or {}).get("mb_prefilter_topn", 120))
    quarantine_out = (quarantine_out or "").strip() or None
    out_public_dir = (repo_root / out_dir).resolve()

    try:
        beijing_now = _beijing_now()
        bjt_date_key = beijing_now.date().isoformat()
        if (date_override or "").strip() and date_override.strip() != bjt_date_key:
            print(
                "BUILD ERROR: date override does not match Asia/Shanghai date. "
                f"override={date_override.strip()} bjt_date={bjt_date_key}"
            )
            return 2
        date_key = bjt_date_key
        now_slot_id = _beijing_slot(beijing_now)
        run_id = f"{date_key}_slots_{uuid.uuid4().hex[:6]}"

        recent_ids = _load_recent_stable_ids(out_public_dir, max_runs=9)
        recent_set = set(recent_ids)
        history_index = load_history_index(out_public_dir / "data" / "archive", current_date_key=bjt_date_key, max_lookback_days=14)

        slot_names = ["Headliner", "Lineage", "DeepCut"]
        slots_payload: list[dict[str, Any]] = []
        used_album_keys: set[str] = set()
        used_artist_keys: set[str] = set()
        used_theme_keys: set[str] = set()
        exhaustion: list[dict[str, Any]] = []

        for slot_id in range(3):
            pool = _get_tag_pool(cfg)
            start_index = _hash_index(f"{date_key}:{slot_id}", len(pool))
            tag_attempts = [pool[(start_index + i) % len(pool)] for i in range(len(pool))]
            if used_theme_keys:
                tag_attempts = sorted(tag_attempts, key=lambda t: (theme_key_from_tag(t) in used_theme_keys, tag_attempts.index(t)))
            max_tag_tries = int((cfg.raw.get("build", {}) or {}).get("max_tag_tries_per_slot", MAX_TAG_TRIES_PER_SLOT))
            tag_attempts = tag_attempts[:max_tag_tries]

            picked: list[Any] = []
            picked_theme_tag = ""
            picked_theme_key = ""
            reject_counts = {"va": 0, "type": 0, "artist_cooldown": 0, "artist_same_day": 0, "album_collision": 0}
            fetched_count = 0
            attempts_meta: list[dict[str, Any]] = []

            for slot_tag in tag_attempts:
                theme_key = theme_key_from_tag(slot_tag)
                last_theme_day = history_index.style_last_seen.get(theme_key)
                if last_theme_day:
                    delta = (datetime.fromisoformat(bjt_date_key).date() - datetime.fromisoformat(last_theme_day).date()).days
                    if delta <= THEME_COOLDOWN_DAYS:
                        attempts_meta.append({"tag": slot_tag, "theme_key": theme_key, "skipped": "theme_cooldown", "last_seen": last_theme_day})
                        continue

                for fetch_limit in (max(n, 200), 800):
                    deepcut = (slot_id == 2)
                    seed_key = f"{date_key}:{slot_id}:{slot_tag}"
                    try:
                        out = run_dry_run(
                            broker,
                            env,
                            tag=slot_tag,
                            n=fetch_limit,
                            topk=max(fetch_limit, topk),
                            deepcut=deepcut,
                            seed_key=seed_key,
                            split_slots=False,
                            mb_search_limit=mb_search_limit,
                            min_confidence=float(min_confidence),
                            ambiguity_gap=float(ambiguity_gap),
                            mb_debug=mb_debug,
                            quarantine_out=None,
                            prefilter_topn=prefilter_topn,
                        )
                    except BrokerRequestError as e:
                        attempts_meta.append({
                            "tag": slot_tag,
                            "theme_key": theme_key,
                            "fetch_limit": fetch_limit,
                            "network_failed": True,
                            "error": str(e),
                            "candidate_count": 0,
                            "candidate_count_after_light_prefilter": 0,
                            "candidate_count_after_hard_filters": 0,
                        })
                        log_line(f"network_failed slot={slot_id} tag={slot_tag} fetch_limit={fetch_limit} error={e}")
                        break

                    prefetched = int(out.get("prefilter_total", len(out.get("candidates") or [])))
                    topn = int(out.get("prefilter_topn", len(out.get("scored") or [])))
                    normalized = int(out.get("normalized_count", len(out.get("scored") or [])))
                    saved_calls = max(0, prefetched - normalized)
                    log_line(
                        f"prefilter slot={slot_id} tag={slot_tag} fetch_limit={fetch_limit} "
                        f"fetched_candidates={prefetched} after_light_prefilter_topN={topn} "
                        f"mb_normalized={normalized} saved_mb_calls={saved_calls}"
                    )

                    candidates = [s for s in (out.get("top") or []) if getattr(s, "n", None) is not None]
                    fetched_count = max(fetched_count, len(candidates))
                    eligible: list[Any] = []
                    local_reject = {k: 0 for k in reject_counts}
                    for candidate in candidates:
                        nobj = getattr(candidate, "n", None)
                        cobj = getattr(candidate, "c", None)
                        rg_id = getattr(nobj, "mb_release_group_id", "") if nobj else ""
                        title = getattr(cobj, "title", "") if cobj else ""
                        artist = getattr(cobj, "artist", "") if cobj else ""
                        year = _safe_year(getattr(nobj, "first_release_date", None) if nobj else None)
                        ptype = getattr(nobj, "primary_type", None) if nobj else None
                        artist_mbids = list(getattr(nobj, "artist_mbids", []) or []) if nobj else []

                        album_key = album_key_from_parts(rg_id, title, artist, year)
                        artist_keys = set(artist_keys_from_parts(artist_mbids, artist))
                        if _is_various_artists_name(artist):
                            local_reject["va"] += 1
                            continue
                        if not _primary_type_allowed(ptype, type_flags):
                            local_reject["type"] += 1
                            continue
                        if album_key in used_album_keys:
                            local_reject["album_collision"] += 1
                            continue
                        if artist_keys.intersection(used_artist_keys):
                            local_reject["artist_same_day"] += 1
                            continue
                        violate_cooldown = False
                        for key in artist_keys:
                            last = history_index.artist_last_seen.get(key)
                            if last and (datetime.fromisoformat(bjt_date_key).date() - datetime.fromisoformat(last).date()).days <= ARTIST_COOLDOWN_DAYS:
                                violate_cooldown = True
                                break
                        if violate_cooldown:
                            local_reject["artist_cooldown"] += 1
                            continue
                        eligible.append(candidate)

                    for k, v in local_reject.items():
                        reject_counts[k] += v
                    attempts_meta.append({"tag": slot_tag, "theme_key": theme_key, "fetch_limit": fetch_limit, "candidate_count": prefetched, "candidate_count_after_light_prefilter": topn, "candidate_count_after_hard_filters": len(eligible), "reject_counts": dict(local_reject), "eligible": len(eligible)})
                    if len(eligible) >= 3:
                        rng = random.Random(f"{date_key}:{slot_id}:{theme_key}")
                        slot_temperature = 9.0 if slot_id == 0 else (10.0 if slot_id == 1 else 14.0)
                        picked, _ = _weighted_sample_unique_artists(
                            eligible,
                            count=3,
                            rng=rng,
                            recent_ids=recent_set,
                            cooling_penalty=None,
                            log_line=log_line,
                            temperature=slot_temperature,
                        )
                        if len(picked) >= 3:
                            picked_theme_tag = slot_tag
                            picked_theme_key = theme_key
                            break
                if len(picked) >= 3:
                    break

            if len(picked) < 3:
                tried_tags = [a.get("tag") for a in attempts_meta if isinstance(a, dict) and a.get("tag")]
                unique_tags = list(dict.fromkeys(tried_tags))
                diag = {
                    "slot_id": slot_id,
                    "tags_tried": len(unique_tags),
                    "max_tag_tries_per_slot": max_tag_tries,
                    "tag_attempts": attempts_meta,
                    "reject_counts": reject_counts,
                }
                print(f"BUILD ERROR: slot={slot_id} exhausted after {len(unique_tags)} tags (cap={max_tag_tries})")
                print(f"exhaustion slot={slot_id} diagnostic={diag}")
                log_line(f"slot_exhausted {json.dumps(diag, ensure_ascii=False)}")
                exhaustion.append(diag)
                return 2

            scored_items = sorted(picked, key=lambda s: float(getattr(s, "score", 0.0)), reverse=True)[:3]
            for selected in scored_items:
                nobj = getattr(selected, "n", None)
                cobj = getattr(selected, "c", None)
                rg_id = getattr(nobj, "mb_release_group_id", "") if nobj else ""
                title = getattr(cobj, "title", "") if cobj else ""
                artist = getattr(cobj, "artist", "") if cobj else ""
                year = _safe_year(getattr(nobj, "first_release_date", None) if nobj else None)
                artist_mbids = list(getattr(nobj, "artist_mbids", []) or []) if nobj else []
                used_album_keys.add(album_key_from_parts(rg_id, title, artist, year))
                used_artist_keys.update(artist_keys_from_parts(artist_mbids, artist))

            used_theme_keys.add(picked_theme_key)
            slot_payload = {
                "slot_id": slot_id,
                "window_label": _slot_label(slot_id),
                "theme": picked_theme_tag,
                "theme_key": picked_theme_key,
                "constraints": {"min_confidence": float(min_confidence), "ambiguity_gap": float(ambiguity_gap)},
                "picks": [],
                "scored_items": scored_items,
            }
            slots_payload.append(slot_payload)
            exhaustion.append({"slot_id": slot_id, "attempts": attempts_meta, "reject_counts": reject_counts, "fetched_count": fetched_count})

        decade_theme = (theme or "").strip() or _deterministic_decade_theme(date_key)
        decade_constraints = {"min_in_decade": 6, "max_unknown_year": 2}

        issue = {
            "output_schema_version": "1.0",
            "date": date_key,
            "run_id": run_id,
            "theme_of_day": decade_theme,
            "decade_theme": decade_theme,
            "slot": now_slot_id,
            "now_slot_id": now_slot_id,
            "run_at": beijing_now.isoformat(timespec="seconds"),
            "lineage_source": None,
            "picks": [],
            "constraints": {**decade_constraints, "min_confidence": float(min_confidence), "ambiguity_gap": float(ambiguity_gap)},
            "slots": [],
            "generation": {"started_at": datetime.now().isoformat(timespec="seconds"), "versions": {"daily3albums": getattr(cfg, "version", None)}},
            "warnings": [],
            "diagnostics": {"exhaustion": exhaustion},
        }

        cover_version = issue["generation"].get("started_at")
        for slot_payload in slots_payload:
            scored_items = slot_payload.pop("scored_items", [])
            for slot_name, s in zip(slot_names, scored_items):
                rg_id = getattr(getattr(s, "n", None), "mb_release_group_id", "") or ""
                cover_result = cover_adapter.fetch_cover(rg_id) if rg_id else None
                item = _pick_to_issue_item(tag=slot_payload.get("theme") or decade_theme, slot=slot_name, s=s, cover_version=cover_version, cover_result=cover_result)
                item["style_key"] = slot_payload.get("theme_key")
                item["theme_key"] = slot_payload.get("theme_key")
                slot_payload["picks"].append(item)
            issue["slots"].append({k: v for k, v in slot_payload.items() if k in {"slot_id", "window_label", "theme", "theme_key", "constraints", "picks"}})

        now_slot_payload = next((s for s in issue["slots"] if s.get("slot_id") == now_slot_id), issue["slots"][0])
        issue["picks"] = now_slot_payload.get("picks", [])

        errors = validate_today_constraints(issue, history_index)
        if errors:
            issue["constraints"]["min_in_decade"] = 5
            issue["warnings"].append("degrade_step_c:min_in_decade=5")
            errors = validate_today_constraints(issue, history_index)
        if errors:
            issue["constraints"]["max_unknown_year"] = 3
            issue["warnings"].append("degrade_step_c:max_unknown_year=3")
            errors = validate_today_constraints(issue, history_index)
        if errors:
            for err in errors:
                print(f"BUILD ERROR: constraint validator: {err}")
            print(f"exhaustion_report={json.dumps(exhaustion, ensure_ascii=False)}")
            return 2

        quarantine_rows: list[dict[str, Any]] = []
        if quarantine_out:
            qpath = Path(quarantine_out)
            if not qpath.is_absolute():
                qpath = repo_root / qpath
            quarantine_rows = _read_quarantine_jsonl(qpath)

        ui_dir = repo_root / "ui"
        ui_dist_dir = ui_dir / "dist"
        web_dir = repo_root / "web"
        if not ui_dir.exists():
            print("BUILD ERROR: ui/ directory is missing. Cannot build frontend.")
            return 2
        print("BUILD: ui bundle")
        npm_exe = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm_exe:
            raise SystemExit("UI build failed: npm not found. Install Node.js and ensure npm is on PATH.")
        ui_build = subprocess.run([npm_exe, "--prefix", str(ui_dir), "run", "build"], check=False, cwd=repo_root)
        if ui_build.returncode != 0:
            print("BUILD ERROR: ui build failed. See npm output above.")
            return 2
        if not ui_dist_dir.exists():
            print("BUILD ERROR: ui/dist is missing after build.")
            return 2

        out_public_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree_overwrite(web_dir, out_public_dir)
        _copy_tree_overwrite(ui_dist_dir, out_public_dir)

        from daily3albums.artifact_writer import write_daily_artifacts
        paths = write_daily_artifacts(issue=issue, out_public_dir=out_public_dir, quarantine_rows=quarantine_rows or None)

        print("BUILD OK")
        print(f"out={out_public_dir}")
        for k, v in paths.items():
            print(f"{k}={v}")
        return 0
    finally:
        broker.close()


# ----------------------------
# CLI entry
# ----------------------------

def main() -> None:
    p = argparse.ArgumentParser(prog="daily3albums")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Check local env/config")

    p_lastfm = sub.add_parser("probe-lastfm", help="Probe Last.fm API (and cache)")
    p_lastfm.add_argument("--tag", required=True)
    p_lastfm.add_argument("--limit", type=int, default=5)
    p_lastfm.add_argument("--verbose", action="store_true")
    p_lastfm.add_argument("--raw", action="store_true")

    p_mb = sub.add_parser("probe-mb", help="Probe MusicBrainz API (and cache)")
    p_mb.add_argument("--artist", required=True)
    p_mb.add_argument("--title", required=True)
    p_mb.add_argument("--limit", type=int, default=5)
    p_mb.add_argument("--verbose", action="store_true")

    p_dry = sub.add_parser("dry-run", help="Dry run: lastfm candidates -> mb normalize -> score -> topN")
    p_dry.add_argument("--tag", required=True)
    p_dry.add_argument("--n", type=int, default=30)
    p_dry.add_argument("--topk", type=int, default=10)
    p_dry.add_argument("--split-slots", action="store_true")
    p_dry.add_argument("--verbose", action="store_true")
    p_dry.add_argument("--mb-search-limit", type=int, default=10)
    p_dry.add_argument("--min-confidence", type=float, default=0.80)
    p_dry.add_argument(
        "--ambiguity-gap",
        type=float,
        default=0.06,
        help="If best and runner-up confidences are too close (< gap), treat as ambiguous and reject.",
    )
    p_dry.add_argument("--mb-debug", action="store_true", help="Print MB matching attempts for each candidate")
    p_dry.add_argument(
        "--quarantine-out",
        type=str,
        default="",
        help="Write rejected/none candidates as JSONL (one JSON per line), e.g. .state/quarantine.jsonl",
    )

    # build
    p_build = sub.add_parser("build", help="Build static artifacts: run pipeline -> write JSON -> copy web/")
    p_build.add_argument("--tag", default="auto")
    p_build.add_argument("--n", type=int, default=30)
    p_build.add_argument("--topk", type=int, default=10)
    p_build.add_argument("--verbose", action="store_true")
    p_build.add_argument("--mb-search-limit", type=int, default=10)
    p_build.add_argument("--min-confidence", type=float, default=0.80)
    p_build.add_argument(
        "--ambiguity-gap",
        type=float,
        default=0.06,
        help="If best and runner-up confidences are too close (< gap), treat as ambiguous and reject.",
    )
    p_build.add_argument("--mb-debug", action="store_true", help="Print MB matching attempts for each candidate")
    p_build.add_argument(
        "--quarantine-out",
        type=str,
        default=".state/quarantine.jsonl",
        help="Write rejected/none candidates as JSONL (one JSON per line). build will also read it back.",
    )
    p_build.add_argument(
        "--out",
        type=str,
        default="_build/public",
        help="Output public directory (will contain web/ + data/). Default: _build/public",
    )
    p_build.add_argument(
        "--date",
        type=str,
        default="",
        help="Override date key (YYYY-MM-DD). If empty, use configured timezone 'today'.",
    )
    p_build.add_argument(
        "--theme",
        type=str,
        default="",
        help="Theme of the day. If empty, use tag.",
    )
    p_build.add_argument(
        "--no-split-slots",
        dest="split_slots",
        action="store_false",
        help="Disable slot split; use top3 instead",
    )
    p_build.set_defaults(split_slots=True)

    args = p.parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.cmd == "doctor":
        raise SystemExit(cmd_doctor(repo_root))
    if args.cmd == "probe-lastfm":
        raise SystemExit(cmd_probe_lastfm(repo_root, tag=args.tag, limit=args.limit, verbose=args.verbose, raw=args.raw))
    if args.cmd == "probe-mb":
        raise SystemExit(cmd_probe_mb(repo_root, artist=args.artist, title=args.title, limit=args.limit, verbose=args.verbose))
    if args.cmd == "dry-run":
        raise SystemExit(
            cmd_dry_run(
                repo_root,
                tag=args.tag,
                n=args.n,
                topk=args.topk,
                verbose=args.verbose,
                split_slots=args.split_slots,
                mb_search_limit=args.mb_search_limit,
                min_confidence=args.min_confidence,
                ambiguity_gap=args.ambiguity_gap,
                mb_debug=args.mb_debug,
                quarantine_out=args.quarantine_out,
            )
        )
    if args.cmd == "build":
        raise SystemExit(
            cmd_build(
                repo_root,
                tag=args.tag,
                n=args.n,
                topk=args.topk,
                verbose=args.verbose,
                split_slots=args.split_slots,
                mb_search_limit=args.mb_search_limit,
                min_confidence=args.min_confidence,
                ambiguity_gap=args.ambiguity_gap,
                mb_debug=args.mb_debug,
                quarantine_out=args.quarantine_out,
                out_dir=args.out,
                date_override=args.date,
                theme=args.theme,
            )
        )

    raise SystemExit(2)


if __name__ == "__main__":
    main()
