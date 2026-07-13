# R5 UI State Ownership Audit

## Status

- R5 code-stage contract: implemented.
- R5 production acceptance: pending.
- This audit records source, local validation, and current PR-stage facts only. It does not claim a production Pages acceptance run.

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
