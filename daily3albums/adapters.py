# daily3albums/adapters.py
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlencode, quote_plus
import re
import unicodedata

from daily3albums.request_broker import RequestBroker


def _ensure_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return [x]
    return []


def _pick_lastfm_image(images: Any, prefer_size: str = "extralarge") -> str | None:
    # Last.fm 常见结构：image: [{"#text": "...", "size":"small"}, ...]
    if not isinstance(images, list):
        return None
    best = None
    for it in images:
        if not isinstance(it, dict):
            continue
        url = (it.get("#text") or "").strip()
        size = (it.get("size") or "").strip()
        if not url:
            continue
        if size == prefer_size:
            return url
        best = url
    return best


@dataclass
class LastFmTopAlbum:
    name: str
    artist: str
    mbid: str | None
    playcount: int | None
    url: str | None
    rank: int | None
    image_extralarge: str | None


def lastfm_tag_top_albums(
    broker: RequestBroker,
    api_key: str,
    tag: str,
    limit: int = 30,
    page: int = 1,
) -> list[LastFmTopAlbum]:
    params = {
        "method": "tag.getTopAlbums",
        "tag": tag,
        "limit": str(limit),
        "page": str(page),
        "api_key": api_key,
        "format": "json",
    }
    url = "https://ws.audioscrobbler.com/2.0/?" + urlencode(params)
    j = broker.get_json(url)

    # Last.fm 错误会以 JSON 返回：{"error":..., "message":...}
    if isinstance(j, dict) and "error" in j:
        raise RuntimeError(f"Last.fm error={j.get('error')} message={j.get('message')}")

    if not isinstance(j, dict):
        return []

    # 兼容 topalbums 与 albums 两种返回
    if isinstance(j.get("topalbums"), dict):
        container = j["topalbums"]
    elif isinstance(j.get("albums"), dict):
        container = j["albums"]
    else:
        container = {}

    albums = _ensure_list(container.get("album"))

    out: list[LastFmTopAlbum] = []
    for a in albums:
        if not isinstance(a, dict):
            continue

        name = (a.get("name") or "").strip()
        artist_obj = a.get("artist")
        if isinstance(artist_obj, dict):
            artist = (artist_obj.get("name") or "").strip()
        else:
            artist = (a.get("artist") or "").strip() if isinstance(a.get("artist"), str) else ""

        if not name or not artist:
            continue

        mbid = (a.get("mbid") or "").strip() or None

        pc_raw = a.get("playcount")
        playcount = None
        if isinstance(pc_raw, str) and pc_raw.isdigit():
            playcount = int(pc_raw)
        elif isinstance(pc_raw, int):
            playcount = pc_raw

        rank = None
        attr = a.get("@attr")
        if isinstance(attr, dict):
            r = attr.get("rank")
            if isinstance(r, str) and r.isdigit():
                rank = int(r)
            elif isinstance(r, int):
                rank = r

        image_extralarge = _pick_lastfm_image(a.get("image"))

        out.append(
            LastFmTopAlbum(
                name=name,
                artist=artist,
                mbid=mbid,
                playcount=playcount,
                url=(a.get("url") or None),
                rank=rank,
                image_extralarge=image_extralarge,
            )
        )

    return out


# -----------------------------
# MusicBrainz: core structures
# -----------------------------


@dataclass
class MbReleaseGroup:
    id: str
    title: str
    artist_credit: str
    first_release_date: str | None
    primary_type: str | None
    secondary_types: list[str]


def musicbrainz_search_release_group(
    broker: RequestBroker,
    mb_user_agent: str,
    title: str,
    artist: str,
    limit: int = 5,
) -> list[MbReleaseGroup]:
    """
    保留原有严格搜索接口（probe-mb 也依赖它）。
    """
    q = f'releasegroup:"{title}" AND artist:"{artist}"'
    return musicbrainz_search_release_group_by_query(broker, mb_user_agent=mb_user_agent, query=q, limit=limit)


def musicbrainz_search_release_group_by_query(
    broker: RequestBroker,
    mb_user_agent: str,
    query: str,
    limit: int = 10,
) -> list[MbReleaseGroup]:
    params = {"query": query, "fmt": "json", "limit": str(limit)}
    url = "https://musicbrainz.org/ws/2/release-group?" + urlencode(params, quote_via=quote_plus)
    headers = {"User-Agent": mb_user_agent, "Accept": "application/json"}
    j = broker.get_json(url, headers=headers)

    rgs = (j or {}).get("release-groups") or []
    out: list[MbReleaseGroup] = []
    for rg in rgs:
        if not isinstance(rg, dict):
            continue
        rg_id = (rg.get("id") or "").strip()
        if not rg_id:
            continue
        rg_title = (rg.get("title") or "").strip()

        # MusicBrainz search results sometimes include only "artist-credit-phrase".
        ac_phrase = rg.get("artist-credit-phrase")
        artist_credit = (ac_phrase or "").strip() if isinstance(ac_phrase, str) else ""
        if not artist_credit:
            ac = rg.get("artist-credit") or []
            names: list[str] = []
            if isinstance(ac, list):
                for x in ac:
                    if not isinstance(x, dict):
                        continue
                    # 常见：{"name": "Brian Eno", "artist": {...}}
                    if isinstance(x.get("name"), str) and x.get("name"):
                        names.append(x["name"])
                        continue
                    # 兜底：{"artist": {"name": "Brian Eno", ...}}
                    art = x.get("artist")
                    if isinstance(art, dict) and isinstance(art.get("name"), str) and art.get("name"):
                        names.append(art["name"])
            artist_credit = " / ".join(names) if names else ""

        out.append(
            MbReleaseGroup(
                id=rg_id,
                title=rg_title,
                artist_credit=artist_credit,
                first_release_date=rg.get("first-release-date") or None,
                primary_type=rg.get("primary-type") or None,
                secondary_types=list(rg.get("secondary-types") or []),
            )
        )
    return out


@dataclass
class MbReleaseGroupSummary:
    id: str
    first_release_date: str | None
    primary_type: str | None


def musicbrainz_get_release_group(
    broker: RequestBroker,
    mb_user_agent: str,
    rg_id: str,
) -> MbReleaseGroupSummary | None:
    """
    通过 release-group id 直接获取 release-group。
    成功返回 (id / first-release-date / primary-type)，失败返回 None。
    """
    rg_id = (rg_id or "").strip()
    if not rg_id:
        return None

    url = f"https://musicbrainz.org/ws/2/release-group/{rg_id}?fmt=json"
    headers = {"User-Agent": mb_user_agent, "Accept": "application/json"}
    try:
        j = broker.get_json(url, headers=headers)
    except Exception:
        return None

    if not isinstance(j, dict):
        return None
    got_id = (j.get("id") or "").strip()
    if not got_id:
        return None

    return MbReleaseGroupSummary(
        id=got_id,
        first_release_date=j.get("first-release-date") or None,
        primary_type=j.get("primary-type") or None,
    )


def musicbrainz_get_release_group_debug(
    broker: RequestBroker,
    mb_user_agent: str,
    rg_id: str,
) -> tuple[MbReleaseGroupSummary | None, str]:
    """
    Debug 版本：返回 (summary_or_none, status_str)。
    status_str 主要用于 dry-run --mb-debug 的可解释输出。
    """
    rg_id = (rg_id or "").strip()
    if not rg_id:
        return None, "rg:skip-empty"

    url = f"https://musicbrainz.org/ws/2/release-group/{rg_id}?fmt=json"
    headers = {"User-Agent": mb_user_agent, "Accept": "application/json"}
    try:
        j = broker.get_json(url, headers=headers)
    except Exception as e:
        return None, f"rg:error:{type(e).__name__}"

    if not isinstance(j, dict):
        return None, "rg:bad-json"

    got_id = (j.get("id") or "").strip()
    if not got_id:
        # 这通常意味着不是 rg endpoint 返回的结构
        return None, "rg:missing-id"

    return (
        MbReleaseGroupSummary(
            id=got_id,
            first_release_date=j.get("first-release-date") or None,
            primary_type=j.get("primary-type") or None,
        ),
        "rg:ok",
    )


@dataclass
class MbReleaseSummary:
    id: str
    release_group_id: str | None


def musicbrainz_get_release(
    broker: RequestBroker,
    mb_user_agent: str,
    release_id: str,
) -> MbReleaseSummary | None:
    """
    通过 release id 获取 release，并取出 release-group id。
    成功返回 (release_id / release_group_id)，失败返回 None。
    """
    release_id = (release_id or "").strip()
    if not release_id:
        return None

    url = f"https://musicbrainz.org/ws/2/release/{release_id}?fmt=json"
    headers = {"User-Agent": mb_user_agent, "Accept": "application/json"}
    try:
        j = broker.get_json(url, headers=headers)
    except Exception:
        return None

    if not isinstance(j, dict):
        return None
    got_id = (j.get("id") or "").strip()
    if not got_id:
        return None

    rg = j.get("release-group") or {}
    rg_id = (rg.get("id") or "").strip() or None
    return MbReleaseSummary(id=got_id, release_group_id=rg_id)


def musicbrainz_get_release_debug(
    broker: RequestBroker,
    mb_user_agent: str,
    release_id: str,
) -> tuple[MbReleaseSummary | None, str]:
    """Debug 版本：返回 (summary_or_none, status_str)。"""
    release_id = (release_id or "").strip()
    if not release_id:
        return None, "rel:skip-empty"

    url = f"https://musicbrainz.org/ws/2/release/{release_id}?fmt=json"
    headers = {"User-Agent": mb_user_agent, "Accept": "application/json"}
    try:
        j = broker.get_json(url, headers=headers)
    except Exception as e:
        return None, f"rel:error:{type(e).__name__}"

    if not isinstance(j, dict):
        return None, "rel:bad-json"

    got_id = (j.get("id") or "").strip()
    if not got_id:
        return None, "rel:missing-id"

    rg = j.get("release-group") or {}
    rg_id = (rg.get("id") or "").strip() or None
    if not rg_id:
        return MbReleaseSummary(id=got_id, release_group_id=None), "rel:ok-no-rg"

    return MbReleaseSummary(id=got_id, release_group_id=rg_id), "rel:ok"


def musicbrainz_normalize_mbid_to_release_group(
    broker: RequestBroker,
    mb_user_agent: str,
    mbid: str,
) -> tuple[MbReleaseGroupSummary | None, str]:
    """
    输入：mbid（可能是 release-group，也可能是 release）
    输出：(release_group_summary_or_none, source)

    source:
      - "mbid:release-group"  直接命中 release-group
      - "mbid:release->rg"    mbid 是 release，通过 release-group 归一
      - "mbid:miss"           两条路都失败
    """
    mbid = (mbid or "").strip()
    if not mbid:
        return None, "mbid:miss"

    # 1) 先把 mbid 当作 release-group 试一遍
    rg = musicbrainz_get_release_group(broker, mb_user_agent=mb_user_agent, rg_id=mbid)
    if rg is not None:
        return rg, "mbid:release-group"

    # 2) 再把 mbid 当作 release，取出 release-group 再查 rg
    rel = musicbrainz_get_release(broker, mb_user_agent=mb_user_agent, release_id=mbid)
    if rel is None or not rel.release_group_id:
        return None, "mbid:miss"

    rg2 = musicbrainz_get_release_group(broker, mb_user_agent=mb_user_agent, rg_id=rel.release_group_id)
    if rg2 is not None:
        return rg2, "mbid:release->rg"

    return None, "mbid:miss"


def musicbrainz_normalize_mbid_to_release_group_debug(
    broker: RequestBroker,
    mb_user_agent: str,
    mbid: str,
) -> tuple[MbReleaseGroupSummary | None, str, list[str]]:
    """
    Debug 版本：返回 (rg_summary_or_none, source, debug_lines)。
    目的：让你在 dry-run --mb-debug 时明确看到 mbid 路径到底卡在哪一步。
    """
    dbg: list[str] = []
    mbid = (mbid or "").strip()
    if not mbid:
        return None, "mbid:miss", ["mbid:skip-empty"]

    rg, rg_status = musicbrainz_get_release_group_debug(broker, mb_user_agent=mb_user_agent, rg_id=mbid)
    dbg.append(f"mbid_try_rg status={rg_status}")
    if rg is not None and rg_status == "rg:ok":
        return rg, "mbid:release-group", dbg

    rel, rel_status = musicbrainz_get_release_debug(broker, mb_user_agent=mb_user_agent, release_id=mbid)
    dbg.append(f"mbid_try_release status={rel_status}")
    if rel is None or not rel.release_group_id:
        return None, "mbid:miss", dbg

    rg2, rg2_status = musicbrainz_get_release_group_debug(
        broker, mb_user_agent=mb_user_agent, rg_id=rel.release_group_id
    )
    dbg.append(f"release_group_from_release status={rg2_status}")
    if rg2 is not None and rg2_status == "rg:ok":
        return rg2, "mbid:release->rg", dbg

    return None, "mbid:miss", dbg


# -----------------------------
# MusicBrainz: safer fallback search (clean + relaxed + scoring)
# -----------------------------


def _mb_norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", (s or "")).lower().strip()
    s = re.sub(r"[\u200b-\u200f]", "", s)
    s = re.sub(r"[’']", "", s)
    # 保留：拉丁字母/数字/扩展拉丁、日文、中文；其余都当成空格
    s = re.sub(r"[^a-z0-9\u00c0-\u024f\u3040-\u30ff\u4e00-\u9fff]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clean_title(title: str) -> str:
    t = unicodedata.normalize("NFKC", (title or "")).strip()
    # 去掉末尾括号/方括号/花括号信息 (Remaster, Deluxe... 常见)
    t = re.sub(r"\s*[\(\[\{].*?[\)\]\}]\s*$", "", t).strip()
    # 去掉常见尾缀词（不追求全覆盖，只要稳定）
    t = re.sub(r"\b(remaster(ed)?|deluxe|expanded|edition|anniversary|reissue|bonus)\b", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _clean_artist(artist: str) -> str:
    a = unicodedata.normalize("NFKC", (artist or "")).strip()
    # 去掉 feat/ft 等后缀
    a = re.split(r"\s+(feat\.|featuring|ft\.)\s+", a, maxsplit=1, flags=re.I)[0].strip()
    a = re.sub(r"\s+", " ", a).strip()
    return a


def _ratio(a: str, b: str) -> float:
    a2 = _mb_norm_text(a)
    b2 = _mb_norm_text(b)
    if not a2 or not b2:
        return 0.0
    return SequenceMatcher(None, a2, b2).ratio()


@dataclass
class MbBestMatch:
    rg: MbReleaseGroup
    confidence: float
    method: str
    query: str
    title_sim: float
    artist_sim: float
    note: str


def _score_release_group_candidate(
    clean_title: str,
    clean_artist: str,
    rg: MbReleaseGroup,
) -> tuple[float, float, float, str]:
    title_sim = _ratio(clean_title, rg.title)
    rg_artist = rg.artist_credit or ""
    artist_sim = _ratio(clean_artist, rg_artist) if rg_artist else 0.0

    conf = 0.72 * title_sim + 0.28 * artist_sim
    note_parts: list[str] = []

    pt = (rg.primary_type or "").lower()
    if pt == "album":
        conf += 0.05
        note_parts.append("pt:album:+0.05")
    elif pt in ("ep", "single"):
        conf -= 0.10
        note_parts.append(f"pt:{pt}:-0.10")

    st = {x.lower() for x in (rg.secondary_types or [])}
    if "compilation" in st:
        conf -= 0.12
        note_parts.append("st:compilation:-0.12")
    if "live" in st:
        conf -= 0.08
        note_parts.append("st:live:-0.08")
    if "remix" in st:
        conf -= 0.06
        note_parts.append("st:remix:-0.06")

    return conf, title_sim, artist_sim, ",".join(note_parts)


def musicbrainz_best_release_group_match(
    broker: RequestBroker,
    mb_user_agent: str,
    title: str,
    artist: str,
    limit: int = 10,
) -> MbBestMatch | None:
    best, _runner_up_conf, _ = musicbrainz_best_release_group_match_debug(
        broker, mb_user_agent=mb_user_agent, title=title, artist=artist, limit=limit
    )
    return best


def musicbrainz_best_release_group_match_debug(
    broker: RequestBroker,
    mb_user_agent: str,
    title: str,
    artist: str,
    limit: int = 10,
) -> tuple[MbBestMatch | None, float | None, list[str]]:
    """
    兜底：当没有可用 mbid 时，用文本搜索并做“最像的”选择。
    原则：宁可返回 None，也不要误配。
    返回：(best_match_or_none, runner_up_conf_or_none, debug_lines)

    runner_up_conf 用于“歧义护栏”：best 和第二名太接近时，直接拒绝。
    """
    raw_title = (title or "").strip()
    raw_artist = (artist or "").strip()
    dbg: list[str] = []
    if not raw_title or not raw_artist:
        return None, None, ["skip:missing_title_or_artist"]

    clean_title = _clean_title(raw_title)
    clean_artist = _clean_artist(raw_artist)

    if len(_mb_norm_text(clean_title)) < 3:
        return None, None, ["skip:title_too_short"]

    attempts: list[tuple[str, str]] = [
        ("search:strict", f'releasegroup:"{raw_title}" AND artist:"{raw_artist}"'),
        ("search:clean_strict", f'releasegroup:"{clean_title}" AND artist:"{clean_artist}"'),
        ("search:clean_loose", f"releasegroup:{clean_title} AND artist:{clean_artist}"),
        ("search:title_only", f"releasegroup:{clean_title}"),
    ]

    top1: MbBestMatch | None = None
    top2: MbBestMatch | None = None

    def _push_top2(cand: MbBestMatch) -> None:
        nonlocal top1, top2

        # 关键：同一个 release-group 被不同 query 命中多次时，只保留分数最高的一次
        if top1 is not None and cand.rg.id == top1.rg.id:
            if cand.confidence > top1.confidence:
                top1 = cand
            return
        if top2 is not None and cand.rg.id == top2.rg.id:
            if cand.confidence > top2.confidence:
                top2 = cand
            return

        if top1 is None:
            top1 = cand
            return

        if cand.confidence > top1.confidence:
            # 新第一名上位：原第一名如果和新第一名不是同一个 id，才下放为第二名
            prev = top1
            top1 = cand
            if prev.rg.id != top1.rg.id:
                top2 = prev
            return

        if top2 is None:
            top2 = cand
            return

        if cand.confidence > top2.confidence:
            top2 = cand

    for method, q in attempts:
        rgs = musicbrainz_search_release_group_by_query(broker, mb_user_agent=mb_user_agent, query=q, limit=limit)
        dbg.append(f"{method}:results={len(rgs)} query={q}")
        if not rgs:
            continue

        for rg in rgs[: min(len(rgs), 10)]:
            conf, title_sim, artist_sim, note = _score_release_group_candidate(clean_title, clean_artist, rg)

            if title_sim < 0.60:
                continue

            if method == "search:title_only":
                # 最危险的路径：抬高门槛，防止同名误配
                if artist_sim < 0.62:
                    continue
                if conf < 0.88:
                    continue
            else:
                if artist_sim < 0.50:
                    continue

            cand = MbBestMatch(
                rg=rg,
                confidence=conf,
                method=method,
                query=q,
                title_sim=title_sim,
                artist_sim=artist_sim,
                note=note,
            )
            _push_top2(cand)

        if top1 is not None:
            runner_conf = top2.confidence if top2 is not None else None
            dbg.append(
                f"best@{method}: conf={top1.confidence:.3f} runner={runner_conf if runner_conf is not None else 'none'} "
                f"title_sim={top1.title_sim:.3f} artist_sim={top1.artist_sim:.3f} "
                f"pt={top1.rg.primary_type or ''} st={','.join(top1.rg.secondary_types or [])}"
            )
            if top1.confidence >= 0.92:
                break

    if top1 is None:
        dbg.append("final:none")
        return None, None, dbg

    runner_up_conf = top2.confidence if (top2 is not None and top2.rg.id != top1.rg.id) else None
    dbg.append(f"final:conf={top1.confidence:.3f} runner={runner_up_conf if runner_up_conf is not None else 'none'} via={top1.method} note={top1.note}")
    return top1, runner_up_conf, dbg
