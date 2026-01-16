# daily3albums/cli.py
from __future__ import annotations

import argparse
import json
from pathlib import Path

from daily3albums.config import load_env, load_config
from daily3albums.request_broker import RequestBroker
from daily3albums.adapters import lastfm_tag_top_albums, musicbrainz_search_release_group
from daily3albums.dry_run import run_dry_run


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


def cmd_dry_run(
    repo_root: Path,
    tag: str,
    n: int,
    topk: int,
    verbose: bool,
    split_slots: bool,
    mb_search_limit: int,
    min_confidence: float,
    mb_debug: bool,
) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)
    mb_search_limit = int(mb_search_limit)
    min_confidence = float(min_confidence)

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
            mb_debug=mb_debug,
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

    p_dry = sub.add_parser("dry-run", help="Dry run: lastfm candidates -> mb normalize -> score -> topN")
    p_dry.add_argument("--tag", required=True)
    p_dry.add_argument("--n", type=int, default=30)
    p_dry.add_argument("--topk", type=int, default=10)
    p_dry.add_argument("--split-slots", action="store_true")
    p_dry.add_argument("--verbose", action="store_true")
    p_dry.add_argument("--mb-search-limit", type=int, default=10)
    p_dry.add_argument("--min-confidence", type=float, default=0.80)
    p_dry.add_argument("--mb-debug", action="store_true", help="Print MB matching attempts for each candidate")

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
                mb_debug=args.mb_debug,
            )
        )

    raise SystemExit(2)


if __name__ == "__main__":
    main()
