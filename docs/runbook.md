# Daily3Albums Runbook

## Active validation entry points

Doctor 已退役，不再生成 `doctor/REPORT*` 或 `doctor/runs/`，也不再作为健康依据。根据改动范围选择以下真实入口：

| 验证目标 | 命令或证据 |
| --- | --- |
| Python 行为 | `python -m pytest` |
| UI 行为 | `npm --prefix ui test` |
| UI production bundle | `npm --prefix ui run build` |
| 完整静态产物 | `daily3albums build --verbose --out _build/public` |
| 公开 JSON 与站点产物一致性 | `python scripts/self_check.py --path _build/public` |
| 真实浏览器 smoke | `npm --prefix ui run browser:smoke`，要求已有 `_build/public` |
| 独立性能基线 | `npm --prefix ui run performance:audit`，见仓库根目录 `PERFORMANCE.md` |
| 每日生产链路 | GitHub Actions 的 `Build and Deploy Pages (Daily)` |
| 构建指标 | workflow 中的 `scripts/build_metrics.py` summary |
| 推荐漏斗 | workflow 中的 `scripts/recommendation_observability_summary.py` summary |

机器专用的 executable 路径和浏览器 channel 以本地 `AGENTS.local.md` 为准。Doctor 的历史设计和能力迁移表见 [legacy/doctor.md](legacy/doctor.md)。

## Custom domain cutover

Use [custom-domain-cutover.md](runbooks/custom-domain-cutover.md) for the `triangulumdaily.space` GitHub Pages and Porkbun handoff.

## Where to find logs

- GitHub Actions runs: **Actions → Build and Deploy Pages**
- Click the latest run to inspect the build job logs and artifact steps.

## Re-run the workflow

1. Open **Actions → Build and Deploy Pages**.
2. Select a failed run.
3. Click **Re-run jobs → Re-run all jobs**.

## Clear / refresh cache

The pipeline caches `.state/` for dedupe and rate limits.

To refresh it:

1. Go to **Actions → Caches** in the repository.
2. Delete the cache keys starting with `state-`.
3. Re-run the workflow to rebuild a clean cache.

## Roll back to last known-good deployment

1. Identify the last successful commit in **Actions** or **Pages → Deployments**.
2. Reset `main` (or create a revert commit) to that SHA.
3. Re-run **Build and Deploy Pages** to publish the known-good build.
