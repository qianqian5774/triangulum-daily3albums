from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from daily3albums.adapters import (
    MbReleaseGroupSummary,
    ProviderApiError,
    discogs_database_search,
    lastfm_tag_top_albums,
    listenbrainz_metadata_release_groups,
    listenbrainz_sitewide_release_groups,
    musicbrainz_best_release_group_match_debug,
    musicbrainz_get_release_group,
    musicbrainz_identity_similarity,
    musicbrainz_normalize_mbid_to_release_group,
    musicbrainz_normalize_mbid_to_release_group_debug,
    musicbrainz_same_work,
)
from daily3albums.normalization_policy import (
    NormalizationPolicy,
    evaluate_normalization_trace,
)
from daily3albums.request_broker import BrokerRequestError, BrokerResponseError, RequestFailed
from daily3albums.runtime_outcomes import OutcomeCode, outcome_code_for_exception


@dataclass
class Candidate:
    title: str
    artist: str
    image_url: Optional[str] = None
    lastfm_rank: Optional[int] = None
    lastfm_mbid: Optional[str] = None
    sources: set[str] = field(default_factory=set)
    source_ranks: dict[str, int] = field(default_factory=dict)
    rg_mbid_hint: Optional[str] = None
    artist_mbid_hint: Optional[str] = None


@dataclass
class NormalizedCandidate:
    title: str
    artist: str
    mb_release_group_id: Optional[str]
    artist_mbids: list[str] = field(default_factory=list)
    primary_type: Optional[str] = None
    first_release_date: Optional[str] = None
    confidence: float = 1.0
    source: str = "hint"


@dataclass
class ScoredCandidate:
    score: float
    c: Candidate
    n: Optional[NormalizedCandidate]
    debug: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    mb_debug: list[str] = field(default_factory=list)


Normalized = NormalizedCandidate
Scored = ScoredCandidate


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _norm_key(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s


def _light_album_key(artist: str, title: str) -> str:
    return f"{_norm_key(artist)}::{_norm_key(title)}"


def _stable_shuffle(items: list[Any], seed: str) -> None:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    r = random.Random(int(h[:16], 16))
    r.shuffle(items)


def _extract_reject_reason(dbg: list[str]) -> str:
    for line in reversed(dbg):
        if "search:rejected ambiguous" in line:
            return "ambiguous"
        if "search:rejected confidence" in line:
            return "low_confidence"
        if line.startswith("final:none") or "search:final=none" in line:
            return "no_match"
    return "none"


def _write_quarantine_line(path: str, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _normalization_trace(
    *,
    source: str,
    best_confidence: float,
    second_best_confidence: float | None = None,
    identity_title_similarity: float | None = None,
    identity_artist_similarity: float | None = None,
    runner_release_group_mbid: str | None = None,
    runner_same_work: bool | None = None,
) -> dict[str, Any]:
    path_by_source = {
        "mbid:release-group": "direct_release_group_mbid",
        "mbid:release->rg": "release_mbid_to_release_group",
        "hint:rg_mbid": "external_release_group_hint",
    }
    strategy_by_source = {
        "search:strict": "strict",
        "search:clean_strict": "cleaned_strict",
        "search:clean_loose": "cleaned_loose",
        "search:title_only": "title_only",
    }
    is_text_search = source.startswith("search:")
    second = float(second_best_confidence) if second_best_confidence is not None else None
    return {
        "path": path_by_source.get(source, "musicbrainz_text_search" if is_text_search else "unknown"),
        "query_strategy": strategy_by_source.get(source) if is_text_search else None,
        "best_confidence": float(best_confidence),
        "second_best_confidence": second,
        "has_second_best": second is not None,
        "ambiguity_gap": round(float(best_confidence) - second, 6) if second is not None else None,
        "shadow_comparison_applicable": is_text_search,
        "identity_title_similarity": identity_title_similarity,
        "identity_artist_similarity": identity_artist_similarity,
        "runner_release_group_mbid": runner_release_group_mbid,
        "runner_same_work": runner_same_work,
    }


def _shadow_reference_result(
    trace: dict[str, Any],
    *,
    min_confidence: float,
    ambiguity_gap: float,
) -> dict[str, Any]:
    if not bool(trace.get("shadow_comparison_applicable")):
        return {
            "status": "not_applicable",
            "rejected": False,
            "reason": "not_applicable_non_text_path",
            "low_confidence": False,
            "ambiguous": False,
        }

    best = float(trace.get("best_confidence", 0.0) or 0.0)
    gap = trace.get("ambiguity_gap")
    low_confidence = best < float(min_confidence)
    ambiguous = bool(trace.get("has_second_best")) and gap is not None and float(gap) < float(ambiguity_gap)
    rejected = low_confidence or ambiguous
    reason = "low_confidence" if low_confidence else ("ambiguous" if ambiguous else "accepted")
    return {
        "status": "evaluated",
        "rejected": rejected,
        "reason": reason,
        "low_confidence": low_confidence,
        "ambiguous": ambiguous,
    }


def _attach_shadow_results(
    diagnostics: dict[str, Any],
    *,
    cli_min_confidence: float,
    cli_ambiguity_gap: float,
    config_min_confidence: float,
    config_ambiguity_gap: float,
) -> None:
    trace = diagnostics.get("normalization_trace")
    if not isinstance(trace, dict):
        return
    record = dict(trace)
    record["references"] = {
        "cli_reference": {
            "min_confidence": float(cli_min_confidence),
            "ambiguity_gap": float(cli_ambiguity_gap),
            **_shadow_reference_result(
                trace,
                min_confidence=cli_min_confidence,
                ambiguity_gap=cli_ambiguity_gap,
            ),
        },
        "config_reference": {
            "min_confidence": float(config_min_confidence),
            "ambiguity_gap": float(config_ambiguity_gap),
            **_shadow_reference_result(
                trace,
                min_confidence=config_min_confidence,
                ambiguity_gap=config_ambiguity_gap,
            ),
        },
    }
    diagnostics["normalization_shadow"] = record


def _attach_policy_result(
    diagnostics: dict[str, Any],
    *,
    policy: NormalizationPolicy,
) -> None:
    trace = diagnostics.get("normalization_trace")
    if not isinstance(trace, dict):
        return
    decision = evaluate_normalization_trace(trace, policy)
    diagnostics["normalization_policy"] = {
        "policy_version": policy.policy_version,
        "authority": "config.normalizer",
        **decision.as_dict(),
    }
    shadow = diagnostics.get("normalization_shadow")
    if isinstance(shadow, dict):
        shadow["policy"] = dict(diagnostics["normalization_policy"])


def _normalize_candidate(
    broker,
    env,
    c: Candidate,
    debug: bool = False,
    mb_search_limit: int = 10,
    mb_max_queries_per_candidate: int = 3,
) -> tuple[Optional[NormalizedCandidate], dict[str, Any]]:
    dbg_lines: list[str] = []
    mb_search_queries_attempted = 0
    normalization_trace: dict[str, Any] | None = None

    def _mb_http_calls_snapshot() -> int | None:
        if not hasattr(broker, "get_stats_snapshot"):
            return None
        try:
            snapshot = broker.get_stats_snapshot()  # type: ignore[attr-defined]
        except Exception:
            return None
        bucket = snapshot.get("MusicBrainzAdapter") if isinstance(snapshot, dict) else None
        if not isinstance(bucket, dict):
            return 0
        return int(bucket.get("requests", 0))

    mb_calls_before = _mb_http_calls_snapshot()

    def _diag_payload() -> dict[str, Any]:
        nonlocal mb_search_queries_attempted
        mb_calls_after = _mb_http_calls_snapshot()
        mb_http_calls = 0
        if mb_calls_before is not None and mb_calls_after is not None:
            mb_http_calls = max(0, int(mb_calls_after) - int(mb_calls_before))
        return {
            "mb_debug": dbg_lines,
            "mb_search_queries_attempted": int(mb_search_queries_attempted),
            "mb_http_calls": int(mb_http_calls),
            # legacy key: kept for compatibility
            "mb_queries_attempted": int(mb_http_calls or mb_search_queries_attempted),
            "normalization_trace": dict(normalization_trace) if normalization_trace is not None else None,
        }

    def _extract_mb_queries_attempted(lines: list[str]) -> int:
        attempted = 0
        for line in lines:
            if line.startswith("search:queries_attempted="):
                m = re.search(r"queries_attempted=(\d+)", line)
                if m:
                    attempted = int(m.group(1))
        return attempted

    if c.lastfm_mbid:
        rg: MbReleaseGroupSummary | None
        if debug:
            rg, src, debug_lines = musicbrainz_normalize_mbid_to_release_group_debug(
                broker,
                mb_user_agent=env.mb_user_agent,
                mbid=c.lastfm_mbid,
            )
            dbg_lines.extend(debug_lines)
        else:
            rg, src = musicbrainz_normalize_mbid_to_release_group(
                broker,
                mb_user_agent=env.mb_user_agent,
                mbid=c.lastfm_mbid,
            )
        if rg is not None:
            title_sim, artist_sim = musicbrainz_identity_similarity(
                c.title,
                c.artist,
                rg.title,
                rg.artist_credit,
            )
            normalization_trace = _normalization_trace(
                source=src,
                best_confidence=1.0,
                identity_title_similarity=title_sim,
                identity_artist_similarity=artist_sim,
            )
            norm = NormalizedCandidate(
                title=c.title,
                artist=c.artist,
                mb_release_group_id=rg.id,
                artist_mbids=list(rg.artist_mbids or []),
                primary_type=rg.primary_type,
                first_release_date=rg.first_release_date,
                confidence=1.0,
                source=src,
            )
            return norm, _diag_payload()

    if c.rg_mbid_hint:
        rg = musicbrainz_get_release_group(broker, env.mb_user_agent, c.rg_mbid_hint)
        if rg is not None:
            title_sim, artist_sim = musicbrainz_identity_similarity(
                c.title,
                c.artist,
                rg.title,
                rg.artist_credit,
            )
            normalization_trace = _normalization_trace(
                source="hint:rg_mbid",
                best_confidence=1.0,
                identity_title_similarity=title_sim,
                identity_artist_similarity=artist_sim,
            )
            norm = NormalizedCandidate(
                title=c.title,
                artist=c.artist,
                mb_release_group_id=c.rg_mbid_hint,
                artist_mbids=list((rg.artist_mbids if rg else []) or ([c.artist_mbid_hint] if c.artist_mbid_hint else [])),
                primary_type=rg.primary_type if rg else None,
                first_release_date=rg.first_release_date if rg else None,
                confidence=1.0,
                source="hint:rg_mbid",
            )
            return norm, _diag_payload()
        dbg_lines.append("hint:rg_mbid_unresolved")

    match, runner_up_conf, dbg2 = musicbrainz_best_release_group_match_debug(
        broker,
        mb_user_agent=env.mb_user_agent,
        title=c.title,
        artist=c.artist,
        limit=int(mb_search_limit),
        max_queries_per_candidate=int(mb_max_queries_per_candidate),
    )
    if debug:
        dbg_lines.extend(dbg2)
    mb_search_queries_attempted = _extract_mb_queries_attempted(dbg2)

    if match is None:
        return None, _diag_payload()

    rg = match.rg
    runner_up = getattr(match, "runner_up", None)
    normalization_trace = _normalization_trace(
        source=match.method,
        best_confidence=float(match.confidence),
        second_best_confidence=runner_up_conf,
        identity_title_similarity=float(getattr(match, "title_sim", 1.0)),
        identity_artist_similarity=float(getattr(match, "artist_sim", 1.0)),
        runner_release_group_mbid=(runner_up.rg.id if runner_up is not None else None),
        runner_same_work=(
            musicbrainz_same_work(
                getattr(rg, "title", ""),
                getattr(rg, "artist_credit", ""),
                getattr(runner_up.rg, "title", ""),
                getattr(runner_up.rg, "artist_credit", ""),
            )
            if runner_up is not None
            else None
        ),
    )
    norm = NormalizedCandidate(
        title=c.title,
        artist=c.artist,
        mb_release_group_id=rg.id,
        artist_mbids=list(rg.artist_mbids or []),
        primary_type=rg.primary_type,
        first_release_date=rg.first_release_date,
        confidence=float(match.confidence),
        source=match.method,
    )
    return norm, _diag_payload()


def _merge_candidates(cands: list[Candidate]) -> list[Candidate]:
    merged: dict[str, Candidate] = {}
    for c in cands:
        k = _light_album_key(c.artist, c.title)
        if k not in merged:
            merged[k] = c
            continue
        m = merged[k]
        m.sources |= c.sources
        m.source_ranks.update(c.source_ranks)
        if not m.image_url and c.image_url:
            m.image_url = c.image_url
        if c.lastfm_rank is not None:
            if m.lastfm_rank is None or c.lastfm_rank < m.lastfm_rank:
                m.lastfm_rank = c.lastfm_rank
        if c.lastfm_mbid and not m.lastfm_mbid:
            m.lastfm_mbid = c.lastfm_mbid
        if c.rg_mbid_hint and not m.rg_mbid_hint:
            m.rg_mbid_hint = c.rg_mbid_hint
        if c.artist_mbid_hint and not m.artist_mbid_hint:
            m.artist_mbid_hint = c.artist_mbid_hint
    return list(merged.values())


def _candidate_source_counts(cands: list[Candidate]) -> dict[str, int]:
    counts = {"lastfm": 0, "discogs": 0, "listenbrainz": 0, "multi_source": 0}
    for c in cands:
        sources = {str(source).lower() for source in getattr(c, "sources", set()) or set()}
        for key in ("lastfm", "discogs", "listenbrainz"):
            if key in sources:
                counts[key] += 1
        if len(sources) > 1:
            counts["multi_source"] += 1
    return counts


def _score(norm: Optional[NormalizedCandidate], cand: Candidate, *, deepcut: bool, seed_key: str) -> float:
    src_bonus = max(0, len(cand.sources) - 1) * 6.0

    def peak_head(r: int) -> float:
        if r <= 0:
            return 0.0
        return max(0.0, 18.0 - r) * 0.8

    def peak_tail(r: int) -> float:
        if r <= 0:
            return 0.0
        return min(22.0, max(0.0, r - 60) * 0.12)

    ranks = list(cand.source_ranks.values())
    if cand.lastfm_rank is not None:
        ranks.append(cand.lastfm_rank)
    rank_score = 0.0
    for r in ranks:
        rank_score += peak_head(r) + peak_tail(r)

    if deepcut:
        for r in ranks:
            if r <= 25:
                rank_score -= (26 - r) * 0.9

    qual = 0.0
    if norm and norm.mb_release_group_id:
        qual += 6.0
    if norm and norm.primary_type == "Album":
        qual += 2.5
    if norm and norm.first_release_date:
        qual += 1.0

    h = hashlib.sha256((seed_key + _light_album_key(cand.artist, cand.title)).encode("utf-8")).hexdigest()
    jitter = (int(h[:8], 16) / 0xFFFFFFFF - 0.5) * 0.6

    return src_bonus + rank_score + qual + jitter


def _pick_slots(items: list[ScoredCandidate]) -> dict[str, Optional[ScoredCandidate]]:
    if not items:
        return {"Headliner": None, "Lineage": None, "DeepCut": None}
    headliner = items[0]

    def year_key(s: ScoredCandidate) -> int:
        if not s.n or not s.n.first_release_date:
            return 999999
        y = s.n.first_release_date[:4]
        return _safe_int(y, 999999)

    lineage = min(items, key=year_key)
    deepcut = next((s for s in items if s is not headliner and s is not lineage), None)
    return {"Headliner": headliner, "Lineage": lineage, "DeepCut": deepcut}


def run_dry_run(
    broker,
    env,
    *,
    tag: str,
    n: int = 200,
    topk: int = 200,
    deepcut: bool = False,
    seed_key: str = "default",
    split_slots: bool = False,
    mb_search_limit: int = 10,
    min_confidence: float = 0.80,
    ambiguity_gap: float = 0.06,
    config_reference_min_confidence: float = 0.72,
    config_reference_ambiguity_gap: float = 0.08,
    normalization_policy: NormalizationPolicy | None = None,
    mb_debug: bool = False,
    quarantine_out: str | None = None,
    prefilter_topn: int = 120,
    lastfm_page_start: int = 1,
    lastfm_max_pages: int = 6,
    mb_max_queries_per_candidate: int = 3,
    mb_max_candidates_per_slot: int = 120,
    mb_time_budget_s_per_slot: float = 90.0,
    discogs_enabled: bool = True,
    discogs_page_start: int = 1,
    discogs_max_pages: int = 3,
    discogs_per_page: int = 100,
    lastfm_only: bool = False,
) -> dict:
    active_normalization_policy = normalization_policy or NormalizationPolicy.defaults()
    if not env.lastfm_api_key:
        raise ProviderApiError(
            provider="Last.fm",
            stage="config_check",
            code=OutcomeCode.NOT_CONFIGURED,
            advice="Configure LASTFM_API_KEY, then retry.",
        )
    if not env.mb_user_agent:
        raise ProviderApiError(
            provider="MusicBrainz",
            stage="config_check",
            code=OutcomeCode.NOT_CONFIGURED,
            advice="Configure MB_USER_AGENT, then retry.",
        )

    h = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:8], 16)
    page_start = max(1, int(lastfm_page_start))
    max_pages = max(1, int(lastfm_max_pages))
    hard_cap = 1000
    deepcut_offset = (h % 2) if deepcut else 0
    bounded_start = min(page_start + deepcut_offset, hard_cap)
    bounded_end = min(page_start + max_pages - 1, hard_cap)
    if bounded_start > bounded_end:
        bounded_start = bounded_end
    lastfm_pages = list(range(bounded_start, bounded_end + 1))

    d_page_start = max(1, int(discogs_page_start))
    d_max_page = max(1, int(discogs_max_pages))
    d_hard_cap = 100
    d_offset = (h % 2) if deepcut else 0
    discogs_requested_page = min(d_page_start + d_offset, d_hard_cap)
    discogs_page_cap_hit = discogs_requested_page > d_max_page
    discogs_page = min(discogs_requested_page, d_max_page)
    discogs_per_page = min(100, max(1, int(discogs_per_page)))

    lb_offset = (200 + (h % 800)) if deepcut else (0 + (h % 200))
    lb_count = min(200, max(50, n))

    raw: list[Candidate] = []
    pages_fetched = 0
    for p in lastfm_pages:
        pages_fetched += 1
        tops = lastfm_tag_top_albums(broker, env.lastfm_api_key, tag=tag, limit=50, page=p)
        for a in tops:
            c = Candidate(title=a.name, artist=a.artist, image_url=a.image_extralarge)
            c.sources.add("lastfm")
            c.lastfm_rank = a.rank
            c.lastfm_mbid = a.mbid
            if a.rank is not None:
                c.source_ranks["lastfm"] = a.rank
            raw.append(c)

    discogs_diag = {
        "discogs_enabled": bool(discogs_enabled and not lastfm_only),
        "discogs_attempted": bool(env.discogs_token and discogs_enabled and not lastfm_only),
        "discogs_pages_fetched": 0,
        "discogs_page_cap_hit": bool(discogs_page_cap_hit),
        "discogs_failed": False,
        "discogs_failed_status": None,
        "discogs_cached_negative_used": False,
        "discogs_outcome_code": (
            OutcomeCode.DISABLED.value
            if lastfm_only or not discogs_enabled
            else OutcomeCode.NOT_CONFIGURED.value
            if not env.discogs_token
            else OutcomeCode.UNAVAILABLE.value
        ),
    }

    if env.discogs_token and discogs_enabled and not lastfm_only:
        try:
            ds = discogs_database_search(
                broker,
                env.discogs_token,
                q=tag,
                page=discogs_page,
                per_page=discogs_per_page,
            )
            adapter_diag = getattr(broker, "_discogs_last_diagnostics", None)
            if isinstance(adapter_diag, dict):
                discogs_diag.update({k: adapter_diag.get(k) for k in discogs_diag.keys() if k in adapter_diag})
            else:
                discogs_diag["discogs_pages_fetched"] = 1
            _stable_shuffle(ds, seed=f"{seed_key}:discogs:{discogs_page}")
            for it in ds:
                t = it.title or ""
                if " - " in t:
                    artist, title = t.split(" - ", 1)
                else:
                    artist, title = "", t
                c = Candidate(title=title.strip(), artist=artist.strip(), image_url=it.cover_image)
                c.sources.add("discogs")
                if it.rank:
                    c.source_ranks["discogs"] = it.rank
                raw.append(c)
        except (BrokerRequestError, BrokerResponseError, RequestFailed, ProviderApiError) as exc:
            discogs_diag["discogs_failed"] = True
            discogs_diag["discogs_outcome_code"] = outcome_code_for_exception(exc).value

    listenbrainz_diag = {
        "listenbrainz_attempted": not lastfm_only,
        "listenbrainz_failed": False,
        "listenbrainz_candidates": 0,
        "listenbrainz_outcome_code": (
            OutcomeCode.DISABLED.value if lastfm_only else OutcomeCode.UNAVAILABLE.value
        ),
    }
    if not lastfm_only:
        try:
            setattr(broker, "_listenbrainz_sitewide_outcome", None)
            lbs = listenbrainz_sitewide_release_groups(
                broker,
                count=lb_count,
                offset=lb_offset,
                range_="all_time",
            )
            sitewide_outcome = getattr(broker, "_listenbrainz_sitewide_outcome", None)
            sitewide_code = (
                sitewide_outcome.code
                if hasattr(sitewide_outcome, "code")
                else OutcomeCode.SUCCESS if lbs else OutcomeCode.LEGITIMATE_EMPTY
            )
            listenbrainz_diag["listenbrainz_outcome_code"] = sitewide_code.value
            if sitewide_code not in {OutcomeCode.SUCCESS, OutcomeCode.LEGITIMATE_EMPTY}:
                listenbrainz_diag["listenbrainz_failed"] = True
                lbs = []
            mbids = [x.release_group_mbid for x in lbs if x.release_group_mbid]
            meta: dict[str, Any] = {}
            metadata_failed = False
            for i in range(0, len(mbids), 25):
                part = mbids[i : i + 25]
                setattr(broker, "_listenbrainz_metadata_outcome", None)
                j = listenbrainz_metadata_release_groups(
                    broker,
                    part,
                    inc="artist tag release",
                )
                metadata_outcome = getattr(broker, "_listenbrainz_metadata_outcome", None)
                metadata_code = (
                    metadata_outcome.code
                    if hasattr(metadata_outcome, "code")
                    else OutcomeCode.SUCCESS if j else OutcomeCode.LEGITIMATE_EMPTY
                )
                listenbrainz_diag["listenbrainz_outcome_code"] = metadata_code.value
                if metadata_code not in {OutcomeCode.SUCCESS, OutcomeCode.LEGITIMATE_EMPTY}:
                    listenbrainz_diag["listenbrainz_failed"] = True
                    metadata_failed = True
                    break
                meta.update(j.get("release_groups") or j.get("payload", {}).get("release_groups") or {})

            tag_l = tag.lower().strip()
            for st in [] if metadata_failed else lbs:
                rgid = st.release_group_mbid
                m = meta.get(rgid) if isinstance(meta, dict) else None
                if not m:
                    continue
                rg = m.get("release_group") or {}
                tags = rg.get("tags") or []
                tag_names = []
                for t in tags:
                    if isinstance(t, dict) and t.get("tag"):
                        tag_names.append(str(t["tag"]).lower())
                    elif isinstance(t, str):
                        tag_names.append(t.lower())
                if tag_l not in tag_names:
                    continue
                c = Candidate(
                    title=str(rg.get("title") or rg.get("name") or st.release_group_name).strip(),
                    artist=str(st.artist_name).strip(),
                    image_url=None,
                )
                c.sources.add("listenbrainz")
                c.source_ranks["listenbrainz"] = st.rank
                c.rg_mbid_hint = rgid
                if st.artist_mbid:
                    c.artist_mbid_hint = st.artist_mbid
                raw.append(c)
                listenbrainz_diag["listenbrainz_candidates"] += 1
            if not listenbrainz_diag["listenbrainz_failed"]:
                listenbrainz_diag["listenbrainz_outcome_code"] = (
                    OutcomeCode.SUCCESS.value
                    if listenbrainz_diag["listenbrainz_candidates"]
                    else OutcomeCode.LEGITIMATE_EMPTY.value
                )
        except (BrokerRequestError, BrokerResponseError, RequestFailed, ProviderApiError) as exc:
            listenbrainz_diag["listenbrainz_failed"] = True
            listenbrainz_diag["listenbrainz_outcome_code"] = outcome_code_for_exception(exc).value

    merged = _merge_candidates(raw)
    raw_count = len(raw)
    merged_count = len(merged)
    source_counts = _candidate_source_counts(merged)

    pre: list[tuple[float, Candidate]] = []
    for c in merged:
        light_bonus = 0.0
        if c.lastfm_mbid:
            light_bonus += 1.5
        if c.rg_mbid_hint:
            light_bonus += 1.5
        pre.append((_score(None, c, deepcut=deepcut, seed_key=seed_key) + light_bonus, c))
    pre.sort(key=lambda x: x[0], reverse=True)

    prefilter_total = len(pre)
    topn = max(1, int(prefilter_topn))
    pre = pre[:topn]

    candidate_cap = max(1, int(mb_max_candidates_per_slot))
    mb_budget_s = max(0.001, float(mb_time_budget_s_per_slot))
    started = time.monotonic()
    mb_candidates_considered = 0
    mb_candidates_normalized = 0
    mb_queries_attempted_total = 0
    mb_search_queries_attempted_total = 0
    mb_http_calls_total = 0
    mb_budget_exceeded = False
    mb_cap_hit = False

    scored: list[ScoredCandidate] = []
    normalized_count = 0
    for _s0, c in pre:
        mb_candidates_considered += 1
        elapsed = time.monotonic() - started
        if elapsed >= mb_budget_s:
            mb_budget_exceeded = True
            mb_cap_hit = True
            break
        if mb_candidates_normalized >= candidate_cap:
            mb_cap_hit = True
            break
        norm = None
        dbg: dict[str, Any] = {}
        norm, dbg = _normalize_candidate(
            broker,
            env,
            c,
            debug=mb_debug,
            mb_search_limit=int(mb_search_limit),
            mb_max_queries_per_candidate=int(mb_max_queries_per_candidate),
        )
        _attach_shadow_results(
            dbg,
            cli_min_confidence=float(min_confidence),
            cli_ambiguity_gap=float(ambiguity_gap),
            config_min_confidence=float(config_reference_min_confidence),
            config_ambiguity_gap=float(config_reference_ambiguity_gap),
        )
        _attach_policy_result(dbg, policy=active_normalization_policy)
        mb_search_queries_attempted_total += int(dbg.get("mb_search_queries_attempted", 0))
        mb_http_calls_total += int(dbg.get("mb_http_calls", 0))
        mb_queries_attempted_total += int(dbg.get("mb_queries_attempted", 0))
        mb_candidates_normalized += 1
        normalized_count += 1

        s = _score(norm, c, deepcut=deepcut, seed_key=seed_key)
        scored.append(ScoredCandidate(score=s, c=c, n=norm, debug=dbg, mb_debug=dbg.get("mb_debug", [])))

        if quarantine_out and norm is None:
            payload = {
                "tag": tag,
                "rank": c.lastfm_rank,
                "artist": c.artist,
                "title": c.title,
                "lastfm_mbid": c.lastfm_mbid,
                "image_url": c.image_url,
                "reject_reason": _extract_reject_reason(dbg.get("mb_debug", [])),
                "debug_tail": dbg.get("mb_debug", [])[-30:],
            }
            _write_quarantine_line(quarantine_out, payload)

    scored.sort(key=lambda x: x.score, reverse=True)
    top = scored[:topk]
    slots = _pick_slots(top) if split_slots else {}
    candidates = [x.c for x in scored]
    normalization_success_count = sum(1 for x in scored if x.n is not None)
    normalization_failed_count = sum(1 for x in scored if x.n is None)
    return {
        "requested_candidate_count": int(n),
        "lastfm_pages_fetched": pages_fetched,
        "lastfm_pages_planned": len(lastfm_pages),
        "raw_candidate_count": raw_count,
        "merged_candidate_count": merged_count,
        "source_counts": source_counts,
        "candidates": candidates,
        "scored": scored,
        "top": top,
        "slots": slots,
        "prefilter_total": prefilter_total,
        "prefilter_topn": len(pre),
        "normalized_count": normalized_count,
        "normalization_success_count": normalization_success_count,
        "normalization_failed_count": normalization_failed_count,
        "mb_candidates_considered": mb_candidates_considered,
        "mb_candidates_normalized": mb_candidates_normalized,
        "mb_queries_attempted_total": mb_queries_attempted_total,
        "mb_search_queries_attempted_total": mb_search_queries_attempted_total,
        "mb_http_calls_total": mb_http_calls_total,
        "mb_budget_exceeded": mb_budget_exceeded,
        "mb_cap_hit": mb_cap_hit,
        "mb_time_spent_s": round(time.monotonic() - started, 3),
        "mb_max_candidates_per_slot": candidate_cap,
        "mb_time_budget_s_per_slot": mb_budget_s,
        **discogs_diag,
        **listenbrainz_diag,
    }
