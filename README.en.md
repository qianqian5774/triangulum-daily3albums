# Triangulum Daily 3 Albums

中文 | [English](README.en.md)

A static-site “daily dose” album recommender with deterministic, time-gated unlock windows on **Beijing Time (Asia/Shanghai)**.

This repo builds **once per day**. The site switches between today’s slots **at runtime** in the browser (no redeploy needed at unlock times).

---

## Local build + preview

1) (Optional) Build the UI (if you changed UI code):

```bash
npm --prefix ui ci
npm --prefix ui run build
```

2) Build the daily artifacts (the generator writes runtime JSON into `_build/public/data`):

```bash
daily3albums build --verbose --out ./_build/public
```

3) Preview the static site from `_build/public`:

```bash
python -m http.server --directory _build/public 8000
```

Then visit `http://localhost:8000/`.

> Note: Local testing should only serve `_build/public`. Do not serve `ui/public/data` (or `ui/dist/data`) for runtime JSON, or you may accidentally render seed data.

---

## Runtime unlock windows (Beijing Time)

The site computes the current state using **Beijing Time (Asia/Shanghai)** on the client:

- `OFFLINE` 00:00–05:59
- `SLOT0` 06:00–11:59
- `SLOT1` 12:00–17:59
- `SLOT2` 18:00–23:59

Unlock switching is **client-side only**: once today’s `today.json` is generated and deployed, the browser selects which slot to display based on BJT.

---

## Schedule + timezone (GitHub Actions)

The GitHub Pages workflow runs **once per day** to generate and deploy “today”:

- Target time: **05:17 Beijing Time (Asia/Shanghai)**
- Cron expression (UTC): `17 21 * * *` (this is **21:17 UTC on the previous day**)
- A small workflow jitter (e.g. `0–120s`) may be applied **inside** the job to avoid “same-second” congestion
- Workflow timezone must be explicit: `TZ=Asia/Shanghai` and `DAILY3ALBUMS_TZ=Asia/Shanghai`

Important: The generator must compute `today.json.date` using **Asia/Shanghai**, not runner-local UTC, to avoid “wrong day” artifacts.

---

## Debug Mode (time simulation)

When developing, you shouldn’t wait for real-world clock boundaries. Use `debug_time` to simulate Beijing Time instantly.

### How it works

Append a query parameter:

`?debug_time=YYYY-MM-DDTHH:MM:SS`

Rules:

- The value is interpreted as **Beijing Time (Asia/Shanghai)**
- Seconds are optional: `YYYY-MM-DDTHH:MM` is also accepted
- When `debug_time` is present, the UI uses it as “now” for:
  - OFFLINE ↔ SLOT transitions
  - Cross-slot boundaries (06:00 / 12:00 / 18:00)
  - Cross-day rollover (23:59:xx → 00:00:xx)

### Examples

- Test OFFLINE → SLOT0:

`http://localhost:8000/?debug_time=2024-03-21T05:59:50`

then change to:

`http://localhost:8000/?debug_time=2024-03-21T06:00:10`

- Test SLOT2 → OFFLINE rollover:

`http://localhost:8000/?debug_time=2024-03-20T23:59:50`

then change to:

`http://localhost:8000/?debug_time=2024-03-21T00:00:10`

### Turning Debug Mode off

Remove the `debug_time` query parameter and reload the page.

If the UI also persists debug time in session storage, you can clear it manually:

```js
sessionStorage.removeItem("tri_debug_time");
```

---

## Generator constraints (current)

- Date/slot/cooldown math uses **Asia/Shanghai (BJT)** only.
- Hard constraints: same-day album uniqueness, same-day main-artist disjointness, 7-day artist cooldown, and type gating (Album allowed by default; unknown type is allowed).
- Slot theme model: each slot picks one `theme` from `tag_pool`; every pick in the slot uses `style_key == theme_key` (normalized theme).
- Theme cooldown: exact `theme_key` cannot repeat within 3 days.
- Decade constraints are disabled by default (`decade_mode: off`), so build validation no longer enforces decade coverage or unknown-year ceilings.

## Notes on caching

Browsers/CDNs may cache `today.json`. At critical boundaries (especially OFFLINE → SLOT0 at 06:00 BJT), the UI may force a cache-busting fetch:

- `fetch("/data/today.json?t=" + Date.now(), { cache: "no-store" })`

If fetching returns stale data (e.g. `today.json.date` is not today in BJT), the UI should enter a safe fallback state and retry until it receives the correct day.
