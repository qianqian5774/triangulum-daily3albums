# Triangulum Daily

[中文](./README.zh-CN.md) · [Live site](https://triangulumdaily.space/)

Triangulum Daily is a music-discovery site with **nine albums per day**, released three at a time. It is designed around a finite daily visit.

## Daily rhythm

All product times use Beijing time (Asia/Shanghai).

| Time (BJT) | Available albums |
| --- | ---: |
| 00:00–07:59 | Offline |
| 08:00–12:29 | 3 |
| 12:30–15:59 | 6 |
| 16:00–23:59 | 9 |

## Record Shop

The production home at `#/` starts outside an interactive 3D record shop. Enter through its door to browse today's records and recent history. Selecting a record opens the Treatment Viewer in the shop. `#/today` and `#/archive` are supporting data pages.

## Static production site

A Python generator prepares each issue before deployment. **Build and Deploy Pages (Daily)** publishes the React/Vite interface, static `data/today.json`, `data/index.json`, archive JSON, and same-origin cover assets to GitHub Pages. The visitor's browser reads those files; it does not generate recommendations or call music-provider APIs for application data. Unavailable covers have a local fallback.

## Develop

Use Python 3.11+, Node.js `>=22 <25`, and npm. Create a virtual environment with `python -m venv .venv` and activate it, then install the project and UI dependencies:

```bash
python -m pip install -e ".[test]"
npm --prefix ui ci
npm --prefix ui run dev
```

For a real-data build, provide build-time credentials using [`.env.example`](./.env.example), then run `daily3albums build --verbose --out _build/public` and `python scripts/self_check.py --path _build/public`. The usual checks are `python -m pytest` and `npm --prefix ui test`.

## Project documentation

- [Runbook](./docs/runbook.md): validation and release commands.
- [Foundation](./docs/foundation/README.md): current architecture, data, and release contracts.
- [Design authority](./docs/design/README.md): Record Shop visual and interaction contract.
- [Performance](./PERFORMANCE.md): stable performance practices and measurement entry point.
- [Agent guidance](./AGENTS.md): repository working rules.
