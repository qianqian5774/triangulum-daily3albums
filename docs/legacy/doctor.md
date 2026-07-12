# Doctor retirement record

## Status

Doctor 已退役，不是当前验证入口，也不再由 `AGENTS.md` 提供可解析的 `doctor_plan`。

以下入口已删除：

- `python -m doctor.run_doctor`
- `daily3albums doctor`
- `doctor/REPORT.md`
- `doctor/REPORT.json`
- `doctor/runs/<run_id>/`

不要根据旧 Doctor report 判断仓库、生产构建或网页健康状态。

## Why it was retired

Doctor 最初用于本地工作区和浏览器可见性不足时，把配置、外部探测、构建、产物检查和 Render QA 包装成一个顺序执行框架。

后续实现没有完成原规格。尤其是所谓 Render QA 没有启动 Playwright，也没有访问页面；它只写入一个固定 `today.desktop.json`，其中 console、network、links 为空，overflow 为 false，a11y violations 为 0，data consistency 为 `not_run`。这类占位输出可能被误读为健康证据，因此不再保留或补完。

## Capability migration

| Former Doctor intent | Active destination |
| --- | --- |
| Config and Python behavior | `python -m pytest` and direct CLI execution |
| Last.fm / MusicBrainz probes | Explicit `daily3albums probe-lastfm` and `daily3albums probe-mb` commands when a bounded network probe is actually required |
| UI unit behavior | `npm --prefix ui test` |
| Production UI bundle | `npm --prefix ui run build` |
| Full static generation | `daily3albums build --verbose --out _build/public` |
| Generated JSON and public artifact checks | `python scripts/self_check.py --path _build/public` |
| Real page behavior and responsive layout | `npm --prefix ui run browser:smoke` |
| Performance/network/layout evidence | `npm --prefix ui run performance:audit` and `PERFORMANCE.md` |
| Production build duration and artifact counts | Build Metrics in the daily workflow |
| Candidate funnel and final-pick diagnostics | Recommendation Observability in the daily workflow |
| Deployment health | GitHub Actions build/deploy jobs and production verification |

No valid check was left exclusively inside Doctor. The fake Render QA artifact was deleted rather than migrated.

## Historical plan outline

The retired `doctor_plan` described these sequential steps:

1. overview and entrypoint discovery;
2. Last.fm and MusicBrainz configuration checks;
3. one-request external probes with rate-limit delay;
4. optional soft probes;
5. static-site build;
6. JSON artifact and slot validation;
7. desktop/mobile Render QA for Today, Archive, and Treatment Viewer.

Its intended report schema contained `meta`, `overall_status`, `steps`, `checks`, and `issues`, with logs and UI audit JSON under `doctor/runs/`. That schema is historical only. Current checks report through their native test output, build logs, ignored Playwright/performance artifacts, and GitHub Actions summaries.

The original full specification remains recoverable from Git history before Doctor retirement; it must not be copied back into active `AGENTS.md`.
