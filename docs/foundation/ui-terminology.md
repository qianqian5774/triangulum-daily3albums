# UI terminology

Use the terms below when describing the deployed UI, a regression, or a review target. The names distinguish the current Record Shop from the older data-centric surfaces that remain available at their own routes.

## Product surfaces and routes

- **Record Shop**: the canonical production experience at `#/`, implemented by `RecordShopRoute`. It is not a prototype, preview catalog, or mock-data route.
- **Entry Diorama**: the Record Shop exterior. It is a procedural Three.js miniature with six named preset views — AXON, FRONT, RIGHT, REAR, LEFT, and ROOF — plus bounded pointer/touch inspection and zoom. The physical door is the only canonical transition into the interior.
- **Record Shop interior**: the formal shop scene reached through the door. It contains the Daily Device, current inventory, the shop HUD, the attendant/counter composition, and a compact recent-date selector.
- **Today inventory**: the current issue as presented in the Record Shop interior. It comes from the published `today.json`; it is not a separate Record Shop catalog.
- **History inventory**: a completed issue selected from the interior's recent-date selector. It is built from `index.json` and the corresponding archive issue JSON while remaining in the same interior.
- **Treatment Viewer**: the modal reading layer opened from a selected record. It uses that same published pick's title, artist, cover, metadata, and available description; it is not a detail route.
- **Today route**: the supporting static-data surface at `#/today`. It is distinct from the canonical Record Shop landing experience.
- **Archive Page**: the broader static archive surface at `#/archive`. It reads the archive index and archive issues; it is not a second shop or a database browser.

## BJT product clock

The public clock is fixed to `Asia/Shanghai` (BJT). One published issue has three slots and three picks per slot.

| BJT window | Current Today inventory |
| --- | ---: |
| 00:00–07:59 | 0 records / Offline |
| 08:00–12:29 | 3 records |
| 12:30–15:59 | 6 records |
| 16:00–23:59 | 9 records |

The product clock gates visibility only. It does not ask the browser to generate recommendations or obtain a different issue. `debug_time` and `debug=1` remain development aids for deterministic clock checks.

## Data and cover terms

- **Published current issue**: `data/today.json`, parsed against the public contract.
- **Last-good recovery**: the current-issue recovery path used when the current issue cannot safely be used. It proceeds through retained valid data rather than inventing a browser-side issue; exact failure classification belongs to `ui/src/lib/data.ts` and its tests.
- **Archive index**: `data/index.json`, containing recent date/run entries and the retention count.
- **Run-specific archive**: `data/archive/{date}/{run_id}.json`, the preferred archive source when the index provides a run ID.
- **Date alias**: `data/archive/{date}.json`, accepted only as the checked alias fallback for the same issue.
- **Static cover manifest**: `assets/cover-manifest.js`, generated during the production build. It maps normalized remote cover URLs to same-origin files under `assets/covers/`.
- **Cover fallback**: `assets/placeholder.svg`, shown when a usable image cannot be displayed. A missing manifest entry is a degraded asset case, not permission to add a browser-side music API.

## Shop interaction terms

- **Daily Device**: the central in-scene control that represents Offline, Ready, arranging, complete, and browse states.
- **Daily OPEN / Shuffle / Continue**: the current interior-session sequence from available inventory to the browsable record strip. It is presentation state in the current client; it is not an account, server, or visitor-write system.
- **Record strip**: the finite horizontal sequence of currently available records. It supports pointer/touch drag, directional controls, and keyboard navigation without creating an infinite carousel.
- **Shop HUD**: the in-scene date, BJT time, status, inventory, and recent-date controls. The general site HUD is hidden while the Record Shop route is active.

## Source basis

Verified from source: `ui/src/App.tsx`, `ui/src/routes/RecordShop.tsx`, `ui/src/components/record-shop/EntryDiorama.tsx`, `ui/src/components/record-shop/InteriorGallery.tsx`, `ui/src/components/record-shop/catalog.ts`, `ui/src/lib/bjt.ts`, `ui/src/lib/data.ts`, `ui/src/lib/archive.ts`, and `ui/src/lib/covers.ts`.
