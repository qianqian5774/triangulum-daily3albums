# Triangulum – Daily3Albums: End-to-End Doctor (Authoritative)

This repository ships a “doctor” workflow that performs a comprehensive end-to-end health check from data ingestion to final rendering.

AGENTS.md is the single source of truth. Implementations must follow this document exactly, especially the hard constraints and the doctor-plan (YAML) below.

## Scope and intent

Doctor must cover the full path:

- Engine / ingestion: external service probes (Last.fm, MusicBrainz; plus optional soft probes)
- Data outputs: generated JSON artifacts
- Build: produce the static site at `_build/public`
- UI: render QA for “renders but looks wrong” defects, with regression-friendly evidence artifacts

Doctor must be sequential, deterministic, and beginner-readable in reporting.

## Non-negotiable constraints (hard)

1) External APIs
- Respect rate limits and backoff.
- No concurrent flooding.
- All external requests MUST go through the repo’s existing cache/governance layer (e.g., RequestBroker) rather than direct ad-hoc HTTP calls.
- Minimal probes must be single lightweight requests.

2) Hard gate behavior
- If Last.fm + MusicBrainz configuration is missing OR the minimal probe fails:
  - `overall_status = fail`
  - Still generate the complete report and all screenshots (SVG), using placeholder SVGs if necessary.

3) Reporting quality (beginner-readable)
For every issue, report MUST include:
- what / where / repro / fix / risk / rollback / verify
Do not dump raw stack traces as the only output; traces can go into logs.

4) Stable outputs
- Fixed paths and stable JSON keys are required to support diffs/automation.
- Do not rename fields casually; prefer additive changes.

5) SVG-only visual evidence
- Screenshots/evidence MUST be SVG.
- Do not generate or depend on PNG/JPEG/WebP or other raster outputs.
- Playwright “screenshots” must be implemented as DOM→SVG snapshots (preferred) or placeholder SVGs (fallback).

## Entry points and artifact chain (overview)

Doctor should explain (in REPORT.md) the repository’s entrypoints and artifact chain, at minimum:

- “Engine” produces data artifacts (JSON) used by the site.
- “Build” places final static outputs under `_build/public`.
- “UI” reads from `_build/public` (including `data/` and assets) and must be render-audited via a local static server.

If specific entrypoints differ (module names, CLI commands), doctor must discover them from the repository (pyproject, README, existing CLI) and record the discovery results as evidence.

## How to run (authoritative)

From repo root:

- Primary:
  - `python -m doctor.run_doctor`

Doctor must:
- parse the doctor-plan YAML embedded in this file,
- execute steps sequentially,
- write run artifacts under `doctor/runs/<run_id>/`,
- copy the “latest” artifacts to fixed paths under `doctor/`.

## Doctor plan (YAML) — must be parsed and executed in order

Do not change the plan structure lightly. Doctor must treat this YAML as machine-readable input.

```yaml
doctor_plan:
  version: 1
  name: triangulum_daily3albums_doctor

  fixed_paths:
    report_md: doctor/REPORT.md
    report_json: doctor/REPORT.json
    screenshots:
      today: doctor/screenshots/today.svg
      archive: doctor/screenshots/archive.svg
      detail: doctor/screenshots/detail.svg
    latest_run_dir: doctor/runs/latest

  per_run_layout:
    root: doctor/runs/{run_id}
    logs_dir: doctor/runs/{run_id}/logs
    artifacts_dir: doctor/runs/{run_id}/artifacts
    ui_audit_dir: doctor/runs/{run_id}/ui_audit

  hard_gates:
    - id: lastfm_configured
      label: Last.fm configuration present
    - id: musicbrainz_configured
      label: MusicBrainz configuration present
    - id: lastfm_probe_ok
      label: Last.fm minimal probe succeeded
    - id: musicbrainz_probe_ok
      label: MusicBrainz minimal probe succeeded

  viewports:
    desktop: { width: 1280, height: 720 }
    mobile: { width: 375, height: 812 }

  ui_targets:
    - id: today
      label: Today
      primary_url_path: /
    - id: archive
      label: Archive
      discovery: nav_link_contains
      match_substring: archive
      fallback_paths: ["/archive", "/archive.html", "/archives", "/index.html"]
    - id: detail
      label: Detail
      discovery: first_archive_item_detail_link

  steps:
    - id: overview
      name: Overview + entrypoint discovery
      action: overview_discovery
      required: true

    - id: config_check
      name: Config check (Last.fm + MusicBrainz)
      action: config_check
      required: true
      hard_gate_ids: [lastfm_configured, musicbrainz_configured]

    - id: probe_lastfm
      name: Minimal probe: Last.fm (1 request, no concurrency)
      action: probe_lastfm_minimal
      required: true
      hard_gate_ids: [lastfm_probe_ok]
      rate_limit:
        max_requests: 1
        sleep_seconds_after: 1

    - id: probe_musicbrainz
      name: Minimal probe: MusicBrainz (1 request, no concurrency)
      action: probe_musicbrainz_minimal
      required: true
      hard_gate_ids: [musicbrainz_probe_ok]
      rate_limit:
        max_requests: 1
        sleep_seconds_after: 1

    - id: soft_probes
      name: Soft probes (non-fatal)
      action: soft_probes_optional
      required: false

    - id: build_public
      name: Build static site to _build/public
      action: build_public
      required: true

    - id: validate_artifacts
      name: Validate JSON artifacts and today 3 slots
      action: validate_artifacts
      required: true

    - id: render_qa
      name: Render QA (Playwright + local server + DOM→SVG + signals)
      action: render_qa
      required: true
```

## Required repository deliverables (doctor/)

Create a `doctor/` package containing, at minimum:

- `doctor/run_doctor.py` (runnable via `python -m doctor.run_doctor`)
  - Reads/loads the doctor-plan YAML from `AGENTS.md`
  - Executes steps sequentially (no parallelism)
  - For each step, records:
    - stdout, stderr, exit_code, duration_ms, log_path, produced_artifacts
  - Produces:
    - `doctor/REPORT.md`
    - `doctor/REPORT.json`
    - `doctor/screenshots/{today,archive,detail}.svg` (always)
  - Optionally archives under:
    - `doctor/runs/<run_id>/...`
    - and copies “latest” to fixed paths

- `doctor/screenshots/`
  - Fixed output paths:
    - `today.svg`, `archive.svg`, `detail.svg`
  - Must exist even on failure (placeholder SVGs with readable text)

- `doctor/runs/<run_id>/` (recommended)
  - logs/screenshots/json evidence for that run
  - “latest” copy for stable diffing

## Render QA requirements (must implement)

Goal: not only verify “it runs/builds”, but systematically detect “renders but looks wrong” defects and land evidence into regression-friendly text artifacts (SVG/JSON).

Method:
- Use Playwright to start a local static server pointing to `_build/public`.
- Visit targets in order (today → archive → detail) in two viewports:
  - Desktop 1280×720
  - Mobile 375×812
- After each page finishes loading:
  - Collect render health signals and write JSON into:
    - `doctor/runs/<run_id>/ui_audit/{today,archive,detail}.{desktop,mobile}.json`
  - Produce SVG-only “visual evidence”:
    - Preferred: DOM→SVG snapshot:
      - Serialize the DOM into an SVG `<foreignObject>`, inline as much critical CSS as possible so the SVG is self-contained and readable.
    - Fallback: placeholder SVG (text-only) that includes:
      - failure reason, url, run_id, commit, timestamp
      - and points to the JSON evidence/log path.

Copy latest snapshots to stable locations (recommended):
- Keep `doctor/screenshots/{today,archive,detail}.svg` as the “three screenshot set”.
- Render QA SVG snapshots may reuse these or be additional, but must not introduce raster dependencies.

### Render QA checklist (each item must land evidence)

Not hard gates by default, but MUST be recorded as Issues (with what/where/repro/fix/risk/rollback/verify) when failing or suspicious.

1) Console health
- Capture: console.error, console.warn, pageerror, unhandledrejection
- Record entries + short stack summaries
- Report top “most destructive” N

2) Network & resource completeness
- Count all requests during page load (url, status, resource type, duration)
- Identify 404/500/failed resources and judge whether they can cause blank page / missing styles / missing data
- Detect any runtime requests to external domains (other than the local server)
  - If present, explain:
    - why it happens,
    - whether it violates “static site should have zero external dependencies” expectations,
    - how to fix

3) Routing & internal link robustness
- Extract key internal links (navigation, first archive item’s detail link, etc.)
- Validate reachable and not 404 under the local server
- If SPA routing is used:
  - verify refresh/direct navigation to the detail link works

4) Layout/overflow and viewport anomalies
- Horizontal overflow:
  - detect `document.documentElement.scrollWidth > clientWidth`
  - record overflow delta and candidate triggering element(s) (bounding-box scan)
- Key container not visible:
  - detect height 0, display:none, visibility:hidden, opacity:0
  - detect likely occlusion by fixed overlays (estimate via bounding boxes and stacking context heuristics)

5) Fonts/icons missing
- Evidence chain:
  - failed network resources related to fonts
  - CSS `@font-face` access failures where detectable
  - DOM heuristics for “tofu”/missing glyph indicators where feasible
- Report suspected impact to real users

6) Data rendering consistency
- Extract “today 3 slots” (title/artist/link or equivalent) from page DOM
- Compare with `_build/public/data/today.json`
- On mismatch, classify:
  - “data correct but UI not showing”
  - “UI showing but data wrong”

7) Basic accessibility (a11y) smoke
- Run a lightweight scan (e.g., axe-core)
- Output violation counts and several most severe findings (text)
- a11y is not required to be a hard gate, but report must describe real-user impact

8) Stability & regressability
- For each page+viewport, generate a comparable fingerprint hash based on:
  - stable fields from SVG text snapshot + key render-signal JSON
- Store fingerprints in REPORT.json under `checks.artifacts` (stable key structure)

## SVG snapshot rules (no raster)

- Do NOT call Playwright `page.screenshot()` or any API that emits PNG by default.
- DOM→SVG snapshot should:
  - include viewport width/height in the SVG
  - embed HTML via `<foreignObject>`
  - inline critical styles (best-effort); record any stylesheet access failures in JSON
- If DOM→SVG cannot be produced:
  - Write a placeholder SVG and record the precise reason in JSON + REPORT.md
  - Examples of reasons: blocked stylesheet access, CSP, cross-origin fonts, inaccessible CSS rules

## REPORT.md fixed structure (must match)

Keep short, but must cover:

1) Summary (environment/commit/run_id/overall_status)
2) Steps (per doctor-plan: command/action + exit_code + duration + log_path)
3) Findings
   - External probes
   - Build/artifacts validation
   - Screenshots index
   - Render QA summary: console/network/link/layout/data/a11y + evidence paths
4) Issues (by severity; each includes what/where/repro/fix/risk/rollback/verify)
5) Algorithm Trace (rules + code locations + run parameters + evidence)
6) Forward Risks & Coverage (what ran/didn’t run and the impact)

## REPORT.json stability rules

- Keep top-level keys stable and additive:
  - `meta` (run_id, timestamp, commit, environment)
  - `overall_status`
  - `steps[]` (id, name, exit_code, duration_ms, log_path, artifacts[])
  - `checks` (structured results; stable nesting)
  - `issues[]` (severity, what, where, repro, fix, risk, rollback, verify, evidence_paths[])
- Prefer adding new fields rather than renaming existing ones.

## Implementation rules for Codex changes

- Prioritize minimal, surgical additions:
  - Add `doctor/` package + supporting files only.
  - Do not refactor core pipeline unless strictly required for correctness.
- Prefer standard library where possible; if adding dependencies (Playwright, axe-core):
  - keep them clearly scoped to doctor
  - vendor any required JS assets locally (no external fetch at runtime)
  - document version and license in doctor/ where appropriate
- Ensure doctor always produces the fixed-path SVGs and reports, even on failures.

## Definition of success

A successful implementation (even when `overall_status=fail`) produces:

- `doctor/REPORT.md`
- `doctor/REPORT.json`
- `doctor/screenshots/today.svg`
- `doctor/screenshots/archive.svg`
- `doctor/screenshots/detail.svg`
- `doctor/runs/<run_id>/` with logs and ui_audit JSON+SVG evidence
- Clear, reproducible issues with rollback guidance and verification steps

End of AGENTS.md.
