# Triangulum Daily runbook

This runbook describes current operational entry points. It does not replace the source, workflow, or Foundation documentation.

## Validation entry points

| Goal | Command or evidence |
| --- | --- |
| Python behavior | python -m pytest |
| UI behavior | npm --prefix ui test |
| Production UI bundle | npm --prefix ui run build |
| Complete static artifact | daily3albums build --verbose --out _build/public |
| Public artifact consistency | python scripts/self_check.py --path _build/public |
| Real-browser smoke | npm --prefix ui run browser:smoke |
| Record Shop browser path | npm --prefix ui run browser:record-shop |
| Performance evidence | npm --prefix ui run performance:audit |
| Daily production path | GitHub Actions: Build and Deploy Pages (Daily) |

Use the machine-specific executables and browser channel described by AGENTS.local.md. Doctor is retired; it is not a health, build, or release command.

## Normal release

1. Merge reviewed code through the normal main branch process.
2. When an immediate publication is required, manually dispatch Build and Deploy Pages (Daily).
3. Confirm the workflow completed its test, archive-seed restore, build, self-check, Pages-upload, and deploy jobs.
4. Inspect the deployed site and its same-origin static data: data/today.json, data/index.json, archive JSON, and the Record Shop at the root URL.

Do not use fixtures, a dev seed, manually constructed issue JSON, or an archive-rewrite flag to make a production release appear current. A same-date published archive may be reused by the normal workflow.

## Archive and cache handling

The workflow restores validated published archive history before selection and retains a safe local seed when a refresh fails. Do not delete state caches as a routine cure for an archive problem. First inspect the failing archive-seed step, its validation summary, and the published data it attempted to restore.

## Incident recovery

For a code regression, prepare a reviewed revert or focused repair through the normal Git process, then run the normal Pages workflow. Do not reset shared main history, bypass contract/self-check gates, or publish generated files by hand.

The canonical public URL is https://triangulumdaily.space/. Domain-specific checks are in [runbooks/custom-domain-cutover.md](runbooks/custom-domain-cutover.md).
