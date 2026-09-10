# Data sources and API boundaries

Triangulum Daily is a build-time generated GitHub Pages site. The deployed browser reads static JSON and static assets; it does not create daily recommendations or call music-data APIs as application backends.

## Static architecture

The Python generator collects candidates, normalizes and enriches them, validates an issue, writes static artifacts, and copies the built UI into `_build/public`. GitHub Actions uploads that directory as the Pages artifact.

The visitor-facing data path is:

```text
same-origin static JSON and assets
  ├─ data/today.json
  ├─ data/index.json
  ├─ data/archive/{date}/{run_id}.json
  ├─ data/archive/{date}.json (checked alias fallback)
  ├─ assets/cover-manifest.js
  └─ assets/covers/* or assets/placeholder.svg
```

The browser has no backend, database, login, comments, user account, player service, marketplace, or visitor-side write path.

## Record Shop data consumption

The Record Shop adapts the same published `TodayIssue` contract used by the rest of the UI. `today.json` supplies the current inventory; `index.json` and archive JSON supply the interior recent-date history. Current-issue recovery follows the application's validated current → last-good → archive path. The UI must not substitute a `previewRecordShopCatalog`, an independent mock catalog, or browser-generated picks.

The BJT clock determines whether the canonical current issue exposes 0, 3, 6, or 9 records. Archive issues are complete published issues and are rendered as history rather than future locked inventory.

## External services

External providers remain build-time inputs only:

- **Last.fm** supplies required candidate discovery.
- **MusicBrainz** supplies release-group normalization and metadata enrichment.
- **Discogs** and **ListenBrainz** are optional candidate paths when enabled and configured.
- **Wikipedia** can provide build-time overview enrichment when an eligible MusicBrainz relation exists.
- **Cover Art Archive** and candidate image URLs are build-time cover sources.

The deployed application must not request Last.fm, MusicBrainz, Discogs, ListenBrainz, Wikipedia, Wikimedia, or comparable music/data APIs for application data. Provider calls use the build-time request broker, its endpoint policy, rate limit, cache, retry/backoff, and redacted diagnostics.

## Same-origin cover materialization

Published pick JSON preserves its cover metadata, including a normalized remote source URL. During a production build, `materialize_static_cover_assets()` scans the generated public JSON, retrieves usable raster covers once, and writes:

- copied images under `assets/covers/`;
- `assets/cover-manifest.js`, mapping each normalized remote source URL to that local file.

`resolveCoverUrl()` uses the manifest before assigning an image URL, so ordinary production rendering uses Pages-hosted cover files. The browser also has the local `assets/placeholder.svg` fallback. If materialization cannot obtain a particular image, the missing map entry is handled as a degraded resource and the existing image-failure fallback remains responsible for a usable UI; direct third-party cover loading is not the normal production architecture.

## Public and private boundaries

Public artifacts may contain the published issue, archive/history metadata, build metadata, and recommendation observability. They must never contain credentials, provider tokens, `.env` values, cache rows, private logs, or deployment secrets.

`.state/cache.sqlite`, provider caches, runtime logs, generated `_build/`, and `ui/dist/` are build artifacts, not source data to commit.

## Source basis

Verified from source: `daily3albums/cli.py`, `daily3albums/cover_assets.py`, `daily3albums/artifact_writer.py`, `daily3albums/request_broker.py`, `config/endpoint_policies.yaml`, `ui/src/lib/data.ts`, `ui/src/lib/archive.ts`, `ui/src/lib/covers.ts`, `ui/src/components/record-shop/catalog.ts`, and `.github/workflows/pages_daily.yml`.
