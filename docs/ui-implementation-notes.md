# UI Implementation Notes

## GitHub Pages Base Path
- The site is deployed under a project sub-path, so every asset and fetch URL must be built from a `BASE_URL`/`import.meta.env.BASE_URL` (Vite) value.
- Avoid leading `/` in URLs; instead, use relative paths that join `BASE_URL` + `data/...` or `BASE_URL` + `assets/...` to keep the app portable between local dev and Pages.

## Routing Strategy
- Prefer `HashRouter` for the initial UI rewrite since it avoids Pages 404 issues and does not require extra SPA fallback setup.
- If `BrowserRouter` is required later, add a GitHub Pages SPA fallback (e.g., a `404.html` that redirects to `index.html` with the original path encoded) and update documentation accordingly.

## Data/Asset Path Construction
- JSON data is generated at build time (`data/today.json`, `data/archive/YYYY-MM-DD.json`, `data/index.json`, optional `data/quarantine/YYYY-MM-DD.json`).
- Always resolve JSON fetches relative to `BASE_URL` (e.g., `${BASE_URL}data/today.json`).
- Asset URLs (cover images, icons, QR placeholders) should also be built with the same `BASE_URL` prefix.
- Keep a single URL helper (e.g., `resolvePublicPath`) to prevent accidental absolute paths.
