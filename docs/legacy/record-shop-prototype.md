# Record-shop prototype retirement

> **Historical / retired:** this record describes local prototype entrypoints removed before the formal production Record Shop. It does not define the active route or validation surface.

## Status

The broken local prototype entrypoints have been retired. The deleted
`ui/src/record-shop-prototype/` assets, data module, and stylesheet are no
longer referenced by the application or its validation entrypoints.

The following former entrypoints are not active anymore:

- `#/prototype/entry` and `#/prototype/browse`;
- the dedicated `record-shop-prototype-file` HTML/file build;
- the matching `browser:record-shop-prototype:file` Playwright suite;
- the `@local-record-shop` Vite alias and its local route wrappers.

This retirement removes broken prototype-only code. It does not remove the
formal record-shop surface or its test coverage.

## Current implementation

The active implementation is `RecordShopRoute` in
`ui/src/routes/RecordShop.tsx`, registered by `ui/src/App.tsx` at `#/`. The
`#/record-shop` path remains a compatibility redirect to that formal route.
The corresponding browser entrypoint is `npm --prefix ui run browser:record-shop`.

## Historical context

The prototype's physical browsing and entry experiments remain historical
context in [the archived UI-RD-04 plan](../archive/ui-rd-04-physical-record-shop-plan.md) and the [formal design authority](../design/). That
record is retained for rationale and does not make the retired routes,
assets, or file build active again.
