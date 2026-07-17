# R5 UI State Ownership Audit

## Status

- R5 code-stage contract: implemented.
- R5 production acceptance: completed for the normal production path.
- The original PR-stage evidence remains below; the final section records the later natural production acceptance separately.

## Scope

R5 separates Today Page business state from its concrete presentation while preserving the existing DOM, CSS, visual treatment, interaction model, schedule, public JSON contract, and recommendation output.

## State ownership

| Authority | Responsibility |
| --- | --- |
| `ProductClockProvider` | Shared product/debug clock, BJT state, slot boundary, visual theme, and Time Lab mutations. |
| `useTodayData` | `today.json` loading, current-date validation, last-good storage, signal-loss/restored state, focus/visibility refresh, retry pacing, and archive fallback. |
| `useTodayPresentation` | Current display issue projection, slot availability and selection, stable pick identity, return-to-now state, and presentation-ready slot/pick props. |
| `useTodayOverlayState` | Treatment Viewer focus/navigation, Share Card open state, Ambient idle/manual state, glitch state, focus restoration, and locked-archive feedback. |
| `TodayRoute` | Existing page composition, transition rendering, cover preloading, HUD presentation updates, and component props. |

The route no longer owns external data loading, recovery storage, archive fallback, or overlay setters. Source-policy tests protect this ownership boundary.

## Preserved behavior

- Visitor browsers continue to read only deployed static JSON and assets; no runtime external music/data API was introduced.
- `debug_time`, BJT schedule boundaries, slot unlock availability, stale-date rejection, last-good behavior, archive recovery, and retry timing are unchanged.
- Today Page, Offline State, Archive Page, Treatment Viewer, Ambient Overlay, Share Card, HUD status, focus restoration, and keyboard navigation retain their existing behavior.
- Public JSON parsing and paths, recommendation generation, request budgets, writer output, and archive lifecycle are unchanged.
- No CSS, Album Card visual, Viewer layout, Archive DOM, typography, color, grid, or animation contract was changed.

## Validation

- UI unit and source-policy tests cover shared clock and Today state ownership.
- Production UI build completes with the existing Node/runtime contract.
- Browser regressions cover product/debug clock boundaries, Today and Offline states, stale payload recovery, archive fallback, retry behavior, slot availability, Treatment Viewer navigation and cover resilience, Share Card, Archive Page, and mobile overflow.
- Deterministic screenshots cover Offline, Today, Share Card, Treatment Viewer, and Archive surfaces against the pre-R5 baseline. Repeated captures produce pixel-identical layouts and text; the only non-identical samples are nondeterministic Chrome shadow antialiasing with a maximum channel delta of 2/255 and an occasional single-pixel 1/255 delta.

## Non-goals

- No new UI or visual design.
- No Viewer or Archive rewrite.
- No CSS decomposition, Archive DOM work, Ambient performance work, or CLS project.
- No schedule, public JSON, recommendation, build-generation, or production-acceptance policy change.
- R6, TD-02B, and later visual implementation stages are not started by R5.

## Production acceptance closure

The original R5 scope and acceptance text require preservation of the normal
UI/data/clock/presentation behavior plus regression coverage for recovery
paths. They do not require a natural production outage to manufacture stale,
last-good or archive fallback.

Scheduled Pages run `29538888750` built and deployed the R5 implementation on
`main`. Its retained production artifact has current Today, index and archive
payloads accepted by the real TypeScript parsers. A browser check of the
deployed site at BJT 16:05 confirmed:

- Today Page date `2026-07-17`, `OPERATIONAL` status and the
  `16:00–23:59` product window;
- the third Today slot rendered three current Album Cards;
- Archive Page loaded seven dates and rendered all three 3-pick windows for
  the current issue;
- Today and Archive shared the same BJT clock state;
- no browser warning or error was recorded during either normal path.

Therefore `R5 production acceptance: completed` for the normal production
path. Natural production did not trigger stale payload, last-good, archive
fallback, retry exhaustion or recovery transitions. Those paths remain
covered by the existing deterministic browser and UI regressions and are not
misreported here as naturally triggered production evidence.
