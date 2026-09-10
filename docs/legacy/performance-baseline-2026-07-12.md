# Historical performance baseline (2026-07-12)

> **Historical / superseded:** this is a dated measurement snapshot. Current performance practices are in [PERFORMANCE.md](../../PERFORMANCE.md).

This is the P1.4 audit baseline for the production static site. It records evidence before optimization; it does not authorize a UI rewrite.

## Reproduce

From the repository root on the configured Windows machine:

```powershell
C:\Users\11836\AppData\Local\nvm\v22.13.0\npm.cmd --prefix ui run performance:audit
```

The command writes timestamped and `latest.json` evidence under the ignored local directory `ui/artifacts/performance/`. The harness uses the installed Chrome channel, production `https://triangulumdaily.space`, 4x CPU throttling, a 1.8 second settle period, and a 2.4 second animation sample. Environment variables can override `PERF_BASE_URL`, `PERF_DATE`, `PERF_CPU_RATE`, `PERF_SETTLE_MS`, `PERF_FPS_SAMPLE_MS`, and `PERF_BROWSER_CHANNEL`. `PERF_SCENARIOS=viewer-desktop` limits a follow-up run to the named scenario without changing the full-audit default.

Baseline date: 2026-07-12. Production commit: `b85f844`. Browser: headless system Chrome. Two complete runs were used to check repeatability; the table below is the final run.

## Scenario baseline

Transfer values are encoded bytes observed by Chrome. `rAF/s` is headless requestAnimationFrame throughput, not display refresh rate; use it only for same-machine comparisons. `Event max` is synthetic Event Timing evidence, not field INP.

| Scenario | Load / LCP ms | CLS | Long tasks count / total ms | Main task / style ms | Requests / KiB | DOM / heap MiB / layers | rAF/s / max gap ms | Interaction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Today desktop cold | 437 / 832 | 0.646 | 7 / 697 | 3,781 / 1,378 | 15 / 221 | 181 / 6.5 / 16 | 161 / 18 | — |
| Today desktop warm | 237 / 352 | 0.646 | 15 / 1,248 | 3,643 / 1,517 | 16 / 9 | 181 / 8.2 / 16 | 163 / 18 | — |
| Today mobile cold | 596 / 788 | 0.532 | 5 / 470 | 3,523 / 1,376 | 15 / 221 | 181 / 6.6 / 17 | 162 / 18 | — |
| Today mobile warm | 316 / 456 | 0.534 | 18 / 1,152 | 3,283 / 1,462 | 16 / 9 | 181 / 6.5 / 17 | 160 / 24 | — |
| Today reduced motion | 462 / 656 | 0.648 | 6 / 596 | 2,856 / 1,246 | 15 / 221 | 181 / 5.6 / 10 | 160 / 12 | 0 animated nodes |
| Archive desktop cold | 500 / 776 | 0.379 | 19 / 2,333 | 4,364 / 1,127 | 20 / 277 | 1,692 / 8.4 / 19 | 117 / 164 | — |
| Viewer desktop cold | 801 / 780 | 0.646 | 6 / 665 | 6,310 / 1,895 | 15 / 221 | 181 / 7.3 / 16 | 160 / 24 | failed after 15,252 ms |
| Ambient desktop cold | 718 / 700 | 0.646 | 9 / 857 | 5,244 / 2,087 | 15 / 221 | 192 / 6.8 / 45 | 53 / 49 | visible in 332 ms; Event max 368 ms |
| Share desktop cold | 662 / 644 | 0.646 | 6 / 892 | 4,811 / 1,481 | 24 / 247 | 385 / 7.2 / 18 | 146 / 43 | visible in 467 ms; Event max 408 ms |
| Today, GPU disabled | 855 / 1,056 | 0.646 | 5 / 534 | 2,712 / 1,093 | 15 / 221 | 181 / 6.0 / 16 | 43 / 50 | — |

The production main application payload was approximately 124.4 KiB encoded JavaScript and 14.5 KiB encoded CSS. The cold Today transfer also included a 66.4 KiB noise texture and an 11.6 KiB Cloudflare beacon. Warm-load transfer fell to about 9 KiB, although aborted Cloudflare RUM pings appeared during page teardown and are not application-resource failures.

## Viewer cover follow-up

The first P1 performance fix was measured on 2026-07-12 against the locally built candidate, using the same machine, system Chrome, production dataset, 4x CPU throttle, settle period, and frame sample as the baseline. Two targeted runs were retained because remote image availability and cold-start scheduling varied between runs.

| Metric | Before fix | After fix, run 1 | After fix, run 2 |
| --- | ---: | ---: | ---: |
| Viewer interaction | failed after 15,252 ms | visible in 566 ms | visible in 726 ms |
| Long tasks, whole scenario | 6 / 665 ms | 25 / 2,392 ms | 18 / 1,656 ms |
| CLS, whole scenario | 0.646 | 0.646 | 0.646 |
| React commit-hook events | 79 | 33 | 35 |
| Page errors | not captured | 0 | 0 |
| Console resource diagnostics | not captured | 1 | 2 |
| Network failures / HTTP failures | 0 | 1 | 2 |
| Horizontal overflow | 0 px | 0 px | 0 px |

The Viewer now meets the 2,500 ms shell budget in both targeted runs and no longer waits for the cover request. The unchanged total CLS shows that this change did not add a page-level shift; the dedicated browser regression measured at most 0.02 CLS after the click and a stable square cover frame while the request was pending and after timeout. The higher long-task totals are whole-page cold-run values and varied substantially between the two candidate runs, so they are recorded as measured rather than attributed to the Viewer change. React commit-hook events fell because the audit no longer spends 15 seconds waiting for a cover before timing out.

The first candidate run recorded only the local server's missing `favicon.ico` 404. The second also encountered a real remote cover HTTP 500. Chrome reported those resource failures in the console, while the application produced zero page errors and the Viewer remained usable. Forced blocked, indefinitely pending, HTTP 503, recovery, Escape, ArrowLeft/ArrowRight, stale-request isolation, no-overflow, and cover-frame stability cases passed in the dedicated Playwright regression.

## Evidence-backed bottlenecks

| Priority | Finding and user impact | Evidence | Expected benefit | Change risk | Verification |
| --- | --- | --- | --- | --- | --- |
| Resolved P0 | Viewer opening was unbounded by a remote cover preload. | Before the fix, both full runs failed after about 15.2 seconds. After the fix, two targeted runs opened in 566 ms and 726 ms. The cover now has a stable placeholder, a 5-second timeout, and per-album stale-request isolation. | Realized: shell and core content remain available when the cover CDN is slow, failed, or unreachable. | Covered by dedicated browser regression. | Blocked, pending, HTTP failure, recovery, Escape, ArrowLeft/ArrowRight, stale-request isolation, layout stability, overflow, and runtime-error assertions pass. |
| P1 | Archive renders every retained day and card at once. Low-end users can see long main-thread stalls while opening or scrolling the page. | 1,692 DOM nodes, 54 images, 19 long tasks totaling 2.33 seconds, and a 164 ms maximum rAF gap. The preceding run showed the same pattern: 1,692 nodes, 1.96 seconds of long tasks, and a 103 ms gap. | Largest likely improvement to Archive responsiveness and image pressure. | Medium-high: pagination, progressive rendering, or virtualization can affect anchors, accessibility, search, and archive navigation. | Keep the six-date fixture, verify date anchors and keyboard navigation, and compare DOM, long tasks, image requests, and visual output at both viewports. |
| P1 | Ambient is the strongest graphics/compositing hotspot. | 14 animated nodes, 4 filtered nodes, 3 fixed nodes, 45 layers, and rAF throughput around 53/s versus about 161/s on Today. The prior run measured 55/s. GPU-disabled Today fell to about 43/s. | Better experience on integrated graphics and battery-powered devices. | Medium: simplifying layers, filters, or animation can materially change the intended art direction. | Compare the same fixed-duration Ambient sample on GPU-on, GPU-disabled, and reduced-motion profiles; preserve screenshots and require no functional regressions. |
| P1 | Initial HUD/data hydration causes a large layout shift. Content moves after it is already visible. | Desktop CLS 0.646 and mobile CLS about 0.53. The largest desktop shift was 0.608: the HUD changed height and the main section moved from y=212 to y=325 before settling. | Removes the most visible startup jump and improves perceived stability. | Medium: reserving HUD space across responsive states can create excess whitespace or clipping. | Capture layout-shift sources and screenshots at desktop/mobile cold load; require the main content and HUD bounds to remain stable. |
| P2 | Remote covers still dominate general image uncertainty and pressure outside the resolved Viewer-opening path. | All 6 Today images and 53 of 54 Archive images were incomplete at baseline measurement time. Share added remote image requests and increased DOM to 385 nodes. Viewer shell reliability is now covered independently. | Faster degraded-mode rendering and less dependence on third-party image latency across the remaining surfaces. | Medium: proxying, local derivatives, placeholders, and cache policy affect build size and visual fidelity. | Retain the Viewer regression; separately measure normal, slow, failed, and cached cover responses on Today, Archive, and Share before changing their image strategy. |
| P2 | The 500 ms clocks/timers and animation work keep React and style work active. | Two intervals were created on Today. The stalled 15-second Viewer scenario accumulated 79 React commit-hook events. Today style recalculation was about 1.25–1.52 seconds over the audit window. | Lower background CPU use and fewer updates while overlays or tabs are inactive. | Low-medium: coarser clocks can visibly desynchronize the HUD or window transitions. | Profile commit reasons before changing code; then compare commit counts and timers with Today, Viewer, hidden-tab, and reduced-motion states. |

The Viewer and Archive findings are implementation candidates, not permission to change UI structure during this audit. The React hook count is a rerender proxy; it does not by itself prove that every commit is unnecessary.

## Initial budgets

These thresholds are tied to this harness and should be revised only with a new recorded baseline.

### Regression guardrails

- Main application JavaScript: at most 140 KiB encoded; CSS: at most 18 KiB encoded.
- Cold Today transfer before remote covers complete: at most 250 KiB encoded and 18 requests.
- Cold Today LCP: at most 1,100 ms under 4x CPU throttling, including the GPU-disabled control.
- Today DOM: at most 220 nodes. Archive must not exceed the current 1,800-node guardrail while its P1 issue is open.
- Reduced motion: zero non-essential animated nodes and no more than 12 observed layers.
- Ambient and Share must become visible within 500 ms and 600 ms respectively under this synthetic profile.
- Ambient should not regress below 45 rAF callbacks/s or above 50 layers in the same headless profile. This is a regression signal, not a 60 FPS claim.

### Verified product target

- Viewer shell visible within 2,500 ms even when the cover request never finishes: passed in the dedicated pending-request regression and in both targeted performance runs.

### Remaining P1 backlog

- Archive progressive rendering: current six-date production data remains at 1,692 DOM nodes, 19 long tasks totaling 2,333 ms, and a 164 ms maximum rAF gap.
- Ambient compositing: the baseline remains at 45 layers and about 53 rAF callbacks/s under the synthetic profile.
- Startup layout stability: desktop CLS remains 0.646 and mobile CLS remains about 0.53.

These items were not changed during the Viewer cover fix.

### Failing product targets

- Initial-load CLS at or below 0.10 on desktop and mobile.
- No interaction-related event or long task above 200 ms when opening Viewer or switching albums on the low-performance profile.
- Archive maximum rAF gap below 100 ms and long-task total below 1,000 ms for the current six-date production dataset.

## Measurement limits

- Valid INP is a field metric gathered from real user interactions over a page lifetime. This synthetic baseline records Event Timing maxima and interaction-to-visible time instead; it must not be presented as field INP.
- Headless Chrome is not display-vsynced, so rAF callback throughput can exceed 60/s. Only relative same-machine comparisons are meaningful.
- Cover decode timing could not be established because most remote covers did not finish loading during the measurement window. The harness records URL, completeness, intrinsic/display dimensions, and request evidence; a future successful-cover run should add a decoded-image timing sample.
- React commit-hook events identify update volume, not the component or whether a render was avoidable. A React Profiler trace is required before changing component boundaries or memoization.
- Results describe this Windows machine, system Chrome, the 2026-07-12 production dataset, and Cloudflare cache state. Repeat the audit after dataset growth, large visual changes, or a browser/toolchain change.
