# R8 High-confidence Dead Code Audit

## Scope conclusion

R8 is a deletion-only engineering cleanup after R6 and R7. It does not change
normalization, scoring, temperature, cooldown, tag selection, roles, provider
requests, public JSON, UI presentation, archive compatibility or error
semantics.

The pre-delete audit found no material dependency or Git/Foundation conflict.
The five local Foundation files remain protected local modifications and are
outside the R8 commit. The formal route is maintained separately from the
repository.

## Search method

The audit checked:

- tracked-file inventory and zero-byte files;
- repository-wide symbol, filename and asset references with `git grep`;
- Python imports, package discovery, CLI parser and runtime call sites;
- UI imports, feature-flag consumers, Vite public-copy behavior and source
  policy tests;
- GitHub Actions workflows, `ui/package.json`, `pyproject.toml`, AGENTS,
  runbooks, active docs and historical audits;
- broad `web/` and Vite copy chains, including resources present only because
  a whole directory is copied;
- manual tools, compatibility readers, fixtures, golden validation,
  normalization evidence and archive recovery escape hatches;
- the retained production Pages artifact to distinguish a copied file from a
  consumed runtime resource.

Dynamic references were treated conservatively. A filename absent from static
imports was not deleted if a package script, workflow string, broad copy/glob,
manual procedure, compatibility path or active visual authority still gave it
value.

## Candidate matrix

| Candidate | Search range | Current references | Manual entry | Compatibility value | Decision |
| --- | --- | --- | --- | --- | --- |
| `daily3albums/alerter.py` | Python imports, CLI, workflows, tests, docs | Zero-byte file; historical audit only | None | None; SMTP declarations already retired | delete |
| `daily3albums/engine.py` | Python imports, package discovery, CLI, tests | Zero-byte file; orchestration is in `cli.py` | None | None | delete |
| `daily3albums/image_optimizer.py` | Python imports, cover path, tests | Zero-byte file; cover policy uses adapter URLs/SVG fallback | None | None | delete |
| `daily3albums/log_jsonl.py` | Python imports, logging, workflows | Zero-byte file; no logger consumer | None | None | delete |
| `daily3albums/r2_state.py` | Python imports, CLI, workflows | Zero-byte file; no R2 runtime command | None | None | delete |
| `scripts/bootstrap_pages.ps1` | CLI/package/workflow/docs/manual entry search | Zero-byte file; historical audit only | None | None | delete |
| `ui/src/components/BioClock.tsx` | UI imports, routes, tests, flags | Component definition only; no import or render | None | None; shared product clock is authoritative | delete |
| `FLAGS.bioClock/fullscreen/i18n` | All UI source/tests | Declared but never read | None | None | delete |
| `_weighted_sample()` | Python calls, tests, docs | Definition only; production calls `_weighted_sample_unique_artists()` | None | None | delete |
| `_ensure_nonblank_index_html()` | Python calls, tests, build flow | Definition only; current build requires and copies `ui/dist` | None | None | delete |
| `scripts/make_placeholder.py` | Package/workflow/docs/import search | Self-references only; sole Pillow consumer | One-off script, undocumented | None; production fallback is `assets/placeholder.svg` | delete |
| `web/assets/placeholder.webp` | JSON/UI/CSS/source/tests and production artifact | Present only through broad `web/` copy; no runtime URL uses it | Generated only by deleted helper | None | delete |
| Python `pillow` dependency | Python imports and package metadata | Used only by deleted placeholder helper | None after helper removal | None | delete |
| `_threshold_steps()` | Current source/tests/docs/history | Not present on current `main`; only historical audit text remains | None | R6 policy authority is elsewhere | defer; no current target |
| `_now_date_in_tz()` | Current source/tests/docs/history | Not present on current `main`; only historical audit text remains | None | Current BJT clock uses active helpers | defer; no current target |
| `_builtin_min_index_html()` | Python calls/tests/docs | Directly imported by `tests/test_product_copy.py` | Diagnostic fallback content | Test/maintenance value remains | retain |
| `scripts/update_golden.ps1` | Workflows/docs/manual tools | Manual-only wrapper for active golden checker | Yes | Fixture maintenance value; toolchain portability needs separate decision | retain |
| `ui/public/brand/slot-window-set-vertical.svg` | UI/CSS/tests/art docs/public copy | Referenced by an unused CSS custom property and copied by Vite | Potential visual reference | No confirmed replacement visual asset yet | defer |
| Share template SVG | UI/tests/public copy | Product-copy test and Share Card visual reference | Yes | Current product asset | retain |
| R6 old `normalization_shadow` reader branches | Python scripts/tests/workflow | Active backward-compatible summary reader | No direct CLI beyond summary script | Required for retained old artifacts | retain |
| Normalization evidence sanitizer/upload | Python tests and Pages workflow | Active generation and 30-day artifact upload | Workflow entry | Required R6 evidence boundary | retain |
| Archive legacy fixtures/readers and `force_archive_rewrite` | Python/UI tests, CLI, runbooks | Active compatibility and maintenance safety paths | Yes | Explicitly required | retain |
| `docs/legacy/`, `docs/revive/`, Foundation snapshots | Documentation policy and AGENTS | Historical/audit authorities | Yes | Explicitly required | retain |

## Deleted set and behavior boundary

The deletion set removes five empty Python modules, one empty PowerShell
script, one unrendered React component, three unused flag fields, two uncalled
Python helpers, the one-off WEBP generator/output and its now-unneeded Pillow
dependency.

`web/` itself remains active because the build copies it and self-check still
requires its archive fallback surface. Removing `placeholder.webp` changes
only an unreferenced extra file in the static payload; generated JSON and UI
fallback URLs continue to use `assets/placeholder.svg`.

No old observability reader, legacy archive path, fixture, golden expectation,
recovery/maintenance command, workflow step or active package script is
removed.

## Dynamic and manual entry checks

- Setuptools package discovery can include empty modules, but no import,
  entrypoint or dynamic module string names the five deleted files.
- Vite and `daily3albums build` copy public directories broadly. That explains
  why the unused WEBP appears in production output, but no HTML, CSS, JS, JSON,
  Python or test consumer requests it.
- Active `FLAGS` consumers remain `dominantViewport`, `viewerOverlay` and
  `organicGlitch`; only unread keys are removed.
- `update_golden.ps1` remains because it is a real manual fixture tool despite
  its portability issue. R8 does not convert a potentially useful manual
  entry into dead code merely because it is undocumented.
- The stale slot-window SVG is deferred because the active art-direction layer
  has not supplied a confirmed replacement asset. Its eventual removal belongs
  with an explicit UI/visual authority decision.

## Expected impact

- Build/workflow/UI: no active import, step or render path changes.
- Public artifacts: issue/index/observability schemas and referenced resources
  are unchanged; one unreferenced WEBP is no longer copied.
- Recommendation policy: final selection, normalization tiers, candidate
  order, request ledger, scoring, sampling, cooldown and role assignment are
  unchanged.
- Operations: restore, self-check, metrics, summaries, evidence upload, cache
  maintenance, deploy and manual archive rewrite remain available.

## Local validation

The implemented deletion set passed:

- Python compileall;
- the complete Python suite: 230 passed, 23 skipped;
- the complete UI unit suite: 104 passed;
- the production UI build;
- CLI top-level and build help;
- fixture dry-run with the optional local Discogs credential explicitly
  disabled to match CI behavior;
- the active golden checker;
- `scripts/self_check.py` against the retained production Pages artifact after
  removing only the unreferenced WEBP;
- Playwright mobile-layout smoke, Viewer cover behavior, deterministic Today
  stale/last-good/archive recovery, and shared product-clock regression: 12
  tests passed in total;
- final whitespace and active-reference checks.

A separate real-provider build reached MusicBrainz normalization and stopped
after repeated `ConnectTimeout` responses exhausted the candidate pool. The
failure was classified as the existing external `timeout` semantic and did
not reference any deleted module, helper, flag, asset or dependency. It is
recorded as an external network limitation, not as a successful full local
generation or an R8 regression.

## Known deferred items

- Decide the stale slot-window visual asset only when a replacement visual
  authority exists.
- If desired, make `update_golden.ps1` portable across machine-local fixed
  toolchains in a separate maintenance task.
- `_threshold_steps()` and `_now_date_in_tz()` require no R8 edit because they
  are already absent from current source; historical references remain
  historical evidence.

This document intentionally does not pre-write CI, merge, branch cleanup or
post-merge Foundation facts.
