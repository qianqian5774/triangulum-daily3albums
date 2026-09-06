# Performance architecture

This document records stable production performance practices. It is not a benchmark table and does not turn a single browser run, device, issue, or threshold into a permanent product claim.

The detailed July 2026 measurement snapshot was moved to [docs/legacy/performance-baseline-2026-07-12.md](./docs/legacy/performance-baseline-2026-07-12.md). It is historical evidence only.

## Current production practices

- The Entry Diorama uses a demand-driven render loop. It schedules frames for initialization, input, camera movement, the door transition, or an explicit state change, then stops once the camera and scene settle. It does not keep rendering an idle scene continuously and does not schedule a hidden document.
- Static opaque diorama meshes with compatible geometry/material are batched into an InstancedMesh. Interactive or transparent objects, including the door and glazing, stay independent so raycasting and visual behavior remain correct.
- The Record Shop preloads and decodes its fixed interior layers before entering the scene. The attendant, counter occluder, device masks, and environment remain separately composited assets rather than one repeatedly rebuilt canvas.
- Cover rendering normally uses same-origin assets materialized during the production build. Each image retains a local placeholder/error path so an upstream cover failure does not prevent the Record Shop or Treatment Viewer from becoming usable.
- Record Shop font files are bundled as local WOFF2 unicode-range slices with font-display: swap. The CJK interface subset has system fallbacks for metadata outside its static vocabulary.
- Reduced-motion media rules remove non-essential long animations while retaining direct state changes and usable controls.

## Validation

Use the performance audit only when a change can affect runtime work, transfer size, interaction delay, layout stability, or rendering behavior:

    npm --prefix ui run performance:audit

The audit writes ignored local evidence under ui/artifacts/performance. For diorama behavior, pair it with the focused browser and unit coverage:

    npm --prefix ui run browser:record-shop
    npm --prefix ui test

A browser result is evidence for the exact code, data, machine, and settings used in that run. It should guide a regression decision, not be copied into this document as a timeless FPS, LCP, or CLS baseline.

## Scope boundary

Performance work must preserve the static Pages architecture, BJT product clock, public JSON contract, archive safety, same-origin cover path, and visual/interaction authority. A lower render cost does not justify changing the daily recommendation system or replacing the Record Shop experience.

## Source basis

Verified from source: ui/src/components/record-shop/EntryDiorama.tsx, ui/src/components/record-shop/diorama-batching.ts, ui/src/components/record-shop/InteriorGallery.tsx, ui/src/routes/record-shop-fonts.css, ui/src/lib/covers.ts, and ui/package.json.
