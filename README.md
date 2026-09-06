# Triangulum Daily

[中文](./README.zh-CN.md)

Nine albums a day, released three at a time. Triangulum Daily is a finite music-discovery product built around a daily rhythm rather than an endless feed.

**Live site:** [triangulumdaily.space](https://triangulumdaily.space/)

## Daily rhythm

All product time uses Asia/Shanghai (BJT).

| BJT window | What is available |
| --- | ---: |
| 00:00–07:59 | Offline State |
| 08:00–12:29 | 3 albums |
| 12:30–15:59 | 6 albums |
| 16:00–23:59 | 9 albums |

Every published issue contains three slots and three picks per slot. The browser only controls the visible 0 / 3 / 6 / 9 inventory; it does not generate recommendations or ask a provider for a new issue.

## Record Shop

The canonical production UI is the **Record Shop** at `#/`.

- The **Entry Diorama** is an interactive Three.js exterior with six named preset views, bounded inspection/zoom, and a physical door.
- The door leads into the formal **Record Shop interior**, where the Daily Device opens the current inventory and the in-scene HUD exposes recent dates.
- **Today** uses the current published issue. **History** uses the published archive index and archive issue JSON in the same interior.
- The **Treatment Viewer** opens the selected published record as a modal reading layer. It does not create a detail route.
- `#/today` and `#/archive` remain supporting static-data surfaces; the Record Shop is the product landing experience.

There is no production preview catalog or independent mock Record Shop catalog. The scene maps the existing public issue contract into records; the product clock determines its visible inventory.

## Static data and covers

Triangulum Daily is a build-time generated GitHub Pages site.

```text
build-time music providers
        ↓
Python collection, normalization, selection, and enrichment
        ↓
validated today.json + archive JSON + index.json
        ↓
same-origin cover assets and manifest
        ↓
React/Vite bundle
        ↓
GitHub Pages
```

The browser reads static JSON and assets only. It has no application backend, database, account system, comments, player, marketplace, or visitor-side writes. Last.fm, MusicBrainz, Discogs, ListenBrainz, Wikipedia, Wikimedia, and Cover Art Archive remain build-time inputs rather than browser application APIs.

During a production build, usable cover sources are copied to `assets/covers/` and recorded in `assets/cover-manifest.js`. The UI resolves that same-origin mapping first and falls back locally when an image cannot be used. Direct third-party cover loading is a degraded-resource fallback, not the normal production path.

The current issue is read from `data/today.json`. Archive browsing uses `data/index.json`, then the run-specific archive JSON with its checked date alias fallback. Current issue recovery follows the application's current → last-good → archive path.

## Repository contracts

- [`tests/fixtures/product_schedule.json`](./tests/fixtures/product_schedule.json) is shared schedule evidence for the BJT windows and 3×3 issue structure.
- [`tests/fixtures/public_contract/manifest.json`](./tests/fixtures/public_contract/manifest.json) is the shared Python/TypeScript public-JSON fixture manifest.
- Published issues use the existing schema, stable roles, release-group identity, and checked archive identity.
- [`AGENTS.md`](./AGENTS.md) records the static architecture boundary, validation model, generated-artifact rules, and Git hygiene.
- [`docs/foundation/`](./docs/foundation/) describes current durable facts; [`docs/design/`](./docs/design/) is the current visual/design authority. [`docs/archive/`](./docs/archive/), [`docs/revive/`](./docs/revive/), and [`docs/legacy/`](./docs/legacy/) are historical context.

## Development and validation

Requirements:

- Python 3.11+
- Node.js `>=22 <25`
- npm
- Build-time provider credentials for a real data build

```bash
python -m venv .venv
python -m pip install -e ".[test]"
npm --prefix ui ci
```

Copy [`.env.example`](./.env.example) to `.env` for a real data build. Do not commit `.env`, `_build/`, `ui/dist/`, caches, logs, or local evidence.

Choose the smallest validation layer that matches a change:

```text
python -m pytest
npm --prefix ui test
npm --prefix ui run build
daily3albums build --verbose --out _build/public
python scripts/self_check.py --path _build/public
npm --prefix ui run browser:smoke
npm --prefix ui run browser:record-shop
npm --prefix ui run performance:audit
```

The daily production workflow is **Build and Deploy Pages (Daily)**. It restores validated published archive history, runs the normal tests/build/self-check flow, materializes cover assets, uploads the Pages artifact, and deploys it. Doctor is retired and is not a health or release command.

## Repository map

```text
daily3albums/       build-time generator, providers, contracts, and writers
ui/                 React/Vite interface, Record Shop, tests, browser checks
config/             recommendation and endpoint policies
tests/              Python tests and cross-runtime fixtures
scripts/            self-check, archive recovery, metrics, and observability
.github/workflows/  CI and daily Pages production workflow
docs/               current foundation/design docs and historical evidence
```

Made for slower listening: one day, nine albums, three at a time.
