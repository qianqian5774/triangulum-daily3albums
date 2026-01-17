# Triangulum Daily 3 Albums

## Local build + preview

1. Build the daily artifacts:
   ```bash
   daily3albums build --tag electronic --verbose
   ```
2. Preview the static site from `_build/public`:
   ```bash
   python -m http.server --directory _build/public 8000
   ```
   Then visit `http://localhost:8000/`.

## Schedule + timezone

The GitHub Pages workflow runs daily at **00:10 Asia/Taipei (UTC+8)**.

- Cron expression (UTC): `10 16 * * *`
- Timezone in workflow: `Asia/Taipei` via `TZ` and `DAILY3ALBUMS_TZ`
