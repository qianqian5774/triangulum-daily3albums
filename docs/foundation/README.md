# Triangulum Daily Foundation

`docs/foundation/` records the durable, source-verified facts needed to maintain the current product. It is not a release diary, a visual-review log, or an archive of exploratory prompts.

The canonical visitor experience is the Record Shop at `#/`: an interactive Entry Diorama leads through a physical door into the Record Shop interior. The generator, public JSON contract, and GitHub Pages deployment remain static and build-time driven.

## Current documents

- [UI terminology](./ui-terminology.md) defines the production surfaces, their relationship, routing, data terminology, and BJT product clock.
- [Data sources and API boundaries](./data-sources-and-api-boundaries.md) defines the static-data boundary, public artifacts, same-origin cover materialization, and provider limits.
- [Recommendation system](./recommendation-system.md) records the recommendation implementation and the way its published output is consumed by the UI. It does not authorize a scoring change.
- [Daily build and release pipeline](./daily-build-and-release-pipeline.md) records the release workflow, archive recovery, validation gates, and Pages deployment.

## Authority and history

When a Foundation document conflicts with current source, configuration, tests, workflow, or an inspected production deployment, the implementation evidence wins and this directory must be corrected.

`docs/design/` is the current design authority. Its formal documents explain the approved spatial and interaction model; they do not override runtime data, archive, or deployment behavior.

`docs/archive/`, `docs/revive/`, and `docs/legacy/` preserve superseded plans, audits, and retired operations. They are useful for tracing a decision, but they are not current authority. A historical item is retained only when it adds context not already available from source, a current document, or Git history.

Before changing a Foundation document, create a local snapshot under `docs/foundation/_snapshots/`. Write verified durable behavior only; do not record a temporary visual judgment, a one-off performance number, a workflow run ID, or a task chronology as a product rule.

## Source basis

Verified from source:

- Production routes and Record Shop components: `ui/src/App.tsx`, `ui/src/routes/RecordShop.tsx`, and `ui/src/components/record-shop/`.
- Static-data parsing and recovery: `ui/src/lib/data.ts`, `ui/src/lib/archive.ts`, and `ui/src/lib/product-clock.tsx`.
- Build/release behavior: `.github/workflows/ci.yml`, `.github/workflows/pages_daily.yml`, `daily3albums/cli.py`, and `scripts/restore_static_archive_seed.py`.
- Same-origin cover materialization: `daily3albums/cover_assets.py` and `ui/src/lib/covers.ts`.
