from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from daily3albums.config import load_env, load_config
from daily3albums.request_broker import RequestBroker
from daily3albums.adapters import lastfm_tag_top_albums, musicbrainz_search_release_group
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

def _now_date_in_tz(tz_name: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.now(ZoneInfo(tz_name))
    except Exception:
        dt = datetime.now()
    return dt.date().isoformat()


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


def _pick_to_issue_item(tag: str, slot: str, s: Any) -> dict[str, Any]:
    c = s.c
    n = s.n

    rg_id = getattr(n, "mb_release_group_id", "") if n else ""
    frd = getattr(n, "first_release_date", None) if n else None
    ptype = getattr(n, "primary_type", None) if n else None
    conf = float(getattr(n, "confidence", 0.0)) if n else 0.0

    artist = getattr(c, "artist", "")
    title = getattr(c, "title", "")
    img = getattr(c, "image_url", "") or ""

    optimized_cover_url = img or "/assets/placeholder.webp"

    return {
        "slot": slot,
        "rg_mbid": rg_id,
        "title": title,
        "artist_credit": artist,
        "artist_mbids": [],
        "first_release_year": _safe_year(frd),
        "primary_type": ptype,
        "secondary_types": [],
        "tags": [{"name": tag, "source": "lastfm"}],
        "popularity": None,
        "cover": {
            "has_cover": bool(img),
            "optimized_cover_url": optimized_cover_url,
            "source_release_mbid": None,
            "original_cover_url": img or None,
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
        const res = await fetch('/data/today.json', { cache: 'no-store' });
        if (!res.ok) throw new Error('fetch /data/today.json failed: ' + res.status);
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
          img.src = (p.cover && p.cover.optimized_cover_url) ? p.cover.optimized_cover_url : '/assets/placeholder.webp';
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

    logger = print if verbose else None
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies, logger=logger)

    mb_search_limit = int(mb_search_limit)
    min_confidence = float(min_confidence)
    ambiguity_gap = float(ambiguity_gap)
    quarantine_out = (quarantine_out or "").strip() or None

    out_public_dir = (repo_root / out_dir).resolve()

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
        )

        # Assemble 3 picks
        picks_scored: list[Any] = []
        if split_slots:
            slots = out.get("slots") or {}
            for name in ("Headliner", "Lineage", "DeepCut"):
                s = slots.get(name)
                if s is None or s.n is None:
                    continue
                picks_scored.append((name, s))
        else:
            for s in out.get("top") or []:
                if getattr(s, "n", None) is None:
                    continue
                picks_scored.append(("Pick", s))
                if len(picks_scored) >= 3:
                    break

        if len(picks_scored) < 3:
            have_rg = {getattr(s.n, "mb_release_group_id", "") for _, s in picks_scored if getattr(s, "n", None)}
            for s in out.get("top") or []:
                if getattr(s, "n", None) is None:
                    continue
                rg = getattr(s.n, "mb_release_group_id", "")
                if rg and rg in have_rg:
                    continue
                picks_scored.append(("Supplement", s))
                have_rg.add(rg)
                if len(picks_scored) >= 3:
                    break

        if len(picks_scored) < 3:
            print("BUILD ERROR: cannot assemble 3 valid picks (normalized items are less than 3).")
            return 2

        slot_names = ["Headliner", "Lineage", "DeepCut"]
        scored_items = [s for _, s in picks_scored[:3]]

        date_key = (date_override or "").strip() or _now_date_in_tz(getattr(cfg, "timezone", "Asia/Shanghai"))
        run_id = f"{date_key}_{uuid.uuid4().hex[:6]}"
        theme_of_day = (theme or "").strip() or tag

        issue = {
            "output_schema_version": "1.0",
            "date": date_key,
            "run_id": run_id,
            "theme_of_day": theme_of_day,
            "lineage_source": None,
            "picks": [],
            "constraints": {"ambiguity_gap": ambiguity_gap, "min_confidence": min_confidence},
            "generation": {
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "versions": {"daily3albums": getattr(cfg, "version", None)},
            },
            "warnings": [],
        }

        issue["picks"] = [_pick_to_issue_item(tag=tag, slot=slot, s=s) for slot, s in zip(slot_names, scored_items)]

        quarantine_rows: list[dict[str, Any]] = []
        if quarantine_out:
            qpath = Path(quarantine_out)
            if not qpath.is_absolute():
                qpath = repo_root / qpath
            quarantine_rows = _read_quarantine_jsonl(qpath)

        # Copy web -> out (if exists)
        web_dir = repo_root / "web"
        out_public_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree_overwrite(web_dir, out_public_dir)

        # Ensure non-blank homepage even if web/ is empty or encoded badly
        _ensure_nonblank_index_html(out_public_dir=out_public_dir, web_dir=web_dir)

        # Write artifacts
        from daily3albums.artifact_writer import write_daily_artifacts  # type: ignore

        paths = write_daily_artifacts(issue=issue, out_public_dir=out_public_dir, quarantine_rows=quarantine_rows or None)

        print("BUILD OK")
        print(f"out={out_public_dir}")
        for k, v in paths.items():
            print(f"{k}={v}")

        # Additional hint if web/index.html is missing/empty
        web_index = web_dir / "index.html"
        if (not web_index.exists()) or web_index.stat().st_size == 0:
            print("NOTE: web/index.html is missing or empty; wrote a built-in minimal index.html into output.")
            print("      You should copy output index.html back to web/index.html to persist it.")

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
    p_build.add_argument("--tag", required=True)
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
