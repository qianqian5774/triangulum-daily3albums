# daily3albums/dry_run.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from daily3albums.adapters import (
    LastFmTopAlbum,
    MbReleaseGroupSummary,
    lastfm_tag_top_albums,
    musicbrainz_best_release_group_match,
    musicbrainz_best_release_group_match_debug,
    musicbrainz_normalize_mbid_to_release_group,
    musicbrainz_normalize_mbid_to_release_group_debug,
)


@dataclass
class Candidate:
    title: str
    artist: str
    lastfm_mbid: str
    lastfm_rank: int
    image_url: str


@dataclass
class Normalized:
    mb_release_group_id: str
    first_release_date: str
    primary_type: str
    confidence: float
    source: str


@dataclass
class Scored:
    c: Candidate
    n: Optional[Normalized]
    score: int
    reason: str
    mb_debug: list[str] = field(default_factory=list)


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _score(c: Candidate, n: Optional[Normalized]) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []

    if n and n.mb_release_group_id:
        score += 20
        reasons.append("mb:+20")

        pt = (n.primary_type or "").lower()
        if pt == "album":
            score += 10
            reasons.append("type:album:+10")
        elif pt in ("ep", "single"):
            score -= 5
            reasons.append(f"type:{pt}:-5")

        if n.first_release_date:
            score += 2
            reasons.append("date:+2")

    rank_bonus = max(0, 20 - (c.lastfm_rank or 9999))
    if rank_bonus:
        score += rank_bonus
        reasons.append(f"rank:+{rank_bonus}")

    return score, ",".join(reasons)


def _normalize_candidate(
    broker,
    mb_user_agent: str,
    c: Candidate,
    mb_search_limit: int = 10,
    min_confidence: float = 0.80,
    mb_debug: bool = False,
) -> tuple[Optional[Normalized], list[str]]:
    dbg: list[str] = []

    # 1) mbid 确定性链路：release-group -> release -> release-group
    if c.lastfm_mbid:
        rg: MbReleaseGroupSummary | None
        if mb_debug:
            # 期望 adapters.musicbrainz_normalize_mbid_to_release_group_debug 返回:
            # (rg: Optional[MbReleaseGroupSummary], src: str, debug_lines: list[str])
            rg, src, debug_lines = musicbrainz_normalize_mbid_to_release_group_debug(
                broker,
                mb_user_agent=mb_user_agent,
                mbid=c.lastfm_mbid,
            )
            dbg.append(f"mbid_present=yes src={src} ok={'yes' if rg else 'no'}")
            dbg.extend(debug_lines)
        else:
            rg, src = musicbrainz_normalize_mbid_to_release_group(
                broker,
                mb_user_agent=mb_user_agent,
                mbid=c.lastfm_mbid,
            )
            dbg.append(f"mbid_present=yes src={src} ok={'yes' if rg else 'no'}")

        if rg is not None:
            return (
                Normalized(
                    mb_release_group_id=rg.id,
                    first_release_date=rg.first_release_date or "",
                    primary_type=rg.primary_type or "",
                    confidence=1.0,
                    source=src,
                ),
                dbg,
            )
    else:
        dbg.append("mbid_present=no")

    # 2) 文本搜索兜底：需要过置信度阈值，否则宁缺毋滥
    if mb_debug:
        match, dbg2 = musicbrainz_best_release_group_match_debug(
            broker,
            mb_user_agent=mb_user_agent,
            title=c.title,
            artist=c.artist,
            limit=mb_search_limit,
        )
        dbg.extend(dbg2)
    else:
        match = musicbrainz_best_release_group_match(
            broker,
            mb_user_agent=mb_user_agent,
            title=c.title,
            artist=c.artist,
            limit=mb_search_limit,
        )

    if match is None:
        dbg.append("search:final=none")
        return None, dbg

    if match.confidence < min_confidence:
        dbg.append(f"search:rejected confidence={match.confidence:.3f} < min={min_confidence:.3f}")
        return None, dbg

    rg = match.rg
    return (
        Normalized(
            mb_release_group_id=rg.id,
            first_release_date=rg.first_release_date or "",
            primary_type=rg.primary_type or "",
            confidence=float(match.confidence),
            source=match.method,
        ),
        dbg,
    )


def _pick_slots(items: list[Scored]) -> dict[str, Optional[Scored]]:
    if not items:
        return {"Headliner": None, "Lineage": None, "DeepCut": None}

    headliner = items[0]

    def year_key(s: Scored) -> int:
        if not s.n or not s.n.first_release_date:
            return 999999
        y = s.n.first_release_date[:4]
        return _safe_int(y, 999999)

    lineage = min(items, key=year_key)

    deepcut = None
    for s in items:
        if s is headliner or s is lineage:
            continue
        deepcut = s
        break

    return {"Headliner": headliner, "Lineage": lineage, "DeepCut": deepcut}


def run_dry_run(
    broker,
    env,
    tag: str,
    n: int = 30,
    topk: int = 10,
    split_slots: bool = False,
    mb_search_limit: int = 10,
    min_confidence: float = 0.80,
    mb_debug: bool = False,
) -> dict[str, Any]:
    if not env.lastfm_api_key:
        raise RuntimeError("Missing env LASTFM_API_KEY")
    if not env.mb_user_agent:
        raise RuntimeError("Missing env MB_USER_AGENT")

    albums: list[LastFmTopAlbum] = lastfm_tag_top_albums(broker, api_key=env.lastfm_api_key, tag=tag, limit=n)

    candidates: list[Candidate] = []
    for a in albums:
        candidates.append(
            Candidate(
                title=a.name,
                artist=a.artist,
                lastfm_mbid=a.mbid or "",
                lastfm_rank=_safe_int(a.rank, 0),
                image_url=a.image_extralarge or "",
            )
        )

    scored: list[Scored] = []
    for c in candidates:
        norm, dbg = _normalize_candidate(
            broker,
            env.mb_user_agent,
            c,
            mb_search_limit=mb_search_limit,
            min_confidence=min_confidence,
            mb_debug=mb_debug,
        )
        s, reason = _score(c, norm)
        scored.append(Scored(c=c, n=norm, score=s, reason=reason, mb_debug=dbg))

    scored.sort(key=lambda x: x.score, reverse=True)
    top = scored[:topk]

    slots = _pick_slots(top) if split_slots else {}
    return {"candidates": candidates, "scored": scored, "top": top, "slots": slots}
