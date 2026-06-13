# Triangulum Daily 3 Albums

[中文](README.md) | English

Triangulum Daily 3 Albums is a static site and generation system that publishes three album recommendations every day.

I started it for myself as a daily way to decide what to listen to. I wanted something that pushed against the usual recommendation loops from streaming platforms and social feeds, and surfaced albums that were less obvious, less popular, or just outside my normal listening path. Later I realized that if the project could live reliably on the web, it could also be useful for more people to open each day. This repository records the implementation used to generate, publish, and maintain the Daily 3 Albums project.

## What it does

The system generates 3 album recommendations per day and publishes them as a static website. Visitors can see the current day's albums, the Beijing-time unlock schedule, and an archive of past recommendations.

The core goals are simple:

- Recommend 3 albums each day.
- Avoid overly mainstream or overly familiar recommendation results where possible.
- Keep the daily publishing flow stable over time.
- Preserve an archive so past recommendations can be revisited.

## How it works

Daily 3 Albums has two main parts:

- Python generator: reads configuration, calls external music data sources, selects candidate albums, and writes the JSON data used by the site.
- Static frontend: reads generated data and renders the today page, archive, and album detail pages in the browser.

The daily automation roughly follows this path:

1. GitHub Actions runs once in the early Beijing morning.
2. The generator uses configuration and cache data to collect candidate albums.
3. The system selects 3 albums for the day and writes `today.json` plus archive data.
4. The frontend is built into static files.
5. GitHub Pages publishes the site from `_build/public`.

The deployed site does not depend on a running backend service. After publishing, visitors load static assets.

## Daily schedule

The site uses Beijing time, Asia/Shanghai, for its visible states:

- 00:00-05:59: the day's albums are not open yet.
- 06:00-11:59: album 1 is open.
- 12:00-17:59: album 2 is open.
- 18:00-23:59: album 3 is open.

The 06:00 / 12:00 / 18:00 transitions happen in the browser at runtime, so the site does not need a new deployment for each slot.

## Features

- 3 album recommendations per day.
- Beijing-time slot unlocks.
- Today page, archive page, and album detail pages.
- Metadata enrichment from external sources such as Last.fm and MusicBrainz.
- Local SQLite cache to reduce repeated requests and external API pressure.
- Generated-output `self_check` for today data, archive consistency, and key static artifacts.
- `doctor` command for checking configuration, environment, timezone, and basic external-service availability.
- `debug_time` parameter for local testing of time-based UI states.

## Project layout

```text
daily3albums/      Python generator and CLI
config/            Tags, data sources, and endpoint policies
scripts/           Maintenance and self-check scripts
ui/                Static frontend
docs/              Operations notes, revive logs, and audit documents
_build/public/     Local final static-site output
```

`_build/public` is the final publishing directory. Frontend development seed data and production generated data should stay separate; do not treat `ui/public/data` as production output.

## Maintainer commands

These commands are for local maintenance and verification. See `docs/runbook.md` and `docs/revive/` for fuller operational notes.

```bash
npm --prefix ui ci
npm --prefix ui test
npm --prefix ui run build
daily3albums doctor
daily3albums build --verbose --out ./_build/public
python scripts/self_check.py --path ./_build/public
```

Local preview:

```bash
python -m http.server --directory _build/public 8000
```

## debug_time

For local debugging, `debug_time` can simulate Beijing time:

```text
?debug_time=YYYY-MM-DDTHH:MM:SS
```

HashRouter builds also support:

```text
/#/?debug_time=YYYY-MM-DDTHH:MM:SS
```

It is commonly used to check 05:59 / 06:00 / 12:00 / 18:00 / cross-day states.

## Runtime notes

- Production CI uses Python 3.11. Newer local Python versions, such as 3.14, can be used for development, but they do not replace CI 3.11 verification.
- The product time model is fixed to Beijing time, Asia/Shanghai. `config.timezone` and environment variables keep local, CI, and generator behavior aligned; they do not mean the site supports a multi-timezone product mode.
- `daily3albums build` builds the UI by default and writes data into `_build/public/data`. If the UI has already been built separately, `--skip-ui-build` can reuse the existing `ui/dist`, but it should not be used where `ui/dist` is missing.
- Browsers or CDNs may cache `today.json`. Critical boundaries use cache-busting requests; if the returned data is not for the current Beijing date, the UI should enter a safe degraded state and retry.
- `require_cover: true` currently means candidates with covers are preferred. It does not mean the build must fail whenever a cover is missing. When Cover Art Archive has no cover, Last.fm artwork may be used; if no image is available, `assets/placeholder.svg` is used.

## Current status

The project is being maintained toward stable publishing and long-running unattended operation. Recent work focuses on build-chain consistency, clearer cache and API failure behavior, static-output self-checks, and eventual release on a production domain.
