# Agent Instructions (Triangulum - Daily3Albums)

## Goal
Run a reusable "doctor" health-check in Codex Web that ALWAYS produces artifacts, even when problems are found.

## Non-interactive
Do not ask follow-up questions. Use safe defaults and proceed.

## Network policy
- Network is allowed and required.
- MUST respect repo rate limit + caching (RequestBroker). Do not bypass.

## Gating philosophy (IMPORTANT)
This doctor is a "medical report", not a CI gate.
- The run must NEVER end without writing REPORT.md + doctor/REPORT.json + screenshots.
- Most issues are WARN, not FAIL, so users can still get the report.

Hard gates (only these can set overall_status=FAIL):
1) Last.fm probe missing/failed (LASTFM_API_KEY)
2) MusicBrainz probe missing/failed (MB_USER_AGENT)
3) Core build cannot produce _build/public at all

Everything else is WARN by default:
- ruff / formatting / tests / optional services / deployment mismatch / determinism mismatch
These must be reported clearly with evidence and suggested fixes, but must not block artifact generation.

## Outputs (must always be produced)
- REPORT.md (repo root)
- doctor/REPORT.json
- SVG screenshots (text files):
  - doctor/screenshots/today.svg
  - doctor/screenshots/archive.svg
  - doctor/screenshots/detail.svg
If Playwright fails, still write diagnostic SVG files.

## Full-mode checks (coverage)
- Probes: Last.fm + MusicBrainz (hard), Discogs/ListenBrainz/SMTP (soft)
- Build: daily3albums build; UI build if ui/ exists
- Artifact validation: today.json + index.json + ALL archive/*.json
- Deployment freshness: compare local build vs GitHub Pages remote (WARN if mismatch; FAIL only if hard-gate services fail or build missing)
- Code health: pip check / compileall / ruff / pytest (all WARN unless compileall fails in core package)

## Repo hygiene for Codex Web visibility
- Do NOT auto-add REPORT.md / doctor/REPORT.json / doctor/screenshots to .gitignore.
  Users need to open them in the Web file tree.
- `.env` remains ignored as environment artifact.

## Required commands
- `daily3albums build --tag electronic --verbose`
- If ui/ exists: `npm --prefix ui run build`
