# Triangulum Daily

English | [Chinese](./README.zh-CN.md)

Nine albums a day. Three release windows, three albums at a time. No endless feed or chart-chasing—just a few daily openings into somewhere less familiar.

**Live site:** [triangulumdaily.space](https://triangulumdaily.space/)

## What it is

Triangulum Daily is a music-discovery product built around a finite daily rhythm. It publishes nine albums each Beijing-time day, split across three windows:

| Time (BJT) | What opens |
| --- | --- |
| 00:00–07:59 | Offline State |
| 08:00 | First window: three albums |
| 12:30 | Second window: three albums |
| 16:00 | Third window: three albums |

The limit is the point. Triangulum Daily does not try to become an infinite catalogue or continuously predict the next click. It offers a small set of records, leaves room to listen, and keeps the recent issues in an archive.

The public experience includes:

- **Today Page** — the current issue, progressively revealed in three windows.
- **Treatment Viewer** — the album overlay opened from an Album Card; it is not a separate detail route.
- **Archive Page** — retained daily issues loaded from static archive files.
- **Share Card** — an image based only on the windows revealed so far.
- **Ambient Overlay** — an immersive or standby view.

## A running static product

This repository is the source of the production site, not a one-off data export. A scheduled GitHub Actions workflow rebuilds and deploys it every day. The latest published archive is restored before generation so recommendation history survives stateless runners.

```text
build-time music sources
        ↓
Python candidate collection, normalization, selection, and enrichment
        ↓
validated today.json + seven-date static archive + build evidence
        ↓
React/Vite production bundle
        ↓
GitHub Pages
```

The deployed site has no application backend, database, account system, or visitor-side write path. Browsers read versioned static JSON and assets; external music services are used by the build-time generator, not as runtime application APIs.

### Daily generation and recommendation safeguards

The generator draws candidate data from configured Last.fm, Discogs, and ListenBrainz adapters, normalizes album identity against MusicBrainz release groups, enriches available metadata and cover links, and selects three roles for each window: `Headliner`, `Lineage`, and `DeepCut`.

Recommendation behavior is bounded and observable:

- A versioned normalization policy separates strict matches, documented borderline cases, and hard rejects.
- The normal policy prevents same-day artist duplication and applies seven-day album and artist cooldowns plus a three-day theme cooldown.
- When a slot cannot be filled, staged fallback is explicit: one extra candidate page, a documented artist-cooldown relaxation, and finally at most one daily pick from the four-to-seven-day album window. The three-day album and artist floor remains in force, and hard-rejected identity matches are never admitted.
- Provider calls go through a broker with per-service rate limits, bounded retries, backoff, cache handling, stable error outcomes, and redacted diagnostic URLs.
- Build Metrics and Recommendation Observability record the candidate funnel, rejection reasons, provider outcomes, fallback use, enrichment coverage, and release timing without turning the browser into a telemetry client.

The active policy lives in [`config/config.yaml`](./config/config.yaml), while provider behavior is defined by [`config/endpoint_policies.yaml`](./config/endpoint_policies.yaml). The implementation and tests remain the final authority.

### Static archive and recovery

The current retention contract is seven unique dates. Generation writes a run-specific archive and a byte-identical date alias, validates the public issue, then updates the archive index atomically. A successfully published issue for the same date is reused unless an explicit recovery operation authorizes a rewrite.

The daily workflow restores archive history from the published site before selection. Recovery tooling validates the index, issue identity, schema, and alias bytes and preserves the last good seed if a refresh is invalid. This history is used by the recommendation cooldowns as well as by the Archive Page.

## Repository contracts

Several small contracts keep the generator, static artifacts, browser, and maintenance workflow aligned:

- [`tests/fixtures/product_schedule.json`](./tests/fixtures/product_schedule.json) is shared schedule evidence for the BJT offline period, three unlock times, three slots, three picks per slot, and Share Card reveal states.
- [`tests/fixtures/public_contract/manifest.json`](./tests/fixtures/public_contract/manifest.json) defines shared current and legacy JSON cases for Python and TypeScript.
- Current Today and archive documents use schema `1.0`, exactly three slots and three picks per slot, stable role values, release-group MBIDs, and checked archive identity.
- [`AGENTS.md`](./AGENTS.md) records the static-architecture boundary, product terminology, validation layers, generated-artifact rules, and Git hygiene used during agent-assisted work.
- [`docs/foundation/`](./docs/foundation/) explains durable architecture and operating decisions; [`docs/revive/`](./docs/revive/) and [`docs/legacy/`](./docs/legacy/) retain historical context without replacing current source and tests.

These are repository contracts rather than aspirations: changes that cross them are expected to update implementation, fixtures, tests, and durable documentation together.

## Testing, release checks, and observability

The repository uses the existing product surfaces as separate validation layers:

| Layer | What it checks |
| --- | --- |
| Python `pytest` suite | configuration, provider behavior, normalization, cooldown and fallback, archive writes/recovery, public contracts, observability, and release-SLA logic |
| Vitest UI suite | schedule calculations, strict static-data parsing, Today recovery state, viewer/share behavior, paths, and component policies |
| Production UI build | TypeScript and Vite production output |
| Static build + `self_check.py` | generated site structure, public JSON, archive identity, and required assets |
| Playwright checks | real-browser mobile, Today-state, viewer-cover, product-clock, record-shop, visual, and smoke scenarios |
| Performance audit | recorded production baselines and regression budgets for Today, Archive, Treatment Viewer, Ambient, and Share surfaces |

CI runs Python and UI tests on pushes and pull requests. The daily Pages workflow repeats those gates, restores archive history, builds the production site, runs the static self-check, publishes sanitized normalization evidence, summarizes build/recommendation metrics, deploys Pages, and reports whether publication met the 08:00 BJT release target. A failed scheduled build can open a repository issue with the run link.

The performance harness and its measured limits are documented in [`PERFORMANCE.md`](./PERFORMANCE.md). Day-to-day recovery commands live in [`docs/runbook.md`](./docs/runbook.md).

## Local development

Requirements:

- Python 3.11 or newer
- Node.js `>=22 <25`
- npm
- A Last.fm API key and a MusicBrainz user agent for a real data build; a Discogs token is optional

Install the project and UI dependencies:

```bash
python -m venv .venv
python -m pip install -e ".[test]"
npm --prefix ui ci
```

Copy [`.env.example`](./.env.example) to `.env` and supply build-time provider credentials. Do not commit `.env` or generated output.

Useful validation commands:

```bash
python -m pytest
npm --prefix ui test
npm --prefix ui run build
daily3albums build --verbose --out _build/public
python scripts/self_check.py --path _build/public
npm --prefix ui run browser:smoke
npm --prefix ui run performance:audit
```

Choose the smallest layer that matches the change. Browser smoke requires an existing `_build/public`; the performance audit probes the configured production site and writes ignored local evidence. `_build/`, `ui/dist/`, caches, logs, and local evidence are generated artifacts and are not committed.

### Repository map

```text
daily3albums/       Python generator, adapters, contracts, and artifact writer
ui/                 React/Vite interface, unit tests, and browser checks
config/             recommendation and endpoint policies
tests/              Python tests and cross-runtime fixtures
scripts/            self-check, recovery, metrics, observability, and audit tools
.github/workflows/  CI and scheduled Pages production workflow
docs/               runbooks, durable foundation docs, and historical evidence
```

The technical package and repository retain the historical `daily3albums` / `triangulum-daily3albums` names even though the product is now called Triangulum Daily.

## Agent-assisted maintenance

Codex is part of the maintenance workflow, but repository evidence remains the authority. I use it to inspect unfamiliar code paths, trace production failures, review diffs, write or extend tests, compare implementation with contracts, and keep operational documentation current. [`AGENTS.md`](./AGENTS.md) constrains that work: preserve the static architecture unless a change is explicitly discussed, protect unrelated worktree changes, avoid committing generated output, and validate in proportion to risk.

Product and editorial decisions are not delegated to an agent. Recommendation rules, release windows, recovery behavior, data boundaries, and interaction direction are maintainer decisions; generated changes are read, tested, revised, and committed through the same repository workflow as other work.

## Why I keep building this

Triangulum Daily began with curiosity: would receiving only a few records each day be more interesting than another endless recommendation feed? My work and long-term experience are in content, music, research, interviewing, and editing, not a traditional software-engineering path. I would not previously have assumed that independently maintaining a software product was a realistic thing for me to do.

Building it has meant deciding what the product actually is: why the day has three windows, how recommendation and fallback should behave, how data and archive history are organized, what recovery means after a failed build, and what kind of attention the interface should ask from a listener. I am also reworking the UI and interaction system through references, interaction sketches, and implementation studies around physical-record browsing, turning, revealing, spacing, and motion.

Codex matters here because it lets me learn inside the actual maintenance loop: read code, understand a failure, change a design, inspect the result, find mistakes, and continue. There is still a great deal I have to understand and decide one piece at a time, but work that once sat in the category of “I probably cannot build that” now exists as running software I can maintain.

The project did not begin as a fork, tutorial exercise, or UI clone. Its product concept, recommendation system, and interaction direction have developed from the questions inside Triangulum Daily itself.

---

Made for slower listening.

One day, nine albums. Three at a time.
