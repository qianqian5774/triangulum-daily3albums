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
from urllib.parse import urlparse

from daily3albums.config import load_env, load_config
from daily3albums.request_broker import BrokerRequestError, RequestBroker, RequestFailed
from daily3albums.adapters import (
    CoverArtArchiveAdapter,
    CoverArtResult,
    ProviderApiError,
    lastfm_tag_top_albums,
    musicbrainz_get_release_group_details,
    musicbrainz_search_release_group,
)
from daily3albums.constraints import (
    CooldownPolicy,
    HistoryIndex,
    HistoryLoadError,
    album_key_from_parts,
    artist_keys_from_parts,
    load_history_index,
    style_key_from_parts,
    theme_key_from_tag,
    validate_today_constraints,
    within_cooldown,
)
from daily3albums.dry_run import run_dry_run


# ----------------------------
# probes / dry-run
# ----------------------------


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
    diagnostics: bool,
) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    mb_search_limit = int(mb_search_limit)
    min_confidence = float(min_confidence)
    ambiguity_gap = float(ambiguity_gap)
    quarantine_out = (quarantine_out or "").strip() or None
    prefilter_topn = int(getattr(cfg, "coarse_top_n_per_slot", 120))
    candidate_cfg = (cfg.raw.get("candidates", {}) or {}).get("lastfm", {})
    build_cfg = cfg.raw.get("build", {}) or {}
    mb_max_queries_per_candidate = int(getattr(cfg, "mb_max_queries_per_candidate", 3))
    mb_max_candidates_per_slot = int(getattr(cfg, "mb_max_candidates_per_slot", 120))
    mb_time_budget_s_per_slot = float(getattr(cfg, "mb_time_budget_s_per_slot", 90.0))
    normalizer_cfg = cfg.raw.get("normalizer", {}) or {}
    config_reference_min_confidence = float(normalizer_cfg.get("min_confidence", 0.72))
    config_reference_ambiguity_gap = float(normalizer_cfg.get("ambiguity_gap", 0.08))
    lastfm_page_start = int(getattr(cfg, "lastfm_page_start", candidate_cfg.get("lastfm_page_start", candidate_cfg.get("page_start", 1))))
    lastfm_max_pages = int(getattr(cfg, "lastfm_max_pages", candidate_cfg.get("lastfm_max_pages", build_cfg.get("lastfm_max_pages", 6))))
    discogs_enabled = bool(getattr(cfg, "discogs_enabled", True))
    discogs_page_start = int(getattr(cfg, "discogs_page_start", 1))
    discogs_max_pages = int(getattr(cfg, "discogs_max_pages", 3))
    discogs_per_page = int(getattr(cfg, "discogs_per_page", 100))

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
            config_reference_min_confidence=config_reference_min_confidence,
            config_reference_ambiguity_gap=config_reference_ambiguity_gap,
            mb_debug=mb_debug,
            quarantine_out=quarantine_out,
            prefilter_topn=prefilter_topn,
            lastfm_page_start=lastfm_page_start,
            lastfm_max_pages=lastfm_max_pages,
            mb_max_queries_per_candidate=mb_max_queries_per_candidate,
            mb_max_candidates_per_slot=mb_max_candidates_per_slot,
            mb_time_budget_s_per_slot=mb_time_budget_s_per_slot,
            discogs_enabled=discogs_enabled,
            discogs_page_start=discogs_page_start,
            discogs_max_pages=discogs_max_pages,
            discogs_per_page=discogs_per_page,
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

        if diagnostics:
            print("\n== MB Diagnostics ==")
            print(json.dumps({
                "mb_candidates_considered": out.get("mb_candidates_considered", 0),
                "mb_candidates_normalized": out.get("mb_candidates_normalized", 0),
                "mb_queries_attempted_total": out.get("mb_queries_attempted_total", 0),
                "mb_search_queries_attempted_total": out.get("mb_search_queries_attempted_total", 0),
                "mb_http_calls_total": out.get("mb_http_calls_total", 0),
                "mb_budget_exceeded": out.get("mb_budget_exceeded", False),
                "mb_cap_hit": out.get("mb_cap_hit", False),
                "mb_time_spent_s": out.get("mb_time_spent_s", 0),
                "discogs_enabled": out.get("discogs_enabled", False),
                "discogs_pages_fetched": out.get("discogs_pages_fetched", 0),
                "discogs_page_cap_hit": out.get("discogs_page_cap_hit", False),
                "discogs_failed_status": out.get("discogs_failed_status"),
                "discogs_cached_negative_used": out.get("discogs_cached_negative_used", False),
            }, ensure_ascii=False, indent=2))

        if quarantine_out:
            print("\n== Quarantine ==")
            print(f"written_to={quarantine_out}")

        return 0
    except KeyboardInterrupt:
        _print_interrupt_diagnostics(broker=broker, diagnostics_summary=None)
        return 130
    finally:
        broker.close()


# ----------------------------
# helpers (build)
# ----------------------------

MAX_TAG_TRIES_PER_SLOT = 8
ARCHIVE_FORCE_REWRITE_TOKEN = "I_UNDERSTAND_THIS_REWRITES_PUBLISHED_ARCHIVE"

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


def _beijing_now() -> datetime:
    # Product time is intentionally fixed to Beijing Time. Workflow TZ keeps
    # CI/Pages aligned; config.yaml does not switch product timezone behavior.
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        return datetime.now()


def _beijing_slot(dt: datetime) -> int:
    minute_of_day = dt.hour * 60 + dt.minute
    if minute_of_day < 12 * 60 + 30:
        return 0
    if minute_of_day < 16 * 60:
        return 1
    return 2


def _slot_label(slot_id: int) -> str:
    if slot_id == 0:
        return "08:00-12:29"
    if slot_id == 1:
        return "12:30-15:59"
    return "16:00-23:59"


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


def _force_archive_rewrite_from_env() -> bool:
    raw = os.getenv("DAILY3ALBUMS_FORCE_ARCHIVE_REWRITE", "").strip()
    if not raw:
        return False
    if raw != ARCHIVE_FORCE_REWRITE_TOKEN:
        raise ValueError(
            "DAILY3ALBUMS_FORCE_ARCHIVE_REWRITE must exactly equal "
            f"{ARCHIVE_FORCE_REWRITE_TOKEN!r}"
        )
    return True


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


def _resolve_history_source(repo_root: Path, out_public_dir: Path) -> tuple[Path | None, str]:
    raw_seed = os.getenv("DAILY3ALBUMS_HISTORY_SEED_DIR", "").strip()
    if raw_seed:
        seed_dir = Path(raw_seed)
        if not seed_dir.is_absolute():
            seed_dir = repo_root / seed_dir
        return seed_dir.resolve(), "external_seed"
    local_data = out_public_dir / "data"
    if local_data.exists():
        return local_data, "local_output"
    return None, "empty"


def _history_context_payload(history: HistoryIndex) -> dict[str, Any]:
    return {
        "source": history.source,
        "dates_loaded": list(history.dates),
        "archive_count": history.archive_count,
        "picks_loaded": history.picks_loaded,
        "album_identity_counts": history.album_identity_counts(),
    }


def _candidate_identity(item: Any) -> tuple[str, set[str]]:
    nobj = getattr(item, "n", None)
    cobj = getattr(item, "c", None)
    rg_id = getattr(nobj, "mb_release_group_id", "") if nobj else ""
    title = getattr(cobj, "title", "") if cobj else ""
    artist = getattr(cobj, "artist", "") if cobj else ""
    year = _safe_year(getattr(nobj, "first_release_date", None) if nobj else None)
    artist_mbids = list(getattr(nobj, "artist_mbids", []) or []) if nobj else []
    return album_key_from_parts(rg_id, title, artist, year), set(
        artist_keys_from_parts(artist_mbids, artist)
    )


def _filter_candidate_pool(
    candidates: list[Any],
    *,
    date_key: str,
    history: HistoryIndex,
    policy: CooldownPolicy,
    album_days: int,
    artist_days: int,
    type_flags: dict[str, bool],
    used_album_keys: set[str],
    used_artist_keys: set[str],
) -> tuple[list[Any], dict[str, int]]:
    eligible: list[Any] = []
    rejected = {
        "va": 0,
        "type": 0,
        "album_collision": 0,
        "artist_same_day": 0,
        "album_cooldown": 0,
        "album_cooldown_rg_mbid": 0,
        "album_cooldown_fallback": 0,
        "artist_cooldown": 0,
    }
    for candidate in candidates:
        nobj = getattr(candidate, "n", None)
        cobj = getattr(candidate, "c", None)
        artist = getattr(cobj, "artist", "") if cobj else ""
        ptype = getattr(nobj, "primary_type", None) if nobj else None
        album_key, artist_keys = _candidate_identity(candidate)
        if _is_various_artists_name(artist):
            rejected["va"] += 1
            continue
        if not _primary_type_allowed(ptype, type_flags):
            rejected["type"] += 1
            continue
        if album_key in used_album_keys:
            rejected["album_collision"] += 1
            continue
        if artist_keys.intersection(used_artist_keys):
            rejected["artist_same_day"] += 1
            continue
        if within_cooldown(date_key, history.album_last_seen.get(album_key), album_days):
            rejected["album_cooldown"] += 1
            identity_kind = history.album_identity_kind.get(album_key, "rg_mbid")
            if identity_kind == "fallback":
                rejected["album_cooldown_fallback"] += 1
            else:
                rejected["album_cooldown_rg_mbid"] += 1
            continue
        if any(
            within_cooldown(date_key, history.artist_last_seen.get(key), artist_days)
            for key in artist_keys
        ):
            rejected["artist_cooldown"] += 1
            continue
        eligible.append(candidate)
    return eligible, rejected


def _merge_scored_candidates(primary: list[Any], additional: list[Any]) -> list[Any]:
    merged: dict[str, Any] = {}
    order: list[str] = []
    for item in [*primary, *additional]:
        album_key, _artist_keys = _candidate_identity(item)
        if not album_key:
            continue
        previous = merged.get(album_key)
        if previous is None:
            merged[album_key] = item
            order.append(album_key)
        elif float(getattr(item, "score", 0.0)) > float(getattr(previous, "score", 0.0)):
            merged[album_key] = item
    return [merged[key] for key in order]


def _request_count(snapshot: dict[str, dict[str, int]]) -> int:
    return sum(int(bucket.get("requests", 0)) for bucket in snapshot.values())


def _attempt_meta_from_out(
    *,
    tag: str,
    theme_key: str,
    out: dict[str, Any],
    eligible: list[Any],
    reject_counts: dict[str, int],
    fallback_stage: int,
    candidate_scope: str,
) -> dict[str, Any]:
    prefetched = int(out.get("prefilter_total", len(out.get("candidates") or [])))
    topn = int(out.get("prefilter_topn", len(out.get("scored") or [])))
    return {
        "tag": tag,
        "theme_key": theme_key,
        "fallback_stage": fallback_stage,
        "candidate_scope": candidate_scope,
        "fetch_limit": int(out.get("requested_candidate_count", 0) or 0),
        "lastfm_pages_fetched": int(out.get("lastfm_pages_fetched", 0)),
        "lastfm_pages_planned": int(out.get("lastfm_pages_planned", 0)),
        "candidate_count": prefetched,
        "candidate_count_after_light_prefilter": topn,
        "candidate_count_after_hard_filters": len(eligible),
        "reject_counts": dict(reject_counts),
        "eligible": len(eligible),
        "mb_candidates_considered": int(out.get("mb_candidates_considered", 0)),
        "mb_candidates_normalized": int(out.get("mb_candidates_normalized", 0)),
        "raw_candidate_count": int(out.get("raw_candidate_count", prefetched)),
        "merged_candidate_count": int(out.get("merged_candidate_count", prefetched)),
        "normalization_success_count": int(out.get("normalization_success_count", 0)),
        "normalization_failed_count": int(out.get("normalization_failed_count", 0)),
        "source_counts": dict(out.get("source_counts") or {}),
        "mb_queries_attempted_total": int(out.get("mb_queries_attempted_total", 0)),
        "mb_search_queries_attempted_total": int(out.get("mb_search_queries_attempted_total", 0)),
        "mb_http_calls_total": int(out.get("mb_http_calls_total", 0)),
        "mb_budget_exceeded": bool(out.get("mb_budget_exceeded", False)),
        "mb_cap_hit": bool(out.get("mb_cap_hit", False)),
        "mb_time_spent_s": float(out.get("mb_time_spent_s", 0.0)),
        "discogs_enabled": bool(out.get("discogs_enabled", False)),
        "discogs_attempted": bool(out.get("discogs_attempted", False)),
        "discogs_pages_fetched": int(out.get("discogs_pages_fetched", 0)),
        "discogs_page_cap_hit": bool(out.get("discogs_page_cap_hit", False)),
        "discogs_failed_status": out.get("discogs_failed_status"),
        "discogs_cached_negative_used": bool(out.get("discogs_cached_negative_used", False)),
        "listenbrainz_attempted": bool(out.get("listenbrainz_attempted", False)),
        "listenbrainz_failed": bool(out.get("listenbrainz_failed", False)),
        "listenbrainz_candidates": int(out.get("listenbrainz_candidates", 0)),
    }


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


def _single_line(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _provider_from_external_error(exc: BaseException) -> str:
    if isinstance(exc, ProviderApiError):
        return exc.provider

    adapter = str(getattr(exc, "adapter_name", "") or "")
    text = str(exc)
    url = str(getattr(exc, "url", "") or "")
    haystack = f"{adapter} {text} {url}"
    if "LastFmAdapter" in haystack or "ws.audioscrobbler.com" in haystack or "LASTFM_API_KEY" in haystack:
        return "Last.fm"
    if "MusicBrainzAdapter" in haystack or "musicbrainz.org" in haystack or "MB_USER_AGENT" in haystack:
        return "MusicBrainz"
    return "external_api"


def _stage_from_external_error(exc: BaseException, provider: str, default_stage: str) -> str:
    if isinstance(exc, ProviderApiError):
        return exc.stage
    text = str(exc)
    if "Bad JSON" in text:
        return "parse_json"
    if "LASTFM_API_KEY" in text or "MB_USER_AGENT" in text:
        return "config_check"
    if provider == "Last.fm":
        return "lastfm_top_albums"
    if provider == "MusicBrainz":
        return "musicbrainz_normalize"
    return default_stage


def _is_known_external_failure(exc: BaseException) -> bool:
    if isinstance(exc, (ProviderApiError, BrokerRequestError, RequestFailed)):
        return True
    if not isinstance(exc, RuntimeError):
        return False
    text = str(exc)
    return (
        "Bad JSON from " in text
        or "LASTFM_API_KEY" in text
        or "MB_USER_AGENT" in text
        or "Last.fm error=" in text
    )


def _advice_for_external_failure(provider: str, stage: str) -> str:
    if stage == "config_check":
        return "Check required secrets/env values in GitHub Actions or local .env, then rerun."
    if stage == "parse_json":
        return "Inspect provider response/cache for invalid JSON; retry after provider recovers or clear stale cache."
    if provider == "Last.fm":
        return "Check LASTFM_API_KEY, tag spelling, Last.fm quota/rate limits, and retry later."
    if provider == "MusicBrainz":
        return "Check MB_USER_AGENT, MusicBrainz availability/rate limits, cache health, and retry later."
    return "Inspect provider availability, credentials, rate limits, and retry with --verbose."


def _format_external_api_failure(
    *,
    slot_id: int,
    tag: str,
    stage: str,
    exc: BaseException,
    fetch_limit: int | None = None,
) -> str:
    provider = _provider_from_external_error(exc)
    resolved_stage = _stage_from_external_error(exc, provider, stage)
    parts = [
        "BUILD ERROR: external_api_failed",
        f"provider={provider}",
        f"slot={slot_id}",
        f"tag={json.dumps(tag, ensure_ascii=False)}",
        f"stage={resolved_stage}",
    ]
    if fetch_limit is not None:
        parts.append(f"fetch_limit={fetch_limit}")
    parts.append(f"error={_single_line(exc)}")
    parts.append(f"advice={_advice_for_external_failure(provider, resolved_stage)}")
    return " ".join(parts)


def _format_slot_exhaustion_failure(diag: dict[str, Any]) -> str:
    slot_id = diag.get("slot_id", "unknown")
    attempts = [a for a in diag.get("tag_attempts", []) if isinstance(a, dict)]
    tags = [str(a.get("tag")) for a in attempts if a.get("tag")]
    unique_tags = list(dict.fromkeys(tags))
    last_error = next(
        (str(a.get("error")) for a in reversed(attempts) if a.get("error")),
        "not enough eligible candidates after filters",
    )
    top_rejections = diag.get("top_rejection_reasons") or []
    return (
        "BUILD ERROR: candidate_pool_exhausted "
        f"provider=candidate_pool slot={slot_id} tag_attempts={json.dumps(unique_tags, ensure_ascii=False)} "
        f"stage=slot_selection error={_single_line(last_error)} "
        f"rejections={json.dumps(top_rejections, ensure_ascii=False)} "
        "advice=Inspect provider failures and rejection counts; broaden tags/candidate limits only if content policy allows."
    )


def _copy_tree_overwrite(src: Path, dst: Path, skip_top_level_dirs: set[str] | None = None) -> None:
    if not src.exists():
        return
    skip_top_level_dirs = skip_top_level_dirs or set()
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        if rel == Path(".") and skip_top_level_dirs:
            dirs[:] = [d for d in dirs if d not in skip_top_level_dirs]
        out_dir = dst / rel
        out_dir.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (out_dir / d).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = Path(root) / f
            t = out_dir / f
            shutil.copy2(s, t)


def _reset_generated_data_dir(out_public_dir: Path) -> None:
    data_dir = out_public_dir / "data"
    if not data_dir.exists():
        return
    if data_dir.is_dir():
        shutil.rmtree(data_dir)
    else:
        data_dir.unlink()


def _restore_history_seed(out_public_dir: Path, repo_root: Path, log_line: callable) -> None:
    raw_seed = os.getenv("DAILY3ALBUMS_HISTORY_SEED_DIR", "").strip()
    if not raw_seed:
        return

    seed_dir = Path(raw_seed)
    if not seed_dir.is_absolute():
        seed_dir = repo_root / seed_dir
    if not seed_dir.exists() or not seed_dir.is_dir():
        log_line(f"history_seed status=missing path={seed_dir}")
        return

    data_dir = out_public_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    restored: list[str] = []
    seed_index = seed_dir / "index.json"
    if seed_index.exists():
        shutil.copy2(seed_index, data_dir / "index.json")
        restored.append("index.json")

    seed_archive = seed_dir / "archive"
    if seed_archive.exists() and seed_archive.is_dir():
        _copy_tree_overwrite(seed_archive, data_dir / "archive")
        restored.append("archive/")

    restored_label = ",".join(restored) or "none"
    log_line(f"history_seed status=restored path={seed_dir} artifacts={restored_label}")


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


WIKIPEDIA_CC_BY_SA_URL = "https://creativecommons.org/licenses/by-sa/3.0/"


def _wikipedia_overview_from_url(
    broker: RequestBroker,
    wiki_url: str | None,
    user_agent: str,
    log_line: callable,
) -> dict[str, Any] | None:
    wiki_url = (wiki_url or "").strip()
    if not wiki_url:
        return None
    parsed = urlparse(wiki_url)
    host = parsed.netloc.lower()
    if "wikipedia.org" not in host or "/wiki/" not in parsed.path:
        return None
    title_path = parsed.path.split("/wiki/", 1)[1].strip("/")
    if not title_path:
        return None

    api_url = f"https://{host}/api/rest_v1/page/summary/{title_path}"
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    try:
        payload = broker.get_json(api_url, headers=headers, adapter_name="WikipediaAdapter")
    except Exception as exc:
        log_line(f"wikipedia_overview status=miss url={wiki_url} error={type(exc).__name__}")
        return None
    if not isinstance(payload, dict):
        return None

    extract = str(payload.get("extract") or "").strip()
    if not extract:
        return None
    content_urls = payload.get("content_urls")
    source_url = wiki_url
    if isinstance(content_urls, dict):
        desktop = content_urls.get("desktop")
        if isinstance(desktop, dict) and isinstance(desktop.get("page"), str):
            source_url = desktop["page"]

    return {
        "text": extract,
        "source": "wikipedia",
        "source_url": source_url,
        "license_url": WIKIPEDIA_CC_BY_SA_URL,
    }


def _pick_to_issue_item(
    tag: str,
    slot: str,
    s: Any,
    cover_version: str | None = None,
    cover_result: CoverArtResult | None = None,
    mb_details: Any | None = None,
    wikipedia_overview: dict[str, Any] | None = None,
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
    mb_tags = list(getattr(mb_details, "tags", []) or []) if mb_details else []
    merged_tags: list[dict[str, Any]] = [{"name": tag, "source": "lastfm"}]
    seen_tags = {tag.lower().strip()}
    for mb_tag in mb_tags:
        if not isinstance(mb_tag, dict):
            continue
        name = str(mb_tag.get("name") or "").strip()
        if not name or name.lower() in seen_tags:
            continue
        seen_tags.add(name.lower())
        merged_tags.append(mb_tag)

    mb_rating = None
    rating_value = getattr(mb_details, "rating_value", None) if mb_details else None
    if rating_value is not None:
        mb_rating = {
            "value": float(rating_value),
            "votes_count": getattr(mb_details, "rating_votes_count", None),
        }
    wikipedia_url = getattr(mb_details, "wikipedia_url", None) if mb_details else None

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
        "tags": merged_tags,
        "musicbrainz": {
            "rating": mb_rating,
            "tags": mb_tags,
            "wikipedia_url": wikipedia_url,
            "overview": wikipedia_overview,
        },
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
  <title>Triangulum Daily</title>
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
    <h1 style="margin:0;">Triangulum Daily</h1>
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


def _top_rejection_reasons(reject_counts: dict[str, int], limit: int = 3) -> list[dict[str, int | str]]:
    ordered = sorted(reject_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"reason": k, "count": int(v)} for k, v in ordered[:limit] if int(v) > 0]


def _slot_window_start(slot_id: int) -> str:
    if slot_id == 0:
        return "08:00"
    if slot_id == 1:
        return "12:30"
    return "16:00"


def _empty_source_counts() -> dict[str, int]:
    return {"lastfm": 0, "discogs": 0, "listenbrainz": 0, "multi_source": 0}


def _sources_for_scored(s: Any) -> list[str]:
    c = getattr(s, "c", None)
    raw_sources = getattr(c, "sources", None) if c is not None else None
    if not raw_sources:
        return ["unknown"]
    sources = sorted({str(source).lower() for source in raw_sources if str(source).strip()})
    return sources or ["unknown"]


def _source_counts_for_scored(items: list[Any]) -> dict[str, int]:
    counts = {**_empty_source_counts(), "unknown": 0}
    for item in items:
        sources = set(_sources_for_scored(item))
        for key in ("lastfm", "discogs", "listenbrainz"):
            if key in sources:
                counts[key] += 1
        if "unknown" in sources:
            counts["unknown"] += 1
        if len(sources - {"unknown"}) > 1:
            counts["multi_source"] += 1
    return counts


def _selected_attempt_meta(attempts_meta: list[dict[str, Any]], picked_theme_tag: str) -> dict[str, Any]:
    for attempt in reversed(attempts_meta):
        if isinstance(attempt, dict) and attempt.get("selected") is True:
            return attempt
    for attempt in reversed(attempts_meta):
        if not isinstance(attempt, dict):
            continue
        if attempt.get("tag") == picked_theme_tag and attempt.get("fetch_limit") is not None:
            return attempt
    for attempt in reversed(attempts_meta):
        if isinstance(attempt, dict) and attempt.get("fetch_limit") is not None:
            return attempt
    return {}


def _rejection_reasons_for_observability(
    reject_counts: dict[str, int],
    selected_attempt: dict[str, Any],
) -> dict[str, int]:
    return {
        "various_artists": int(reject_counts.get("va", 0)),
        "unsupported_primary_type": int(reject_counts.get("type", 0)),
        "duplicate_album_same_day": int(reject_counts.get("album_collision", 0)),
        "duplicate_artist_same_day": int(reject_counts.get("artist_same_day", 0)),
        "album_cooldown": int(reject_counts.get("album_cooldown", 0)),
        "album_cooldown_rg_mbid": int(reject_counts.get("album_cooldown_rg_mbid", 0)),
        "album_cooldown_fallback": int(reject_counts.get("album_cooldown_fallback", 0)),
        "artist_cooldown": int(reject_counts.get("artist_cooldown", 0)),
        "theme_cooldown": int(reject_counts.get("theme_cooldown", 0)),
        "musicbrainz_normalization_failed": int(selected_attempt.get("normalization_failed_count", 0)),
        "missing_required_metadata": 0,
        "other": 0,
    }


def _normalization_shadow_slot_payload(
    *,
    candidates: list[Any],
    eligible: list[Any],
    final_picks: list[Any],
    cli_min_confidence: float,
    cli_ambiguity_gap: float,
    config_min_confidence: float,
    config_ambiguity_gap: float,
) -> dict[str, Any]:
    eligible_keys = {_candidate_identity(item)[0] for item in eligible}
    final_keys = {_candidate_identity(item)[0] for item in final_picks}
    rows: list[dict[str, Any]] = []
    for item in candidates:
        debug = getattr(item, "debug", None)
        shadow = debug.get("normalization_shadow") if isinstance(debug, dict) else None
        if not isinstance(shadow, dict):
            continue
        candidate_key, _artist_keys = _candidate_identity(item)
        nobj = getattr(item, "n", None)
        references = shadow.get("references") if isinstance(shadow.get("references"), dict) else {}
        rows.append(
            {
                "candidate_key": candidate_key,
                "release_group_mbid": getattr(nobj, "mb_release_group_id", None) if nobj else None,
                "path": shadow.get("path"),
                "query_strategy": shadow.get("query_strategy"),
                "best_confidence": shadow.get("best_confidence"),
                "second_best_confidence": shadow.get("second_best_confidence"),
                "has_second_best": bool(shadow.get("has_second_best", False)),
                "ambiguity_gap": shadow.get("ambiguity_gap"),
                "in_normalized_pool": True,
                "in_eligible_pool": candidate_key in eligible_keys,
                "in_final_picks": candidate_key in final_keys,
                "references": {
                    name: dict(value)
                    for name, value in references.items()
                    if name in {"cli_reference", "config_reference"} and isinstance(value, dict)
                },
            }
        )
    rows.sort(key=lambda row: (str(row.get("candidate_key") or ""), str(row.get("path") or "")))

    path_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    for row in rows:
        path = str(row.get("path") or "unknown")
        path_counts[path] = path_counts.get(path, 0) + 1
        strategy = row.get("query_strategy")
        if strategy is not None:
            key = str(strategy)
            strategy_counts[key] = strategy_counts.get(key, 0) + 1

    reference_specs = (
        ("cli_reference", float(cli_min_confidence), float(cli_ambiguity_gap)),
        ("config_reference", float(config_min_confidence), float(config_ambiguity_gap)),
    )
    impacts: dict[str, Any] = {}
    for name, min_confidence, gap_threshold in reference_specs:
        evaluated = 0
        not_applicable = 0
        rejected_rows: list[dict[str, Any]] = []
        low_confidence = 0
        ambiguous = 0
        for row in rows:
            result = (row.get("references") or {}).get(name)
            if not isinstance(result, dict):
                continue
            if result.get("status") == "not_applicable":
                not_applicable += 1
            else:
                evaluated += 1
            if result.get("rejected") is True:
                rejected_rows.append(row)
                if result.get("reason") == "low_confidence":
                    low_confidence += 1
                elif result.get("reason") == "ambiguous":
                    ambiguous += 1

        rejected_keys = {str(row.get("candidate_key") or "") for row in rejected_rows}
        eligible_before = sum(1 for row in rows if row.get("in_eligible_pool") is True)
        final_before = sum(1 for row in rows if row.get("in_final_picks") is True)
        eligible_impacted = sum(
            1
            for row in rows
            if row.get("in_eligible_pool") is True and str(row.get("candidate_key") or "") in rejected_keys
        )
        final_impacted = sum(
            1
            for row in rows
            if row.get("in_final_picks") is True and str(row.get("candidate_key") or "") in rejected_keys
        )
        eligible_remaining = max(0, eligible_before - eligible_impacted)
        impacts[name] = {
            "min_confidence": min_confidence,
            "ambiguity_gap": gap_threshold,
            "text_search_evaluated": evaluated,
            "not_applicable_non_text_path": not_applicable,
            "rejected_total": len(rejected_rows),
            "rejected_low_confidence": low_confidence,
            "rejected_ambiguous": ambiguous,
            "normalized_before": len(rows),
            "normalized_impacted": len(rejected_rows),
            "normalized_remaining": max(0, len(rows) - len(rejected_rows)),
            "eligible_before": eligible_before,
            "eligible_impacted": eligible_impacted,
            "eligible_remaining": eligible_remaining,
            "final_picks_before": final_before,
            "final_picks_impacted": final_impacted,
            "candidate_shortage": eligible_remaining < 3,
            "possible_higher_fallback": eligible_remaining < 3,
        }

    return {
        "status": "observed_not_enforced",
        "enforced": False,
        "candidate_count": len(rows),
        "path_counts": dict(sorted(path_counts.items())),
        "query_strategy_counts": dict(sorted(strategy_counts.items())),
        "references": impacts,
        "candidates": rows,
    }


def _slot_observability_payload(
    *,
    slot_id: int,
    tag_attempts: list[str],
    picked_theme_tag: str,
    attempts_meta: list[dict[str, Any]],
    reject_counts: dict[str, int],
    scored_items: list[Any],
    history_context: dict[str, Any],
    fallback: dict[str, Any],
    normalization_shadow: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_attempt = _selected_attempt_meta(attempts_meta, picked_theme_tag)
    attempted_tags = list(
        dict.fromkeys(
            str(attempt.get("tag"))
            for attempt in attempts_meta
            if isinstance(attempt, dict) and str(attempt.get("tag") or "").strip()
        )
    )
    if not attempted_tags:
        attempted_tags = list(dict.fromkeys([str(tag) for tag in tag_attempts if str(tag).strip()]))
    source_counts = _empty_source_counts()
    raw_source_counts = selected_attempt.get("source_counts")
    if isinstance(raw_source_counts, dict):
        for key in source_counts:
            source_counts[key] = int(raw_source_counts.get(key, 0) or 0)

    return {
        "slot_id": slot_id,
        "window": _slot_window_start(slot_id),
        "window_label": _slot_label(slot_id),
        "theme": picked_theme_tag,
        "attempted_tags": attempted_tags,
        "candidate_counts": {
            "raw": int(selected_attempt.get("raw_candidate_count", selected_attempt.get("candidate_count", 0)) or 0),
            "merged": int(selected_attempt.get("merged_candidate_count", selected_attempt.get("candidate_count", 0)) or 0),
            "normalization_attempted": int(selected_attempt.get("mb_candidates_normalized", 0) or 0),
            "normalized": int(selected_attempt.get("normalization_success_count", 0) or 0),
            "eligible": int(selected_attempt.get("eligible", 0) or 0),
            "final_picks": len(scored_items),
        },
        "source_share": source_counts,
        "final_picks_by_source": _source_counts_for_scored(scored_items),
        "rejection_reasons": _rejection_reasons_for_observability(reject_counts, selected_attempt),
        "history_context": history_context,
        "fallback": fallback,
        "stage_attempts": [
            {
                key: attempt.get(key)
                for key in (
                    "fallback_stage",
                    "tag",
                    "candidate_scope",
                    "eligible",
                    "candidate_count",
                    "reject_counts",
                    "expansion_before",
                    "expansion_after",
                    "additional_requests",
                    "stage3_relaxed_candidates",
                    "blocked",
                )
                if key in attempt
            }
            for attempt in attempts_meta
            if isinstance(attempt, dict) and "fallback_stage" in attempt
        ],
        "source_diagnostics": {
            "discogs_enabled": bool(selected_attempt.get("discogs_enabled", False)),
            "discogs_attempted": bool(selected_attempt.get("discogs_attempted", False)),
            "discogs_pages_fetched": int(selected_attempt.get("discogs_pages_fetched", 0) or 0),
            "discogs_failed_status": selected_attempt.get("discogs_failed_status"),
            "discogs_cached_negative_used": bool(selected_attempt.get("discogs_cached_negative_used", False)),
            "listenbrainz_attempted": bool(selected_attempt.get("listenbrainz_attempted", False)),
            "listenbrainz_failed": bool(selected_attempt.get("listenbrainz_failed", False)),
            "listenbrainz_candidates": int(selected_attempt.get("listenbrainz_candidates", 0) or 0),
        },
        "normalization_shadow": normalization_shadow or {
            "status": "not_available",
            "enforced": False,
            "candidate_count": 0,
            "path_counts": {},
            "query_strategy_counts": {},
            "references": {},
            "candidates": [],
        },
        "final_picks": [],
    }


def _head_commit_sha(repo_root: Path) -> str:
    env_sha = (os.getenv("GITHUB_SHA") or "").strip()
    if env_sha:
        return env_sha

    head_path = repo_root / ".git" / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    if head.startswith("ref:"):
        ref_name = head.split(":", 1)[1].strip()
        ref_path = repo_root / ".git" / ref_name
        try:
            return ref_path.read_text(encoding="utf-8").strip() or "unknown"
        except OSError:
            packed_refs = repo_root / ".git" / "packed-refs"
            try:
                for line in packed_refs.read_text(encoding="utf-8").splitlines():
                    if not line or line.startswith("#") or line.startswith("^"):
                        continue
                    sha, _, name = line.partition(" ")
                    if name.strip() == ref_name and sha.strip():
                        return sha.strip()
            except OSError:
                return "unknown"
            return "unknown"
    return head or "unknown"


def _new_recommendation_observability(
    *,
    repo_root: Path,
    issue: dict[str, Any],
    slot_payloads: list[dict[str, Any]],
    discogs_enabled: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generation_mode": "generated",
        "candidate_funnel_rerun": True,
        "reused_archive_seed": False,
        "reused_archive_date": None,
        "reused_archive_run_id": None,
        "final_picks_source": "candidate_funnel",
        "normalization_shadow": {
            "status": "observed_not_enforced",
            "enforced": False,
            "production_sample_eligible": True,
            "references": [
                {"name": "cli_reference", "source": "CLI arguments"},
                {"name": "config_reference", "source": "config.normalizer"},
            ],
        },
        "date": issue.get("date"),
        "run_id": issue.get("run_id"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "commit_sha": _head_commit_sha(repo_root),
        "slots": [
            slot["observability"]
            for slot in slot_payloads
            if isinstance(slot.get("observability"), dict)
        ],
        "final_pick_coverage": {},
        "final_pick_metadata_coverage": {},
        "enrichment": {
            "musicbrainz_normalization_attempted": 0,
            "musicbrainz_normalization_success": 0,
            "musicbrainz_detail_attempted": 0,
            "musicbrainz_detail_success": 0,
            "wikipedia_overview_attempted": 0,
            "wikipedia_overview_success": 0,
            "cover_attempted": 0,
            "cover_success": 0,
            "discogs_candidate_source_enabled": bool(discogs_enabled),
            "discogs_candidate_source_attempted": False,
            "discogs_candidate_source_failed": False,
            "listenbrainz_candidate_source_attempted": False,
            "listenbrainz_candidate_source_failed": False,
            "listenbrainz_candidate_source_ignored": 0,
        },
        "notes": [
            "Candidate counts are observability only and do not change recommendation weights.",
            "Slot candidate counts describe the selected tag fetch window; attempted_tags records the slot search space.",
            "Region/country/language are unavailable in the current public pick schema and are not inferred.",
        ],
    }


def _cover_source_for_observability(item: dict[str, Any], sources: list[str]) -> str:
    cover = item.get("cover") if isinstance(item.get("cover"), dict) else {}
    url = str(cover.get("optimized_cover_url") or "")
    original_url = str(cover.get("original_cover_url") or "")
    if cover.get("source_release_mbid") or "coverartarchive.org" in url or "coverartarchive.org" in original_url:
        return "cover_art_archive"
    if not cover.get("has_cover") or url.endswith("assets/placeholder.svg"):
        return "placeholder"
    if "discogs" in sources and "lastfm" not in sources:
        return "discogs_candidate"
    if "lastfm" in sources:
        return "lastfm_candidate"
    return "candidate_image"


def _observability_final_pick(item: dict[str, Any], scored: Any) -> dict[str, Any]:
    musicbrainz = item.get("musicbrainz") if isinstance(item.get("musicbrainz"), dict) else {}
    links = item.get("links") if isinstance(item.get("links"), dict) else {}
    cover = item.get("cover") if isinstance(item.get("cover"), dict) else {}
    sources = _sources_for_scored(scored)
    mb_tags = musicbrainz.get("tags")
    return {
        "role": item.get("slot"),
        "title": item.get("title"),
        "artist": item.get("artist_credit"),
        "year": item.get("first_release_year"),
        "sources": sources,
        "metadata": {
            "musicbrainz_rg_mbid": bool(item.get("rg_mbid")),
            "artist_mbids": bool(item.get("artist_mbids")),
            "rating": bool(musicbrainz.get("rating")),
            "tags": bool(mb_tags),
            "wikipedia_overview": bool(musicbrainz.get("overview")),
            "cover": bool(cover.get("has_cover")),
            "cover_source": _cover_source_for_observability(item, sources),
            "musicbrainz_url": bool(links.get("musicbrainz")),
            "youtube_search_url": bool(links.get("youtube_search")),
        },
    }


def _decade_label(year: int) -> str:
    start = (year // 10) * 10
    return f"{start}s"


def _finalize_recommendation_observability(payload: dict[str, Any]) -> None:
    slots = [slot for slot in payload.get("slots", []) if isinstance(slot, dict)]
    picks = [
        pick
        for slot in slots
        for pick in slot.get("final_picks", [])
        if isinstance(pick, dict)
    ]
    total = len(picks)
    decades: dict[str, int] = {}
    year_present = 0
    for pick in picks:
        year = pick.get("year")
        if isinstance(year, int):
            year_present += 1
            label = _decade_label(year)
            decades[label] = decades.get(label, 0) + 1

    payload["final_pick_coverage"] = {
        "total": total,
        "year_present": year_present,
        "year_missing": total - year_present,
        "decades": decades,
        "region_present": 0,
        "region_missing": total,
        "region_status": "unavailable_in_current_pick_schema",
        "country_present": 0,
        "country_missing": total,
        "country_status": "unavailable_in_current_pick_schema",
        "region_country_present": 0,
        "region_country_missing": total,
        "language_present": 0,
        "language_missing": total,
        "language_status": "unavailable_in_current_pick_schema",
    }

    metadata_fields = [
        "musicbrainz_rg_mbid",
        "artist_mbids",
        "rating",
        "tags",
        "wikipedia_overview",
        "cover",
        "musicbrainz_url",
        "youtube_search_url",
    ]
    metadata_coverage: dict[str, Any] = {"total": total, "cover_source_distribution": {}}
    for field in metadata_fields:
        present = sum(1 for pick in picks if bool((pick.get("metadata") or {}).get(field)))
        metadata_coverage[f"{field}_present"] = present
        metadata_coverage[f"{field}_missing"] = total - present
    for pick in picks:
        cover_source = str((pick.get("metadata") or {}).get("cover_source") or "unknown")
        distribution = metadata_coverage["cover_source_distribution"]
        distribution[cover_source] = int(distribution.get(cover_source, 0)) + 1
    payload["final_pick_metadata_coverage"] = metadata_coverage

    enrichment = payload.get("enrichment")
    if isinstance(enrichment, dict):
        enrichment["musicbrainz_normalization_attempted"] = sum(
            int((slot.get("candidate_counts") or {}).get("normalization_attempted", 0) or 0)
            for slot in slots
        )
        enrichment["musicbrainz_normalization_success"] = sum(
            int((slot.get("candidate_counts") or {}).get("normalized", 0) or 0)
            for slot in slots
        )
        enrichment["discogs_candidate_source_attempted"] = any(
            bool((slot.get("source_diagnostics") or {}).get("discogs_attempted", False))
            for slot in slots
        )
        enrichment["discogs_candidate_source_failed"] = any(
            (slot.get("source_diagnostics") or {}).get("discogs_failed_status") is not None
            for slot in slots
        )
        enrichment["listenbrainz_candidate_source_attempted"] = any(
            bool((slot.get("source_diagnostics") or {}).get("listenbrainz_attempted", False))
            for slot in slots
        )
        enrichment["listenbrainz_candidate_source_failed"] = any(
            bool((slot.get("source_diagnostics") or {}).get("listenbrainz_failed", False))
            for slot in slots
        )


def _archive_lock_final_pick(pick: dict[str, Any]) -> dict[str, Any]:
    cover = pick.get("cover") if isinstance(pick.get("cover"), dict) else {}
    return {
        "slot": pick.get("slot"),
        "title": pick.get("title"),
        "artist_credit": pick.get("artist_credit"),
        "rg_mbid": pick.get("rg_mbid"),
        "year": pick.get("first_release_year"),
        "metadata": {
            "musicbrainz_rg_mbid": pick.get("rg_mbid"),
            "artist_mbids": pick.get("artist_mbids") or [],
            "rating": pick.get("rating"),
            "tags": pick.get("tags") or [],
            "wikipedia_overview": pick.get("wikipedia_overview"),
            "cover": cover,
            "cover_source": cover.get("source") or "unknown",
            "musicbrainz_url": pick.get("musicbrainz_url"),
            "youtube_search_url": pick.get("youtube_search_url"),
        },
    }


def _archive_lock_observability(
    *,
    repo_root: Path,
    issue: dict[str, Any],
    generated_run_id: str,
) -> dict[str, Any]:
    slots_payload: list[dict[str, Any]] = []
    for slot in issue.get("slots") or []:
        if not isinstance(slot, dict):
            continue
        picks = [pick for pick in slot.get("picks") or [] if isinstance(pick, dict)]
        slots_payload.append(
            {
                "slot_id": slot.get("slot_id"),
                "window": _slot_window_start(int(slot.get("slot_id", 0) or 0)),
                "window_label": slot.get("window_label"),
                "theme": slot.get("theme"),
                "attempted_tags": [],
                "candidate_counts": {
                    "raw": 0,
                    "merged": 0,
                    "normalization_attempted": 0,
                    "normalized": 0,
                    "eligible": 0,
                    "final_picks": len(picks),
                },
                "source_share": _empty_source_counts(),
                "final_picks_by_source": _empty_source_counts(),
                "rejection_reasons": {
                    "various_artists": 0,
                    "unsupported_primary_type": 0,
                    "duplicate_album_same_day": 0,
                    "duplicate_artist_same_day": 0,
                    "album_cooldown": 0,
                    "artist_cooldown": 0,
                    "theme_cooldown": 0,
                    "musicbrainz_normalization_failed": 0,
                    "missing_required_metadata": 0,
                    "other": 0,
                },
                "source_diagnostics": {
                    "discogs_enabled": False,
                    "discogs_attempted": False,
                    "discogs_pages_fetched": 0,
                    "discogs_failed_status": None,
                    "discogs_cached_negative_used": False,
                    "listenbrainz_attempted": False,
                    "listenbrainz_failed": False,
                    "listenbrainz_candidates": 0,
                },
                "final_picks": [_archive_lock_final_pick(pick) for pick in picks],
            }
        )

    payload = {
        "schema_version": 1,
        "generation_mode": "reused_published_archive",
        "candidate_funnel_rerun": False,
        "reused_archive_seed": True,
        "reused_archive_date": issue.get("date"),
        "reused_archive_run_id": issue.get("run_id"),
        "final_picks_source": "published_archive_seed",
        "normalization_shadow": {
            "status": "not_available_reused_published_archive",
            "enforced": False,
            "production_sample_eligible": False,
            "reason": (
                "Final public observability was restored from the published archive seed; any internal candidate "
                "funnel data was discarded and is not a production shadow sample."
            ),
        },
        "date": issue.get("date"),
        "run_id": issue.get("run_id"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "commit_sha": _head_commit_sha(repo_root),
        "archive_lock": {
            "reused_published_date": True,
            "published_date": issue.get("date"),
            "published_run_id": issue.get("run_id"),
            "discarded_generated_run_id": generated_run_id,
        },
        "slots": slots_payload,
        "final_pick_coverage": {},
        "final_pick_metadata_coverage": {},
        "enrichment": {
            "musicbrainz_normalization_attempted": 0,
            "musicbrainz_normalization_success": 0,
            "musicbrainz_detail_attempted": 0,
            "musicbrainz_detail_success": 0,
            "wikipedia_overview_attempted": 0,
            "wikipedia_overview_success": 0,
            "cover_attempted": 0,
            "cover_success": 0,
            "discogs_candidate_source_attempted": False,
            "discogs_candidate_source_failed": False,
            "listenbrainz_candidate_source_attempted": False,
            "listenbrainz_candidate_source_failed": False,
        },
    }
    _finalize_recommendation_observability(payload)
    return payload


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
    diagnostics: bool,
    skip_ui_build: bool = False,
) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)
    build_logger = _get_build_logger(repo_root)
    try:
        force_archive_rewrite = _force_archive_rewrite_from_env()
    except ValueError as exc:
        print(f"BUILD ERROR: {exc}")
        return 2

    if getattr(cfg, "ignored_legacy_decade_keys", []):
        ignored_keys = ", ".join(sorted(set(cfg.ignored_legacy_decade_keys)))
        msg = f"decade_* settings ignored: decade_mode={cfg.decade_mode} ({ignored_keys})"
        print(f"BUILD WARN: {msg}")
        build_logger.warning(msg)
    if force_archive_rewrite:
        msg = (
            "archive_immutability force_rewrite=true "
            "reason=DAILY3ALBUMS_FORCE_ARCHIVE_REWRITE confirmed; "
            "published same-day archive may be replaced"
        )
        print(f"BUILD WARN: {msg}")
        build_logger.warning(msg)

    def log_line(msg: str) -> None:
        if verbose:
            print(msg)
        build_logger.info(msg)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    cover_adapter = CoverArtArchiveAdapter(broker)
    type_flags = _type_flags_from_cfg(cfg)

    mb_search_limit = int(mb_search_limit)
    prefilter_topn = int(getattr(cfg, "coarse_top_n_per_slot", 120))
    candidate_cfg = (cfg.raw.get("candidates", {}) or {}).get("lastfm", {})
    build_cfg = cfg.raw.get("build", {}) or {}
    mb_max_queries_per_candidate = int(getattr(cfg, "mb_max_queries_per_candidate", 3))
    mb_max_candidates_per_slot = int(getattr(cfg, "mb_max_candidates_per_slot", 120))
    mb_time_budget_s_per_slot = float(getattr(cfg, "mb_time_budget_s_per_slot", 90.0))
    normalizer_cfg = cfg.raw.get("normalizer", {}) or {}
    config_reference_min_confidence = float(normalizer_cfg.get("min_confidence", 0.72))
    config_reference_ambiguity_gap = float(normalizer_cfg.get("ambiguity_gap", 0.08))
    lastfm_page_start = int(getattr(cfg, "lastfm_page_start", candidate_cfg.get("lastfm_page_start", candidate_cfg.get("page_start", 1))))
    lastfm_max_pages = int(getattr(cfg, "lastfm_max_pages", candidate_cfg.get("lastfm_max_pages", build_cfg.get("lastfm_max_pages", 6))))
    discogs_enabled = bool(getattr(cfg, "discogs_enabled", True))
    discogs_page_start = int(getattr(cfg, "discogs_page_start", 1))
    discogs_max_pages = int(getattr(cfg, "discogs_max_pages", 3))
    discogs_per_page = int(getattr(cfg, "discogs_per_page", 100))
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
        generated_run_id = run_id

        cooldown_policy = CooldownPolicy(
            album_days=int(getattr(cfg, "dedupe_same_rg_days", 7)),
            artist_days=int(getattr(cfg, "dedupe_same_artist_days", 7)),
        )
        history_data_dir, history_source = _resolve_history_source(repo_root, out_public_dir)
        try:
            history_index = load_history_index(
                history_data_dir,
                current_date_key=bjt_date_key,
                max_lookback_days=max(
                    cooldown_policy.album_days,
                    cooldown_policy.artist_days,
                    cooldown_policy.theme_days,
                ),
                source=history_source,
            )
        except HistoryLoadError as exc:
            print(f"BUILD ERROR: history source invalid: {exc}")
            log_line(f"history_source status=invalid source={history_source} error={_single_line(exc)}")
            return 2
        history_context = _history_context_payload(history_index)
        log_line(
            "history_source status=loaded "
            f"source={history_index.source} archives={history_index.archive_count} "
            f"picks={history_index.picks_loaded} dates={','.join(history_index.dates) or 'none'}"
        )

        slot_names = ["Headliner", "Lineage", "DeepCut"]
        slots_payload: list[dict[str, Any]] = []
        used_album_keys: set[str] = set()
        used_artist_keys: set[str] = set()
        used_theme_keys: set[str] = set()
        slot_cooldown_windows: dict[int, tuple[int, int]] = {}
        stage3_daily_pick_count = 0
        exhaustion: list[dict[str, Any]] = []
        diagnostics_summary = {"requests": {}, "timeouts": {}, "retries": {}, "slot_rejections": {}, "slot_progress": {}}

        for slot_id in range(3):
            pool = _get_tag_pool(cfg)
            start_index = _hash_index(f"{date_key}:{slot_id}", len(pool))
            tag_attempts = [pool[(start_index + i) % len(pool)] for i in range(len(pool))]
            if used_theme_keys:
                tag_attempts = sorted(tag_attempts, key=lambda t: (theme_key_from_tag(t) in used_theme_keys, tag_attempts.index(t)))
            max_tag_tries = int(getattr(cfg, "max_tag_tries_per_slot", (cfg.raw.get("build", {}) or {}).get("max_tag_tries_per_slot", MAX_TAG_TRIES_PER_SLOT)))
            tag_attempts = tag_attempts[:max_tag_tries]

            picked: list[Any] = []
            picked_theme_tag = ""
            picked_theme_key = ""
            selected_candidates: list[Any] = []
            selected_eligible: list[Any] = []
            fallback_stage = 0
            candidate_scope_expanded = False
            expansion_before = 0
            expansion_after = 0
            additional_requests = 0
            stage3_pick_info: dict[str, Any] | None = None
            reject_counts = {
                "va": 0,
                "type": 0,
                "album_cooldown": 0,
                "album_cooldown_rg_mbid": 0,
                "album_cooldown_fallback": 0,
                "artist_cooldown": 0,
                "artist_same_day": 0,
                "album_collision": 0,
                "theme_cooldown": 0,
            }
            fetched_count = 0
            attempts_meta: list[dict[str, Any]] = []
            tag_records: list[dict[str, Any]] = []
            slot_temperature = 9.0 if slot_id == 0 else (10.0 if slot_id == 1 else 14.0)

            def sample_three(items: list[Any], theme_key: str, *, seed_suffix: str = "") -> list[Any]:
                seed = f"{date_key}:{slot_id}:{theme_key}{seed_suffix}"
                sampled, _ = _weighted_sample_unique_artists(
                    items,
                    count=3,
                    rng=random.Random(seed),
                    recent_ids=set(),
                    cooling_penalty=None,
                    log_line=log_line,
                    temperature=slot_temperature,
                )
                return sampled

            for slot_tag in tag_attempts:
                theme_key = theme_key_from_tag(slot_tag)
                last_theme_day = history_index.style_last_seen.get(theme_key)
                if theme_key in used_theme_keys or within_cooldown(
                    bjt_date_key,
                    last_theme_day,
                    cooldown_policy.theme_days,
                ):
                    reject_counts["theme_cooldown"] += 1
                    attempts_meta.append(
                        {
                            "tag": slot_tag,
                            "theme_key": theme_key,
                            "fallback_stage": 0,
                            "skipped": "theme_cooldown",
                            "last_seen": last_theme_day,
                        }
                    )
                    continue

                fetch_limit = max(n, 200)
                deepcut = slot_id == 2
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
                        config_reference_min_confidence=config_reference_min_confidence,
                        config_reference_ambiguity_gap=config_reference_ambiguity_gap,
                        mb_debug=mb_debug,
                        quarantine_out=None,
                        prefilter_topn=prefilter_topn,
                        lastfm_page_start=lastfm_page_start,
                        lastfm_max_pages=lastfm_max_pages,
                        mb_max_queries_per_candidate=mb_max_queries_per_candidate,
                        mb_max_candidates_per_slot=mb_max_candidates_per_slot,
                        mb_time_budget_s_per_slot=mb_time_budget_s_per_slot,
                        discogs_enabled=discogs_enabled,
                        discogs_page_start=discogs_page_start,
                        discogs_max_pages=discogs_max_pages,
                        discogs_per_page=discogs_per_page,
                    )
                except (ProviderApiError, BrokerRequestError, RequestFailed, RuntimeError) as exc:
                    if not _is_known_external_failure(exc):
                        raise
                    error_message = _format_external_api_failure(
                        slot_id=slot_id,
                        tag=slot_tag,
                        stage="candidate_fetch",
                        exc=exc,
                        fetch_limit=fetch_limit,
                    )
                    attempts_meta.append(
                        {
                            "tag": slot_tag,
                            "theme_key": theme_key,
                            "fallback_stage": 0,
                            "candidate_scope": "strict",
                            "network_failed": True,
                            "provider": _provider_from_external_error(exc),
                            "stage": _stage_from_external_error(
                                exc,
                                _provider_from_external_error(exc),
                                "candidate_fetch",
                            ),
                            "error": error_message,
                            "candidate_count": 0,
                            "candidate_count_after_light_prefilter": 0,
                            "candidate_count_after_hard_filters": 0,
                        }
                    )
                    print(error_message)
                    log_line(error_message)
                    continue

                candidates = [item for item in (out.get("top") or []) if getattr(item, "n", None) is not None]
                fetched_count = max(fetched_count, len(candidates))
                eligible, local_reject = _filter_candidate_pool(
                    candidates,
                    date_key=date_key,
                    history=history_index,
                    policy=cooldown_policy,
                    album_days=cooldown_policy.album_days,
                    artist_days=cooldown_policy.artist_days,
                    type_flags=type_flags,
                    used_album_keys=used_album_keys,
                    used_artist_keys=used_artist_keys,
                )
                for key, value in local_reject.items():
                    reject_counts[key] += value
                attempt_meta = _attempt_meta_from_out(
                    tag=slot_tag,
                    theme_key=theme_key,
                    out=out,
                    eligible=eligible,
                    reject_counts=local_reject,
                    fallback_stage=0,
                    candidate_scope="strict",
                )
                attempts_meta.append(attempt_meta)
                tag_records.append(
                    {
                        "tag": slot_tag,
                        "theme_key": theme_key,
                        "out": out,
                        "candidates": candidates,
                        "strict_eligible": eligible,
                        "attempt_meta": attempt_meta,
                    }
                )
                if len(eligible) >= 3:
                    sampled = sample_three(eligible, theme_key)
                    if len(sampled) >= 3:
                        picked = sampled
                        picked_theme_tag = slot_tag
                        picked_theme_key = theme_key
                        selected_candidates = candidates
                        selected_eligible = eligible
                        attempt_meta["selected"] = True
                        break

            if len(picked) < 3 and tag_records:
                candidate_scope_expanded = True
                expansion_record = max(
                    enumerate(tag_records),
                    key=lambda item: (len(item[1]["strict_eligible"]), -item[0]),
                )[1]
                expansion_before = len(expansion_record["candidates"])
                requests_before = _request_count(broker.get_stats_snapshot())
                expansion_page = lastfm_page_start + lastfm_max_pages
                try:
                    expanded_out = run_dry_run(
                        broker,
                        env,
                        tag=expansion_record["tag"],
                        n=max(n, 200),
                        topk=max(max(n, 200), topk),
                        deepcut=slot_id == 2,
                        seed_key=f"{date_key}:{slot_id}:{expansion_record['tag']}:stage1",
                        split_slots=False,
                        mb_search_limit=mb_search_limit,
                        min_confidence=float(min_confidence),
                        ambiguity_gap=float(ambiguity_gap),
                        config_reference_min_confidence=config_reference_min_confidence,
                        config_reference_ambiguity_gap=config_reference_ambiguity_gap,
                        mb_debug=mb_debug,
                        quarantine_out=None,
                        prefilter_topn=prefilter_topn,
                        lastfm_page_start=expansion_page,
                        lastfm_max_pages=1,
                        mb_max_queries_per_candidate=mb_max_queries_per_candidate,
                        mb_max_candidates_per_slot=mb_max_candidates_per_slot,
                        mb_time_budget_s_per_slot=mb_time_budget_s_per_slot,
                        discogs_enabled=False,
                        discogs_page_start=discogs_page_start,
                        discogs_max_pages=discogs_max_pages,
                        discogs_per_page=discogs_per_page,
                        lastfm_only=True,
                    )
                    additional_requests = max(
                        0,
                        _request_count(broker.get_stats_snapshot()) - requests_before,
                    )
                    expanded_candidates = [
                        item for item in (expanded_out.get("top") or []) if getattr(item, "n", None) is not None
                    ]
                    combined = _merge_scored_candidates(expansion_record["candidates"], expanded_candidates)
                    expansion_after = len(combined)
                    expansion_record["candidates"] = combined
                    combined_out = dict(expansion_record["out"])
                    combined_out.update(
                        {
                            "requested_candidate_count": max(n, 200),
                            "raw_candidate_count": int(expansion_record["out"].get("raw_candidate_count", 0))
                            + int(expanded_out.get("raw_candidate_count", 0)),
                            "merged_candidate_count": len(combined),
                            "prefilter_total": len(combined),
                            "prefilter_topn": len(combined),
                            "normalization_success_count": len(combined),
                            "mb_candidates_normalized": int(
                                expansion_record["out"].get("mb_candidates_normalized", 0)
                            )
                            + int(expanded_out.get("mb_candidates_normalized", 0)),
                            "lastfm_pages_fetched": int(
                                expansion_record["out"].get("lastfm_pages_fetched", 0)
                            )
                            + int(expanded_out.get("lastfm_pages_fetched", 0)),
                            "lastfm_pages_planned": int(
                                expansion_record["out"].get("lastfm_pages_planned", 0)
                            )
                            + int(expanded_out.get("lastfm_pages_planned", 0)),
                        }
                    )
                    expansion_record["out"] = combined_out
                    eligible, local_reject = _filter_candidate_pool(
                        combined,
                        date_key=date_key,
                        history=history_index,
                        policy=cooldown_policy,
                        album_days=cooldown_policy.album_days,
                        artist_days=cooldown_policy.artist_days,
                        type_flags=type_flags,
                        used_album_keys=used_album_keys,
                        used_artist_keys=used_artist_keys,
                    )
                    expansion_record["strict_eligible"] = eligible
                    for key, value in local_reject.items():
                        reject_counts[key] += value
                    stage1_meta = _attempt_meta_from_out(
                        tag=expansion_record["tag"],
                        theme_key=expansion_record["theme_key"],
                        out=combined_out,
                        eligible=eligible,
                        reject_counts=local_reject,
                        fallback_stage=1,
                        candidate_scope="expanded_lastfm_one_page",
                    )
                    stage1_meta.update(
                        {
                            "expansion_before": expansion_before,
                            "expansion_after": expansion_after,
                            "additional_requests": additional_requests,
                        }
                    )
                    attempts_meta.append(stage1_meta)
                    if len(eligible) >= 3:
                        sampled = sample_three(eligible, expansion_record["theme_key"])
                        if len(sampled) >= 3:
                            picked = sampled
                            picked_theme_tag = expansion_record["tag"]
                            picked_theme_key = expansion_record["theme_key"]
                            selected_candidates = combined
                            selected_eligible = eligible
                            fallback_stage = 1
                            stage1_meta["selected"] = True
                except (ProviderApiError, BrokerRequestError, RequestFailed, RuntimeError) as exc:
                    if not _is_known_external_failure(exc):
                        raise
                    additional_requests = max(
                        0,
                        _request_count(broker.get_stats_snapshot()) - requests_before,
                    )
                    attempts_meta.append(
                        {
                            "tag": expansion_record["tag"],
                            "theme_key": expansion_record["theme_key"],
                            "fallback_stage": 1,
                            "candidate_scope": "expanded_lastfm_one_page",
                            "network_failed": True,
                            "additional_requests": additional_requests,
                            "error": _format_external_api_failure(
                                slot_id=slot_id,
                                tag=expansion_record["tag"],
                                stage="candidate_expansion",
                                exc=exc,
                                fetch_limit=max(n, 200),
                            ),
                        }
                    )

            if len(picked) < 3:
                for record in tag_records:
                    eligible, local_reject = _filter_candidate_pool(
                        record["candidates"],
                        date_key=date_key,
                        history=history_index,
                        policy=cooldown_policy,
                        album_days=cooldown_policy.album_days,
                        artist_days=cooldown_policy.fallback_days,
                        type_flags=type_flags,
                        used_album_keys=used_album_keys,
                        used_artist_keys=used_artist_keys,
                    )
                    for key, value in local_reject.items():
                        reject_counts[key] += value
                    stage2_meta = dict(record["attempt_meta"])
                    stage2_meta.update(
                        {
                            "fallback_stage": 2,
                            "candidate_scope": "reuse_normalized",
                            "eligible": len(eligible),
                            "candidate_count_after_hard_filters": len(eligible),
                            "reject_counts": dict(local_reject),
                        }
                    )
                    attempts_meta.append(stage2_meta)
                    if len(eligible) >= 3:
                        sampled = sample_three(eligible, record["theme_key"])
                        if len(sampled) >= 3:
                            picked = sampled
                            picked_theme_tag = record["tag"]
                            picked_theme_key = record["theme_key"]
                            selected_candidates = record["candidates"]
                            selected_eligible = eligible
                            fallback_stage = 2
                            stage2_meta["selected"] = True
                            break

            if len(picked) < 3 and stage3_daily_pick_count < cooldown_policy.stage3_daily_pick_cap:
                for record in tag_records:
                    base_eligible, _base_reject = _filter_candidate_pool(
                        record["candidates"],
                        date_key=date_key,
                        history=history_index,
                        policy=cooldown_policy,
                        album_days=cooldown_policy.album_days,
                        artist_days=cooldown_policy.fallback_days,
                        type_flags=type_flags,
                        used_album_keys=used_album_keys,
                        used_artist_keys=used_artist_keys,
                    )
                    relaxed_eligible, local_reject = _filter_candidate_pool(
                        record["candidates"],
                        date_key=date_key,
                        history=history_index,
                        policy=cooldown_policy,
                        album_days=cooldown_policy.fallback_days,
                        artist_days=cooldown_policy.fallback_days,
                        type_flags=type_flags,
                        used_album_keys=used_album_keys,
                        used_artist_keys=used_artist_keys,
                    )
                    base_keys = {_candidate_identity(item)[0] for item in base_eligible}
                    relaxed_candidates = [
                        item
                        for item in relaxed_eligible
                        if _candidate_identity(item)[0] not in base_keys
                        and within_cooldown(
                            date_key,
                            history_index.album_last_seen.get(_candidate_identity(item)[0]),
                            cooldown_policy.album_days,
                        )
                        and not within_cooldown(
                            date_key,
                            history_index.album_last_seen.get(_candidate_identity(item)[0]),
                            cooldown_policy.fallback_days,
                        )
                    ]
                    stage3_meta = dict(record["attempt_meta"])
                    stage3_meta.update(
                        {
                            "fallback_stage": 3,
                            "candidate_scope": "reuse_normalized",
                            "eligible": len(relaxed_eligible),
                            "candidate_count_after_hard_filters": len(relaxed_eligible),
                            "reject_counts": dict(local_reject),
                            "stage3_relaxed_candidates": len(relaxed_candidates),
                        }
                    )
                    attempts_meta.append(stage3_meta)
                    if len(base_eligible) < 2 or not relaxed_candidates:
                        continue
                    base_picks, _ = _weighted_sample_unique_artists(
                        base_eligible,
                        count=2,
                        rng=random.Random(f"{date_key}:{slot_id}:{record['theme_key']}:stage3-base"),
                        recent_ids=set(),
                        cooling_penalty=None,
                        log_line=log_line,
                        temperature=slot_temperature,
                    )
                    if len(base_picks) < 2:
                        continue
                    base_artist_keys = set().union(*(_candidate_identity(item)[1] for item in base_picks))
                    relaxed_candidates = [
                        item
                        for item in relaxed_candidates
                        if not _candidate_identity(item)[1].intersection(base_artist_keys)
                    ]
                    relaxed_pick, _ = _weighted_sample_unique_artists(
                        relaxed_candidates,
                        count=1,
                        rng=random.Random(f"{date_key}:{slot_id}:{record['theme_key']}:stage3-relaxed"),
                        recent_ids=set(),
                        cooling_penalty=None,
                        log_line=log_line,
                        temperature=slot_temperature,
                    )
                    if len(relaxed_pick) != 1:
                        continue
                    picked = [*base_picks, relaxed_pick[0]]
                    picked_theme_tag = record["tag"]
                    picked_theme_key = record["theme_key"]
                    selected_candidates = record["candidates"]
                    selected_eligible = relaxed_eligible
                    fallback_stage = 3
                    stage3_daily_pick_count += 1
                    relaxed_key, _relaxed_artists = _candidate_identity(relaxed_pick[0])
                    nobj = getattr(relaxed_pick[0], "n", None)
                    stage3_pick_info = {
                        "slot_id": slot_id,
                        "release_group_mbid": getattr(nobj, "mb_release_group_id", None) if nobj else None,
                        "identity_kind": history_index.album_identity_kind.get(relaxed_key, "rg_mbid"),
                        "identity_key": relaxed_key,
                        "history_date": history_index.album_last_seen.get(relaxed_key),
                    }
                    stage3_meta["selected"] = True
                    stage3_meta["stage3_pick"] = stage3_pick_info
                    break

            if len(picked) < 3 and stage3_daily_pick_count >= cooldown_policy.stage3_daily_pick_cap:
                attempts_meta.append(
                    {
                        "fallback_stage": 3,
                        "candidate_scope": "reuse_normalized",
                        "blocked": "stage3_daily_cap",
                        "stage3_daily_pick_cap": cooldown_policy.stage3_daily_pick_cap,
                    }
                )

            if len(picked) < 3:
                tried_tags = [a.get("tag") for a in attempts_meta if isinstance(a, dict) and a.get("tag")]
                unique_tags = list(dict.fromkeys(tried_tags))
                pages_fetched = sum(int(a.get("lastfm_pages_fetched", 0)) for a in attempts_meta if isinstance(a, dict))
                diag = {
                    "slot_id": slot_id,
                    "tags_tried": len(unique_tags),
                    "max_tag_tries_per_slot": max_tag_tries,
                    "pages_fetched": pages_fetched,
                    "tag_attempts": attempts_meta,
                    "reject_counts": reject_counts,
                    "top_rejection_reasons": _top_rejection_reasons(reject_counts),
                    "history": history_context,
                    "candidate_scope_expanded": candidate_scope_expanded,
                    "expansion_before": expansion_before,
                    "expansion_after": expansion_after,
                    "additional_requests": additional_requests,
                    "fallback_stage": "exhausted_after_stage3",
                }
                print(_format_slot_exhaustion_failure(diag))
                print(f"exhaustion slot={slot_id} diagnostic={diag}")
                log_line(f"slot_exhausted {json.dumps(diag, ensure_ascii=False)}")
                exhaustion.append(diag)
                return 2

            if fallback_stage <= 1:
                slot_cooldown_windows[slot_id] = (
                    cooldown_policy.album_days,
                    cooldown_policy.artist_days,
                )
            elif fallback_stage == 2:
                slot_cooldown_windows[slot_id] = (
                    cooldown_policy.album_days,
                    cooldown_policy.fallback_days,
                )
            else:
                slot_cooldown_windows[slot_id] = (
                    cooldown_policy.fallback_days,
                    cooldown_policy.fallback_days,
                )

            selected_attempt = _selected_attempt_meta(attempts_meta, picked_theme_tag)
            diagnostics_summary["slot_progress"][str(slot_id)] = {
                "slot_id": slot_id,
                "selected_tag": picked_theme_tag,
                "attempted_tags": list(
                    dict.fromkeys(
                        str(attempt.get("tag"))
                        for attempt in attempts_meta
                        if isinstance(attempt, dict) and str(attempt.get("tag") or "").strip()
                    )
                ),
                "history": history_context,
                "fallback_stage": fallback_stage,
                "candidate_scope_expanded": candidate_scope_expanded,
                "expansion_before": expansion_before,
                "expansion_after": expansion_after,
                "additional_requests": additional_requests,
                "album_cooldown_days": slot_cooldown_windows[slot_id][0],
                "artist_cooldown_days": slot_cooldown_windows[slot_id][1],
                "theme_cooldown_days": cooldown_policy.theme_days,
                "stage3_used": stage3_pick_info is not None,
                "top_rejection_reasons": _top_rejection_reasons(reject_counts),
                "strict_raw_candidates": int(selected_attempt.get("raw_candidate_count", 0) or 0),
                "strict_normalized_candidates": int(
                    selected_attempt.get("normalization_success_count", 0) or 0
                ),
                "eligible_candidates": int(selected_attempt.get("eligible", 0) or 0),
            }

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
            slot_payload["observability"] = _slot_observability_payload(
                slot_id=slot_id,
                tag_attempts=tag_attempts,
                picked_theme_tag=picked_theme_tag,
                attempts_meta=attempts_meta,
                reject_counts=reject_counts,
                scored_items=scored_items,
                history_context=history_context,
                fallback={
                    "stage": fallback_stage,
                    "candidate_scope_expanded": candidate_scope_expanded,
                    "expansion_before": expansion_before,
                    "expansion_after": expansion_after,
                    "additional_requests": additional_requests,
                    "album_cooldown_days": slot_cooldown_windows[slot_id][0],
                    "artist_cooldown_days": slot_cooldown_windows[slot_id][1],
                    "theme_cooldown_days": cooldown_policy.theme_days,
                    "stage3_used": stage3_pick_info is not None,
                    "stage3_pick": stage3_pick_info,
                    "stage3_daily_pick_cap": cooldown_policy.stage3_daily_pick_cap,
                },
                normalization_shadow=_normalization_shadow_slot_payload(
                    candidates=selected_candidates,
                    eligible=selected_eligible,
                    final_picks=scored_items,
                    cli_min_confidence=float(min_confidence),
                    cli_ambiguity_gap=float(ambiguity_gap),
                    config_min_confidence=config_reference_min_confidence,
                    config_ambiguity_gap=config_reference_ambiguity_gap,
                ),
            )
            slots_payload.append(slot_payload)
            exhaustion.append({"slot_id": slot_id, "attempts": attempts_meta, "reject_counts": reject_counts, "fetched_count": fetched_count})

        effective_theme = (theme or "").strip() or (tag or "").strip() or "auto"

        broker_stats = broker.get_stats_snapshot()
        diagnostics_summary["requests"] = {k: int(v.get("requests", 0)) for k, v in broker_stats.items()}
        diagnostics_summary["timeouts"] = {k: int(v.get("timeouts", 0)) for k, v in broker_stats.items()}
        diagnostics_summary["retries"] = {k: int(v.get("retries", 0)) for k, v in broker_stats.items()}
        diagnostics_summary["slot_rejections"] = {
            str(e.get("slot_id")): _top_rejection_reasons(e.get("reject_counts", {}))
            for e in exhaustion if isinstance(e, dict)
        }

        issue = {
            "output_schema_version": "1.0",
            "date": date_key,
            "run_id": run_id,
            "theme_of_day": effective_theme,
            "decade_theme": None,
            "slot": now_slot_id,
            "now_slot_id": now_slot_id,
            "run_at": beijing_now.isoformat(timespec="seconds"),
            "lineage_source": None,
            "picks": [],
            "constraints": {"min_confidence": float(min_confidence), "ambiguity_gap": float(ambiguity_gap)},
            "slots": [],
            "generation": {"started_at": datetime.now().isoformat(timespec="seconds"), "versions": {"daily3albums": getattr(cfg, "version", None)}},
            "warnings": [],
            "diagnostics": {"exhaustion": exhaustion, "summary": diagnostics_summary},
        }
        observability_payload = _new_recommendation_observability(
            repo_root=repo_root,
            issue=issue,
            slot_payloads=slots_payload,
            discogs_enabled=discogs_enabled,
        )

        cover_version = issue["generation"].get("started_at")
        for slot_payload in slots_payload:
            scored_items = slot_payload.pop("scored_items", [])
            slot_observability = slot_payload.get("observability") if isinstance(slot_payload.get("observability"), dict) else None
            for slot_name, s in zip(slot_names, scored_items):
                rg_id = getattr(getattr(s, "n", None), "mb_release_group_id", "") or ""
                if rg_id:
                    observability_payload["enrichment"]["cover_attempted"] += 1
                    observability_payload["enrichment"]["musicbrainz_detail_attempted"] += 1
                cover_result = cover_adapter.fetch_cover(rg_id) if rg_id else None
                if cover_result and cover_result.has_cover:
                    observability_payload["enrichment"]["cover_success"] += 1
                mb_details = musicbrainz_get_release_group_details(
                    broker,
                    mb_user_agent=env.mb_user_agent,
                    rg_id=rg_id,
                ) if rg_id else None
                if mb_details:
                    observability_payload["enrichment"]["musicbrainz_detail_success"] += 1
                wikipedia_url = getattr(mb_details, "wikipedia_url", None) if mb_details else None
                if wikipedia_url:
                    observability_payload["enrichment"]["wikipedia_overview_attempted"] += 1
                wikipedia_overview = _wikipedia_overview_from_url(
                    broker,
                    wikipedia_url,
                    env.mb_user_agent,
                    log_line,
                ) if mb_details else None
                if wikipedia_overview:
                    observability_payload["enrichment"]["wikipedia_overview_success"] += 1
                item = _pick_to_issue_item(
                    tag=slot_payload.get("theme") or effective_theme,
                    slot=slot_name,
                    s=s,
                    cover_version=cover_version,
                    cover_result=cover_result,
                    mb_details=mb_details,
                    wikipedia_overview=wikipedia_overview,
                )
                item["style_key"] = slot_payload.get("theme_key")
                item["theme_key"] = slot_payload.get("theme_key")
                slot_payload["picks"].append(item)
                if slot_observability is not None:
                    slot_observability["final_picks"].append(_observability_final_pick(item, s))
            issue["slots"].append({k: v for k, v in slot_payload.items() if k in {"slot_id", "window_label", "theme", "theme_key", "constraints", "picks"}})
        _finalize_recommendation_observability(observability_payload)

        now_slot_payload = next((s for s in issue["slots"] if s.get("slot_id") == now_slot_id), issue["slots"][0])
        issue["picks"] = now_slot_payload.get("picks", [])

        errors = validate_today_constraints(
            issue,
            history_index,
            policy=cooldown_policy,
            slot_windows=slot_cooldown_windows,
            stage3_pick_count=stage3_daily_pick_count,
        )
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
        if skip_ui_build:
            print("BUILD: ui bundle skipped (--skip-ui-build)")
        else:
            print("BUILD: ui bundle")
            npm_exe = shutil.which("npm.cmd") or shutil.which("npm")
            if not npm_exe:
                raise SystemExit("UI build failed: npm not found. Install Node.js and ensure npm is on PATH.")
            ui_timeout_s = int(getattr(cfg, "ui_build_timeout_s", 300))
            try:
                ui_build = subprocess.run(
                    [npm_exe, "--prefix", str(ui_dir), "run", "build"],
                    check=False,
                    cwd=repo_root,
                    timeout=ui_timeout_s,
                )
            except subprocess.TimeoutExpired as exc:
                print(
                    "BUILD ERROR: ui build timed out "
                    f"timeout_s={ui_timeout_s} cmd={' '.join(exc.cmd) if isinstance(exc.cmd, (list, tuple)) else exc.cmd}"
                )
                log_line(f"ui_build_timeout timeout_s={ui_timeout_s}")
                return 2
            if ui_build.returncode != 0:
                print("BUILD ERROR: ui build failed. See npm output above.")
                return 2
        if not ui_dist_dir.exists():
            if skip_ui_build:
                print("BUILD ERROR: ui/dist is missing. Run npm --prefix ui run build or omit --skip-ui-build.")
            else:
                print("BUILD ERROR: ui/dist is missing after build.")
            return 2

        out_public_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree_overwrite(web_dir, out_public_dir)
        _copy_tree_overwrite(ui_dist_dir, out_public_dir, skip_top_level_dirs={"data"})
        _reset_generated_data_dir(out_public_dir)
        _restore_history_seed(out_public_dir, repo_root, log_line)

        from daily3albums.artifact_writer import (
            OutputValidationError,
            atomic_write_json,
            write_daily_artifacts,
        )
        try:
            paths = write_daily_artifacts(
                issue=issue,
                out_public_dir=out_public_dir,
                quarantine_rows=quarantine_rows or None,
                archive_retention_days=int(getattr(cfg, "archive_retention_days", 7)),
                force_archive_rewrite=force_archive_rewrite,
            )
        except OutputValidationError as exc:
            print(f"BUILD ERROR: archive artifact validation failed: {exc}")
            return 2
        if issue.get("run_id") != generated_run_id:
            print(
                "ARCHIVE IMMUTABILITY: reused published archive "
                f"date={issue.get('date')} published_run_id={issue.get('run_id')} "
                f"discarded_generated_run_id={generated_run_id}"
            )
            log_line(
                "archive_immutability status=reused_published_date "
                f"date={issue.get('date')} published_run_id={issue.get('run_id')} "
                f"discarded_generated_run_id={generated_run_id}"
            )
            observability_payload = _archive_lock_observability(
                repo_root=repo_root,
                issue=issue,
                generated_run_id=generated_run_id,
            )
        observability_path = out_public_dir / "data" / "recommendation-observability.json"
        atomic_write_json(observability_path, observability_payload)
        paths["recommendation_observability"] = observability_path

        if diagnostics:
            print("\n== Diagnostics Summary ==")
            print("Decade constraints: OFF")
            print(json.dumps(diagnostics_summary, ensure_ascii=False, indent=2))

        print("BUILD OK")
        print(f"out={out_public_dir}")
        for k, v in paths.items():
            print(f"{k}={v}")
        return 0
    except KeyboardInterrupt:
        _print_interrupt_diagnostics(broker=broker, diagnostics_summary=diagnostics_summary)
        return 130
    finally:
        broker.close()



def _print_interrupt_diagnostics(
    *,
    broker: RequestBroker | None,
    diagnostics_summary: dict[str, Any] | None,
) -> None:
    print("Interrupted by user (Ctrl+C)")
    if broker is not None:
        try:
            print("\n== Adapter Stats ==")
            print(json.dumps(broker.get_stats_snapshot(), ensure_ascii=False, indent=2))
        except Exception:
            pass
    if diagnostics_summary:
        print("\n== Slot Progress ==")
        print(json.dumps(diagnostics_summary.get("slot_progress", {}), ensure_ascii=False, indent=2))

# ----------------------------
# CLI entry
# ----------------------------

def main() -> None:
    p = argparse.ArgumentParser(prog="daily3albums")
    sub = p.add_subparsers(dest="cmd", required=True)

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
    p_dry.add_argument(
        "--diagnostics",
        action="store_true",
        help="Print MB and progress diagnostics.",
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
        help="Override date key (YYYY-MM-DD). If empty, use Asia/Shanghai product date.",
    )
    p_build.add_argument(
        "--theme",
        type=str,
        default="",
        help="Theme of the day. If empty, use tag.",
    )
    p_build.add_argument(
        "--diagnostics",
        action="store_true",
        help="Print per-adapter request/timeout/retry and slot rejection summaries.",
    )
    p_build.add_argument(
        "--skip-ui-build",
        action="store_true",
        help="Reuse existing ui/dist instead of running npm --prefix ui run build. Default keeps one-command builds self-contained.",
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

    if args.cmd == "probe-lastfm":
        raise SystemExit(cmd_probe_lastfm(repo_root, tag=args.tag, limit=args.limit, verbose=args.verbose, raw=args.raw))
    if args.cmd == "probe-mb":
        raise SystemExit(cmd_probe_mb(repo_root, artist=args.artist, title=args.title, limit=args.limit, verbose=args.verbose))
    if args.cmd == "dry-run":
        try:
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
                    diagnostics=args.diagnostics,
                )
            )
        except KeyboardInterrupt:
            _print_interrupt_diagnostics(broker=None, diagnostics_summary=None)
            raise SystemExit(130)
    if args.cmd == "build":
        try:
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
                    diagnostics=args.diagnostics,
                    skip_ui_build=args.skip_ui_build,
                )
            )
        except KeyboardInterrupt:
            _print_interrupt_diagnostics(broker=None, diagnostics_summary=None)
            raise SystemExit(130)

    raise SystemExit(2)


if __name__ == "__main__":
    main()
