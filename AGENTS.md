# Triangulum – Daily3Albums: Project Codex Guidance

## Codex operating rules

These rules apply to Codex work in this repository unless a task gives narrower instructions.

### Project root and local toolchain

- Default project root:
  - Prefer `CODEX_WORKTREE_PATH` when it is set.
  - Otherwise use `D:\projects\triangulum-daily3albums`.
- On this Windows machine, use the fixed local Node/npm paths:
  - `C:\Users\11836\AppData\Local\nvm\v22.13.0\node.exe`
  - `C:\Users\11836\AppData\Local\nvm\v22.13.0\npm.cmd`
- Use the repository `.venv` Python/CLI paths when running project Python commands:
  - `.venv\Scripts\python.exe`
  - `.venv\Scripts\daily3albums.exe`
- Do not rely on global `npm`, `python`, or `daily3albums` when repository-specific paths are available.
- Do not use `C:\nvm4w\nodejs\npm.cmd`, change the Node install location, or swap toolchains as a workaround.

### Git hygiene and generated artifacts

- Do not use `git add .`.
- Before any commit workflow, run status/diff checks such as `git status -sb`, `git diff --stat`, and an appropriate content diff.
- Stage only explicit files that belong to the requested change.
- Do not commit generated/build artifacts, local environment files, caches, logs, or secrets, including:
  - `_build/`
  - `ui/dist/`
  - `.state/`
  - `.venv/`
  - `doctor/runs/`
  - `.codex/`
  - cache directories, logs, credentials, API keys, or token files.
- Doctor reports such as `doctor/REPORT.md`, `doctor/REPORT.json`, and `doctor/runs/<run_id>/...` are generated evidence artifacts. They are not default commit content unless a task explicitly asks for them.

### Local foundation docs memory layer

- `docs/foundation/` is an ignored local long-term project memory layer, not normal PR content.
- At the start of substantial tasks, inspect `docs/foundation/` when available and use it as durable project context.
- After major tasks, decide explicitly whether `docs/foundation/` needs updating.
- Major tasks include changes or durable clarifications to:
  - archive/data write behavior
  - build, release, GitHub Actions, GitHub Pages, custom domain, or deployment behavior
  - public JSON schema or generated static data
  - recommendation generation, filtering, scoring, sampling, observability, or metadata enrichment
  - external data/API boundaries
  - UI structure, routing, layout system, mobile behavior, terminology, or debug behavior
  - validated operational baselines, such as a successful workflow run or production verification
- Before editing `docs/foundation/`, create a local snapshot under `docs/foundation/_snapshots/` so the change can be rolled back outside Git.
- Write only verified durable facts. Do not write wishes, temporary debugging notes, or unverified assumptions as implemented behavior.
- Do not commit, open PRs for, or `git add -f` `docs/foundation/` unless the user explicitly asks.
- If `docs/foundation/` appears in `git status`, do not treat it as source-code dirt. Stash it only when necessary for branch switching, pulling, merging, or keeping a code PR clean.

## End-to-End Doctor (Authoritative)

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

- Primary on this Windows machine:
  - `.venv\Scripts\python.exe -m doctor.run_doctor`
- Portable module form, only when already inside the configured project virtual environment:
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

## Required Doctor source and generated deliverables (`doctor/`)

Doctor-related implementation work should create or maintain source files under a `doctor/` package containing, at minimum:

- `doctor/run_doctor.py` (runnable via `.venv\Scripts\python.exe -m doctor.run_doctor`)
  - Reads/loads the doctor-plan YAML from `AGENTS.md`
  - Executes steps sequentially (no parallelism)
  - For each step, records:
    - stdout, stderr, exit_code, duration_ms, log_path, produced_artifacts

Doctor runtime must produce generated evidence artifacts even when `overall_status=fail`:

- `doctor/REPORT.md`
- `doctor/REPORT.json`
- `doctor/runs/<run_id>/...` with logs/json evidence for that run
- `doctor/runs/latest` or equivalent “latest” copies for stable diffing

These generated Doctor artifacts are not default commit content unless a task explicitly asks to commit them.

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
  - If present, classify and explain:
    - why it happens,
    - whether it is a visitor-side application data/API request,
    - whether it is a remote resource dependency from generated public JSON or static assets,
    - how to fix or reduce the risk.
  - Visitor-side calls to Last.fm, MusicBrainz, Discogs, ListenBrainz, Wikipedia, or Wikimedia APIs are architecture-boundary violations unless explicitly approved.
  - Remote cover, image, or font resources can be resource dependency risks when they come from generated public JSON or static assets. Do not automatically classify them as external music/API data violations.

3) Routing & internal link robustness

- Extract key internal links (navigation, first archive item’s detail link, etc.)
- Validate reachable and not 404 under the local server
- If no standalone detail route exists, audit the Treatment Viewer overlay interaction from an Album Card as the detail target; do not treat the missing detail route alone as an automatic failure.
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

## Implementation rules for Doctor changes

- These rules apply to Doctor-related changes, not every Codex task in this repository.
- Prioritize minimal, surgical Doctor additions:
  - Add or update the `doctor/` package and directly supporting files only.
  - Do not refactor the core pipeline unless strictly required for Doctor correctness.
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

These are generated evidence artifacts. Producing them is required for Doctor behavior; committing them is not required unless explicitly requested.

End of AGENTS.md.
