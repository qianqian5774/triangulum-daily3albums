# Triangulum Daily: project guidance

These rules apply to repository work unless the task gives a narrower scope. Check the current source, tests, workflows, and production artifacts before relying on older notes.

## Local environment

- Read `AGENTS.local.md` before local commands when it exists. It is Git-ignored machine guidance for executable paths and browser setup, not repository authority.
- Use the existing project runtimes and tools. Run only the validation relevant to the change.

## Product and architecture

- Triangulum Daily publishes nine albums per BJT day in three windows, with three albums unlocked in each window. The schedule and public contract are checked in `tests/fixtures/`.
- The production entry is the Record Shop at `#/`: an Entry Diorama leads into the shop, where Today and History use published static data. `#/today` and `#/archive` are supporting surfaces. Treatment Viewer is an overlay, not a detail route.
- The Python generator may use external music services before deployment. GitHub Pages serves static JSON and assets; visitor browsers must not use those services as application data APIs. Do not add a backend, database, login, visitor writes, or player service without an explicit architecture decision.
- Remote images and fonts are resource dependencies, not application data APIs. Evaluate their availability, privacy, CORS, and performance when changing them. Build-time provider probes must follow the project's rate limits and retry policy.

## Validation

Choose the smallest applicable layer. Portable commands, with the configured runtimes active:

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

Browser smoke needs an existing `_build/public`; performance audits are separate production probes. See `docs/runbook.md` for release checks. Doctor is retired and is not a health or release command.

## Git and artifacts

- Preserve unrelated changes. Before committing, inspect `git status -sb`, `git diff --stat`, and the content diff; stage only explicit task files. Do not use `git add .` in a mixed worktree.
- Do not commit generated outputs, credentials, environment files, caches, logs, or local evidence, including `_build/`, `ui/dist/`, `ui/artifacts/`, `.playwright-cli/`, `.state/`, `.venv/`, and `.codex/`.
- Build Metrics and Recommendation Observability source code are tracked; their runtime outputs are generated artifacts.

## Documentation

- `docs/foundation/` contains tracked current-state architecture, data, recommendation, release, and UI explanations. `docs/design/` holds the formal visual and interaction authority; `docs/runbook.md` holds operational entry points; `PERFORMANCE.md` holds stable performance guidance. `docs/archive/`, `docs/revive/`, and `docs/legacy/` are historical.
- For durable changes to product behavior, data/API boundaries, UI structure, generation, or deployment, update the relevant current document within the task scope. Before editing Foundation, save a local snapshot under `docs/foundation/_snapshots/`; snapshots and temporary measurements are not committed.
- Source, tests, workflows, and verified production behavior take precedence when documentation differs. Keep changes focused and reviewable; do not use a documentation task to change recommendation logic or UI behavior.
