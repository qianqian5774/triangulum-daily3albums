# Triangulum – Daily3Albums: End-to-End Doctor (Authoritative)



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
- Minimal probes must be single lightweight requests.

## Plan parsing robustness (required)

Doctor implementations must be resilient to plan parsing failures and must still produce artifacts.

1) Preferred: keep the YAML in this file strictly valid.
2) Defensive parsing (required): before parsing, perform a best-effort sanitization pass for a narrow class of common YAML footguns:
   - If any `name:` or `label:` scalar contains an unquoted colon pattern (`:` followed by a space), automatically wrap the full scalar value in double quotes.
   - This sanitization must be conservative and limited to `name:` and `label:` keys only (do not rewrite other keys).
   - Record that sanitization happened as evidence in logs and in REPORT.md “Algorithm Trace”.
3) Fallback plan (required): if AGENTS.md is missing, severely corrupted, or plan parsing still fails after sanitization:
   - Do NOT crash.
   - Switch to a built-in, hard-coded minimal fallback plan that:
     - emits `overall_status=fail`,
     - records a single severity="high" Issue that includes the parsing error details and how to fix AGENTS.md,
     - produces `doctor/REPORT.md` and `doctor/REPORT.json`.
   - Exit with a failing exit code after writing artifacts.

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
      name: "Minimal probe: Last.fm (1 request, no concurrency)"
      action: probe_lastfm_minimal
      required: true
      hard_gate_ids: [lastfm_probe_ok]
      rate_limit:
        max_requests: 1
        sleep_seconds_after: 1

    - id: probe_musicbrainz
      name: "Minimal probe: MusicBrainz (1 request, no concurrency)"
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
      name: Render QA (Playwright + local server + signals)
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
  - Optionally archives under:
    - `doctor/runs/<run_id>/...`
    - and copies “latest” to fixed paths


- `doctor/runs/<run_id>/` (recommended)
  - logs/json evidence for that run
  - “latest” copy for stable diffing

## Render QA requirements (must implement)

Goal: not only verify “it runs/builds”, but systematically detect “renders but looks wrong” defects and land evidence into regression-friendly text artifacts (JSON).

Method:

- Use Playwright to start a local static server pointing to `_build/public`.
- Visit targets in order (today → archive → detail) in two viewports:
  - Desktop 1280×720
  - Mobile 375×812
- After each page finishes loading:
  - Collect render health signals and write JSON into:
    - `doctor/runs/<run_id>/ui_audit/{today,archive,detail}.{desktop,mobile}.json`
      Copy latest snapshots to stable locations (recommended):

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
  - stable fields from the DOM + key render-signal JSON
- Store fingerprints in REPORT.json under `checks.artifacts` (stable key structure)

## REPORT.md fixed structure (must match)

Keep short, but must cover:

1) Summary (environment/commit/run_id/overall_status)
2) Steps (per doctor-plan: command/action + exit_code + duration + log_path)
3) Findings
   - External probes
   - Build/artifacts validation
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
- Ensure doctor always produces the reports, even on failures.

## Definition of success

A successful implementation (even when `overall_status=fail`) produces:

- `doctor/REPORT.md`
- `doctor/REPORT.json`
- `doctor/runs/<run_id>/` with logs and ui_audit JSON evidence

End of AGENTS.md.
