# Daily build and release pipeline

Triangulum Daily is deployed through the existing GitHub Actions workflow **Build and Deploy Pages (Daily)** (`.github/workflows/pages_daily.yml`). It produces a static GitHub Pages artifact; deployment is the only production write step.

## Daily production flow

The workflow runs on a schedule at 21:17 UTC (05:17 BJT on the following product day) and can be started with `workflow_dispatch`. It keeps lead time ahead of the 08:00 BJT first product window.

For a normal production run it:

1. checks out `main`, prepares Python/Node dependencies, and runs UI and Python tests;
2. restores and validates the published archive seed, preserving a valid local seed when refresh data is invalid;
3. builds the Vite UI;
4. runs the normal `daily3albums build --skip-ui-build` against the recovered history;
5. writes the public current issue, archive JSON and index, recommendation observability, and same-origin cover manifest/assets;
6. writes build metadata and runs `scripts/self_check.py` against `_build/public`;
7. emits build/recommendation summaries, uploads the Pages artifact, and deploys it with `actions/deploy-pages`.

The workflow does not use fixture mode, dev seeds, hand-authored issues, or an archive rewrite shortcut to obtain a new selection. A locked published archive may legitimately be reused for its date.

## Archive lifecycle

The static archive retention contract is seven distinct dates. A completed issue is stored both as a run-specific JSON document and a byte-identical date alias; the index identifies the run. The next production build restores this history before selection, so runner-local state does not become the only record of cooldown or archive history.

The browser receives only the published static results. It reads `today.json` for the current issue, `index.json` for history, and the checked archive run/alias pair for a date. The Record Shop consumes those same artifacts through the application parsers and recovery path.

## Local validation

Use the smallest layer that matches the change. The repository's portable forms are:

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

Machine-specific executable paths belong in `AGENTS.local.md`. Doctor is retired and is not a build, health, or release entry point. `_build/public` and `ui/dist` are generated outputs and are not committed.

## Release and incident handling

CI (`.github/workflows/ci.yml`) runs the fixture-based Python checks, dry-run/golden checks, and UI tests on pushes and pull requests. The daily workflow repeats the production gates because provider availability and archive recovery are production concerns.

To deploy a code change, merge it through the normal reviewed `main` branch process, then manually dispatch **Build and Deploy Pages (Daily)** when an immediate publication is required. For a production regression, use a reviewed revert or a focused fix on `main`; do not reset shared history or bypass archive validation, contract checks, or Pages deployment gates.

The canonical public site is `https://triangulumdaily.space/`. `DAILY3ALBUMS_PAGES_BASE_URL` is the optional published-site base URL used by archive seed recovery.

## Source basis

Verified from source: `.github/workflows/pages_daily.yml`, `.github/workflows/ci.yml`, `daily3albums/cli.py`, `daily3albums/artifact_writer.py`, `daily3albums/cover_assets.py`, `scripts/restore_static_archive_seed.py`, `scripts/self_check.py`, `scripts/build_metrics.py`, and `scripts/recommendation_observability_summary.py`.
