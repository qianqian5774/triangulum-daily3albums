# Triangulum Daily 3 Albums

## Local build + preview

1. Build the daily artifacts:
   ```bash
   daily3albums build --verbose
   ```
2. Preview the static site from `_build/public`:
   ```bash
   python -m http.server --directory _build/public 8000
   ```
   Then visit `http://localhost:8000/`.

> Note: Local testing should only serve `_build/public`. Do not serve `ui/public/data` for runtime JSON.

## Schedule + timezone

The GitHub Pages workflow runs **three times per day** on Beijing time (Asia/Shanghai).

- Cron expressions (UTC):
  - `5 16 * * *` (Asia/Shanghai 00:05 next day)
  - `5 0 * * *` (Asia/Shanghai 08:05)
  - `5 8 * * *` (Asia/Shanghai 16:05)
- Timezone in workflow: `Asia/Shanghai` via `TZ` and `DAILY3ALBUMS_TZ`
