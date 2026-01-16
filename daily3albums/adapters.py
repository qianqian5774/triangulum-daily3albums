from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, quote_plus

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
        # 兜底：记录最后一个非空
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

    # 关键修复：兼容 topalbums 与 albums 两种返回
    container = None
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
    q = f'releasegroup:"{title}" AND artist:"{artist}"'
    params = {"query": q, "fmt": "json", "limit": str(limit)}
    url = "https://musicbrainz.org/ws/2/release-group?" + urlencode(params, quote_via=quote_plus)

    headers = {"User-Agent": mb_user_agent, "Accept": "application/json"}
    j = broker.get_json(url, headers=headers)

    rgs = (j or {}).get("release-groups") or []
    out: list[MbReleaseGroup] = []
    for rg in rgs:
        if not isinstance(rg, dict):
            continue
        rg_id = (rg.get("id") or "").strip()
        rg_title = (rg.get("title") or "").strip()

        ac = rg.get("artist-credit") or []
        names: list[str] = []
        if isinstance(ac, list):
            for x in ac:
                if isinstance(x, dict) and isinstance(x.get("name"), str):
                    names.append(x["name"])
        artist_credit = " / ".join(names) if names else artist

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
