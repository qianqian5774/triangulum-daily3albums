# Triangulum Daily: project guidance

These rules apply to repository work unless a task gives narrower instructions.

## Local instructions

- If `AGENTS.local.md` exists at the repository root, read it before running local commands.
- `AGENTS.local.md` is machine-local and ignored by Git. It may define absolute paths, local runtimes, sandbox behavior, and environment-specific commands.
- Local instructions must not override the static architecture boundary, security constraints, Git hygiene, generated-artifact rules, or foundation policy in this file.

## Architecture boundary

Triangulum Daily is a build-time generated static GitHub Pages site.

- The Python generator may call external music/data services before deployment.
- The deployed site serves static JSON and static assets. Visitor browsers must not call Last.fm, MusicBrainz, Discogs, ListenBrainz, Wikipedia, Wikimedia, or similar external music/data APIs as runtime application data sources.
- Remote covers, images, or fonts referenced by generated JSON or static assets are resource dependencies, not automatically runtime API violations. Record and evaluate their availability, privacy, CORS, and performance risks.
- Do not introduce a backend, database, login, comments, player service, visitor-side writes, or runtime external music API calls without explicit architecture discussion and approval.
- External probes and build-time API use must respect provider rate limits, retry/backoff policy, and sequential minimal-probe behavior where applicable.

## Product and UI terminology

- Product name: `Triangulum Daily`.
- The product publishes nine albums per natural day, split across three unlock windows with three albums each.
- `Today Page` is the current-day surface.
- `Archive Page` is the retained static-history surface.
- `Treatment Viewer` is the overlay opened from an Album Card; it is not a standalone detail route.
- `Ambient Overlay` and `Share Card` are overlays, not independent routes.
- Preserve the canonical schedule and terminology already defined in source, tests, README, and `docs/foundation/`; do not reintroduce historical `Daily 3 Albums` product copy or old unlock times.

## Validation model

Use the smallest set that fully matches the change. The active validation layers are:

1. Python unit/integration tests.
2. UI unit tests.
3. Production UI build.
4. Static-site generation followed by `scripts/self_check.py`.
5. GitHub Actions for CI and daily production build/deploy evidence.
6. Independent real Playwright browser smoke and performance audits.
7. Build Metrics and Recommendation Observability for production-generation diagnostics.

Portable command forms, assuming the repository's configured runtimes are active:

```text
python -m pytest
npm --prefix ui test
npm --prefix ui run build
daily3albums build --verbose --out _build/public
python scripts/self_check.py --path _build/public
npm --prefix ui run browser:smoke
npm --prefix ui run performance:audit
```

- Read `AGENTS.local.md` for machine-specific executable paths and environment setup.
- Run only the subset appropriate to the task. Markdown-only changes do not require a full build unless they modify executable examples or operational commands that need verification.
- Browser smoke tests require an existing `_build/public`. Performance audits are independent production probes and write ignored local evidence.
- `scripts/build_metrics.py` and `scripts/recommendation_observability_summary.py` remain active and independent of browser tests.
- Doctor is retired. Do not run, restore, or treat `daily3albums doctor`, `doctor/REPORT*`, or `doctor/runs/` as a health signal. Historical context is in `docs/legacy/doctor.md`.

## Git hygiene and generated artifacts

- Do not use `git add .` or broad staging in a mixed worktree.
- Before committing, run `git status -sb`, `git diff --stat`, and an appropriate content diff.
- Stage only explicit files belonging to the requested change. Preserve unrelated user edits.
- Do not commit generated outputs, environment files, caches, logs, credentials, API keys, or tokens, including:
  - `_build/`
  - `ui/dist/`
  - `ui/artifacts/`
  - `.state/`
  - `.venv/`
  - `.codex/`
  - cache directories and logs
- Build Metrics and Recommendation Observability source code are tracked; their transient local/runtime outputs follow the generated-artifact boundary.

## Foundation docs memory layer

- `docs/foundation/` is the ignored local, long-term project memory layer and the canonical current-state explanation for architecture, data/API boundaries, recommendation behavior, release flow, and UI terminology.
- `docs/revive/` and `docs/legacy/` are historical context, not the current authority.
- At the start of substantial work, inspect relevant foundation files when available.
- At the end of major work, explicitly decide whether foundation needs updating. Major work includes durable changes to:
  - archive/data writes
  - build, release, GitHub Actions, Pages, custom domain, or deployment behavior
  - public JSON/schema boundaries
  - recommendation generation, filtering, scoring, sampling, observability, or metadata enrichment
  - external data/API boundaries
  - UI structure, routing, layout, mobile behavior, terminology, or debug behavior
  - validated operational baselines
- Before editing foundation, create a local snapshot under `docs/foundation/_snapshots/`.
- Write verified durable facts only. Do not write wishes, temporary debugging notes, PR chronology, or unverified assumptions as implemented behavior.
- Do not commit, open PRs for, or force-add `docs/foundation/` unless the user explicitly asks.
- Foundation changes are not source-code dirt. Stash them only when technically necessary for an operation and explicitly authorized.

## Scope discipline

- Keep behavior changes, documentation changes, performance audits, and refactors within the task's stated boundary.
- Do not change recommendation logic during observability-only work.
- Do not rewrite UI during audit-only performance work.
- Prefer small, reviewable changes backed by tests or recorded evidence.
- When facts differ between documentation and current source/config/workflows, verify the implementation first, then update the appropriate canonical documentation.
