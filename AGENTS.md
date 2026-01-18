- # Agent Instructions (Triangulum - Daily3Albums)

  ## Primary rule
  This repo uses a "doctor" health-check. It must ALWAYS write artifacts for the user to read in Codex Web.

  ## Network policy
  Network is allowed and required. Respect repo rate limiting + caching. No bypass.

  ## Gating philosophy
  This is a medical report, not a CI gate.
  - Report and screenshots must be produced even when issues are found.

  Hard FAIL conditions (overall_status=FAIL):
  1) Last.fm probe fails (LASTFM_API_KEY missing or probe error)
  2) MusicBrainz probe fails (MB_USER_AGENT missing or probe error)
  3) Build attempt cannot produce `_build/public`

  Everything else is WARN by default:
  - ruff/format issues, pytest failures or no tests, deployment mismatch, determinism mismatch, optional service probes, screenshot failures, unknown external origins.

  ## Required outputs (always)
  - REPORT.md (repo root)
  - doctor/REPORT.json
  - doctor/screenshots/today.svg
  - doctor/screenshots/archive.svg
  - doctor/screenshots/detail.svg
  If Playwright fails, write diagnostic SVGs instead.

  ## Visibility rule (Codex Web)
  Do NOT add REPORT.md / doctor/REPORT.json / doctor/screenshots/* to .gitignore automatically.
  Keep `.env` ignored as environment artifact.

  ## Doctor run commands
  - daily3albums build --tag electronic --verbose
  - If ui/ exists: npm --prefix ui run build
