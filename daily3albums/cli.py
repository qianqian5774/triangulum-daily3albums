from __future__ import annotations
import argparse
import json
from pathlib import Path

from daily3albums.config import load_env, load_config
from daily3albums.request_broker import RequestBroker
from daily3albums.adapters import lastfm_tag_top_albums, musicbrainz_search_release_group


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
            # 直接拉原始 JSON（用于定位为什么 albums 为空）
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
            j = broker.get_json(url)
            print(json.dumps(j, ensure_ascii=False, indent=2))
            return 0

        albums = lastfm_tag_top_albums(broker, api_key=env.lastfm_api_key, tag=tag, limit=limit)
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

    args = p.parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.cmd == "doctor":
        raise SystemExit(cmd_doctor(repo_root))
    if args.cmd == "probe-lastfm":
        raise SystemExit(cmd_probe_lastfm(repo_root, tag=args.tag, limit=args.limit, verbose=args.verbose, raw=args.raw))
    if args.cmd == "probe-mb":
        raise SystemExit(cmd_probe_mb(repo_root, artist=args.artist, title=args.title, limit=args.limit, verbose=args.verbose))

    raise SystemExit(2)


if __name__ == "__main__":
    main()
