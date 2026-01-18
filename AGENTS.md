# Agent Instructions (Triangulum - Daily3Albums)

## Scope
This repo supports a reusable "doctor health-check" that must be runnable in Codex Web (cloud). The doctor run must be non-interactive and must produce stable artifacts (REPORT.md + doctor/REPORT.json + 3 screenshots).

## Doctor mode: FULL (default)
FULL mode means: run ALL checks below, including external-service probes + builds + artifact validation + deployment freshness check + code health. Do not downgrade to partial unless a dependency truly cannot be installed in Codex Web.

## Network policy
- Network is allowed and required for correctness (Last.fm / MusicBrainz).
- MUST respect the repo’s own rate limiting + caching (RequestBroker or equivalent). Do not bypass.
- For "probes", use minimal calls (one tag sample, one MB lookup, etc.) and prefer cache hits on repeated runs.

## Gates
Hard gates (must PASS, otherwise overall FAIL):
1) Last.fm probe (requires LASTFM_API_KEY)
2) MusicBrainz probe (requires MB_USER_AGENT)
3) Build pipeline completes and produces _build/public

Soft coverage (WARN only, never FAIL):
- Discogs / ListenBrainz / SMTP are best-effort. If missing or probe fails, report coverage=PARTIAL with risks.

## Outputs (must always be produced)
1) REPORT.md (repo root, human readable)
2) doctor/REPORT.json (machine readable receipt)
3) Screenshots as SVG text files (NOT PNG):
   - doctor/screenshots/today.svg
   - doctor/screenshots/archive.svg
   - doctor/screenshots/detail.svg
   Screenshot implementation may embed a raster screenshot inside an SVG wrapper (base64) so the file stays text-based.

## Environment artifacts (not source code)
- `.env` is an environment artifact. Ensure it is gitignored.
- doctor outputs (REPORT.md, doctor/REPORT.json, doctor/screenshots/*) are run artifacts; default to gitignore unless explicitly requested otherwise.

## Build commands (must run in doctor)
- `daily3albums build --tag electronic --verbose`
- If `ui/` exists: `npm --prefix ui run build`

## Artifact validation (full)
- Validate _build/public/data/today.json structure and invariants.
- Validate _build/public/data/index.json references every archive date file.
- Validate ALL files under _build/public/data/archive/*.json (not just the first).
- Determinism check: run build twice in the same doctor run (2nd run should be mostly cache hits) and compare hashes of key artifacts (today.json, index.json, the referenced archive date file). Report mismatch as FAIL (or WARN if repo design explicitly allows non-determinism).

## Deployment freshness check (required)
- Infer GitHub Pages URL from git remote (owner/repo) as: https://{owner}.github.io/{repo}/
- Fetch remote `index.html`, `data/today.json`, `data/index.json` and compare hashes with local build artifacts.
- If remote differs, report "STALE DEPLOY" with likely causes checklist (workflow not triggered, pages artifact wrong, caching/service worker, CDN cache) and show evidence (hashes + key differing lines/fields).

## External origins scan (informational)
- External origins are allowed. Categorize as:
  - EXPECTED (e.g., lastfm cover domains, musicbrainz.org, youtube.com)
  - UNKNOWN (anything else)
- UNKNOWN origins => WARN with file paths.
- EXPECTED origins => INFO.

## Code health (full)
- Python:
  - pip check (WARN on conflicts)
  - compileall (FAIL on syntax/import errors)
  - ruff check + ruff format --check (FAIL on errors)
  - pytest (FAIL on test failures; if no tests exist, create minimal smoke tests under tests/ and run them)
  - Optional (WARN if tool/config exists): mypy, bandit, pip-audit
- UI (if ui/ exists):
  - npm run lint (if script exists) (FAIL on lint errors)
  - npm run test (if script exists) (WARN/FAIL based on script result; at least report coverage)

## Algorithm & Rules section (must be accurate to repo code)
Doctor report must explain "Headliner/Lineage/DeepCut" selection as implemented in THIS repo, including:
- Candidate sources and normalization keys
- Quarantine/ambiguity rules
- Filters/guards
- Scoring + constraints (dedupe windows, same-artist rule if present, seeding/determinism)
- Where to find score breakdown / decision trace in logs/artifacts
