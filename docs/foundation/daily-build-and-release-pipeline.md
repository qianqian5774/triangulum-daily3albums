# Daily Build And Release Pipeline

本文说明 Triangulum Daily 3 Albums 如何作为无后端 GitHub Pages 静态站成立。

## Architecture Overview

项目当前有四层：

- Python generator：获取候选、归一化 metadata、写静态 JSON，并把站点资产复制到 `_build/public`。
- React / Vite UI：构建静态前端到 `ui/dist`。
- Static JSON：浏览器读取 `today.json`、archive JSON、`index.json` 和 `meta.json`。
- GitHub Actions / GitHub Pages：定时或手动 workflow 构建静态输出，并作为 Pages artifact 发布。

浏览器不会生成每日数据。它只读取已发布的静态文件，并在运行时按 BJT 解锁规则控制显示。

## Local Build Flow

常用本地验证意图包括：

```powershell
C:\Users\11836\AppData\Local\nvm\v22.13.0\npm.cmd --prefix ui test
C:\Users\11836\AppData\Local\nvm\v22.13.0\npm.cmd --prefix ui run build
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m doctor.run_doctor
.\.venv\Scripts\daily3albums.exe doctor
.\.venv\Scripts\daily3albums.exe build --verbose --out _build\public
.\.venv\Scripts\python.exe scripts\self_check.py --path _build\public
```

自动化执行时应按仓库 `AGENTS.md` 或当前运行环境使用固定 Node/npm、Python 和 CLI 路径，不要依赖全局 `npm`、`python` 或 `daily3albums`。

只改 Markdown 时，不强制跑全量本地构建。若改到源码、workflow、配置、package、pyproject、lockfile 或构建脚本，应视为本任务越界或需要重新评估验证范围。

`_build/public` 是最终静态站点输出，不提交。`ui/dist` 是 UI build 产物，也不提交。

## GitHub Actions Pages Workflow

主 Pages workflow 是 `.github/workflows/pages_daily.yml`，名称为 `Build and Deploy Pages (Daily)`。

当前触发方式：

- `workflow_dispatch`，包含可选 `tag`，以及 `n`、`topk` 输入。
- `schedule`，当前为 UTC 21:17，即 Asia/Shanghai 次日 05:17。

当前 build job 结构：

1. Checkout。
2. Jitter，避免 cron stampede。
3. Setup Python 3.11，并启用 pip cache。
4. Start build metrics。
5. Install Python package with doctor extras。
6. Setup Node 24，并按 `ui/package-lock.json` 使用 npm cache。
7. `npm --prefix ui ci`。
8. Run UI tests。
9. Run Python tests。
10. Restore `.state` cache。
11. Prune old `.state` JSONL files。
12. Build UI。
13. Restore published archive seed 到 `.state/pages-history-seed/data`，并使用 `--max-days 7`。seed source 可由 `DAILY3ALBUMS_PAGES_BASE_URL` 覆盖；未设置时保持当前 GitHub Pages project URL fallback，避免 custom domain 尚未生效前丢失 archive seed。
14. 设置 `DAILY3ALBUMS_HISTORY_SEED_DIR`，运行 `daily3albums build --skip-ui-build`，并接入 workflow_dispatch 输入。
15. 写入 `_build/public/data/meta.json`。
16. 运行 `scripts/self_check.py --path _build/public`。
17. Summarize build metrics。
18. Summarize recommendation observability。
19. Maintain `.state/cache.sqlite`。
20. Upload Pages artifact from `_build/public`。
21. 失败时向 GitHub issue 报告。

deploy job 随后用 `actions/deploy-pages` 发布 Pages artifact。

另一个 `.github/workflows/ci.yml` 在 push 和 pull request 上运行。它使用 fixtures 做 Python dry-run/golden checks，然后安装 UI 依赖并运行 UI tests。

## Data Generation Flow

每日生成流程：

1. 读取环境变量和配置。
2. 确定当前 Asia/Shanghai 日期和 slot。
3. 如果设置了 `DAILY3ALBUMS_HISTORY_SEED_DIR`，恢复已发布 archive seed。
4. 读取最近 archive history，用于 artist/theme cooldown context。
5. 对 3 个 slots 分别执行：
   - 从 tag pool 选择候选 tags，
   - 获取 Last.fm candidates，
   - 可选合并 Discogs candidates，
   - 可选合并 ListenBrainz candidates，
   - 通过 MusicBrainz 归一化 candidates，
   - scoring 和 prefilter，
   - hard filters，
   - weighted sample 出 3 个 unique-artist picks，
   - 分配 Headliner / Lineage / DeepCut 标签。
6. 为最终 picks 获取 cover 和 MusicBrainz details。
7. 仅在 MusicBrainz 提供 Wikipedia URL relation 时获取 Wikipedia overview。
8. validate issue。
9. 复制 static frontend 和 web assets 到 output。
10. 写入 `today.json`、archive JSON、`index.json` 和 `recommendation-observability.json`。

## Archive Retention

Archive retention 的含义是“最多 7 个有数据的唯一日期”，不是固定保证最近 7 个自然日每天都有数据。

当前来源：

- `config/config.yaml` 设置 `history.archive_retention_days: 7`。
- `write_daily_artifacts()` 把 retention value 写入 `data/index.json`。
- Archive seed restore 使用 `--max-days 7`。
- `getRecentArchiveEntries()` 读取 `index.archive_retention_days` 并按 date 去重。

当可用日期少于 7 个时，Archive Page 展示实际可用日期，并可显示 partial-history 文案。Archive Page 先依赖 `index.json`，再加载每个 entry 指向的 archive JSON。

## Build Metrics

`scripts/build_metrics.py` 记录 step timings 和静态输出指标。Pages workflow 用它包装主要步骤，并在 `if: always()` 下输出 summary。

在 GitHub Actions 中，build metrics 默认写入 runner 临时目录：

```text
${RUNNER_TEMP}/daily3albums-build-metrics/${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}
```

本地非 Actions 环境仍回退到 `.state/build-metrics`。workflow 恢复 `.state` cache 后会删除 legacy `.state/build-metrics`，因此 `.state` cache 不能覆盖当前 run 的 metrics。metrics 文件会记录 `GITHUB_RUN_ID` 和 `GITHUB_RUN_ATTEMPT`；summary 只读取当前 run/attempt 的 step rows，发现旧 rows 时会忽略并在 summary 中输出 warning。

当前 public metrics 包括：

- Public size
- Public size bytes
- Archive retention days
- Archive dates in index
- Archive visible albums
- Today albums
- Total measured duration
- Step timings
- Missing archive JSON dates, if present

这些指标用于观察 GitHub Pages artifact size、archive 增长、构建健康和步骤耗时。不要把失败 workflow 中的 `0 B`、`n/a`、`0` 等占位值写成有效 baseline。

## Custom Domain Cutover

目标公开域名是 `https://triangulumdaily.space/`。当前 UI 使用 Vite `base: "./"`、HashRouter 和 `resolvePublicPath()` 拼接 `data/...` 与 `assets/...`，因此静态 artifact 应能从 domain root `/` 预览和部署，不应要求 `/triangulum-daily3albums/` 子路径。

Archive seed restore 的部署顺序需要保守处理：在 DNS、GitHub Pages custom domain 和 HTTPS 尚未完成前，workflow 不应默认从新域名恢复历史 archive。等 `https://triangulumdaily.space/` 已能稳定提供 `data/index.json` 后，再把 repository variable `DAILY3ALBUMS_PAGES_BASE_URL` 设置为 `https://triangulumdaily.space/`，并手动触发 `Build and Deploy Pages (Daily)`。

详细人工切换步骤见 `docs/runbooks/custom-domain-cutover.md`。

## Recommendation Observability

daily build 会生成 `_build/public/data/recommendation-observability.json`。该文件记录每个 slot 的 candidate counts、source share、rejection reasons、final picks metadata coverage、year/region/language coverage 和 enrichment success rate。

Pages workflow 通过 `scripts/recommendation_observability_summary.py` 把该 JSON 渲染到 GitHub Actions Summary。Summary 包含每个 slot 的 candidate counts 表、source share 表、rejection reasons 总览、最终 9 张 metadata coverage 和 enrichment success rate。

这些输出只用于构建期观测，不改变推荐算法权重、最终 picks 选择逻辑、Today Page 或 Archive Page 的用户体验。当前 schema 不提供 region/country/language 时，summary 会说明 unavailable，不会推断地区、语言、性别或年代均衡已经实现。

## Runtime Logic

浏览器运行时：

- 使用 HashRouter 提供 `#/` 和 `#/archive`；
- 从静态站 fetch `data/today.json`、`data/index.json` 和 archive JSON；
- 在 `ui/src/lib/bjt.ts` 中计算 BJT state；
- 把 00:00-05:59 视为 Offline State；
- 在 06:00、12:00、18:00 解锁 Today Page slots；
- 支持 `debug_time` 和 Time Lab 做确定性 UI 检查；
- Archive Page 读取 archive index 和 archive JSON；
- Share Card 只基于当前 BJT 已解锁 slots 生成版本；
- Share Card 不应提前泄露未来 slot。

如果公开 JSON 中包含绝对 cover URL，浏览器仍可能加载远端封面图片。这是资源依赖风险，不是访客端音乐 API 数据源。

## Static Architecture Boundary

GitHub Pages 不能在访客访问时写入新数据。任何需要写入、用户状态、账号、评论、实时 API、个性化历史或播放器服务的功能，都必须另开架构讨论。

不要用访客端调用外部音乐 API 的方式绕过当前静态 build 模型。

## Source basis

Verified from source:
- Python package 和 CLI entrypoint：`pyproject.toml`。
- Vite UI build/test scripts：`ui/package.json` 和 `ui/vite.config.ts`。
- Pages workflow 与 CI workflow：`.github/workflows/pages_daily.yml` 和 `.github/workflows/ci.yml`。
- 生成器 build flow：`daily3albums/cli.py`、`daily3albums/dry_run.py`、`daily3albums/artifact_writer.py`。
- Archive seed restore：`scripts/restore_static_archive_seed.py`。
- Build metrics：`scripts/build_metrics.py`。
- Recommendation observability：`daily3albums/cli.py`、`scripts/recommendation_observability_summary.py`。
- 输出验证：`scripts/self_check.py`。
- runtime data 和 BJT 行为：`ui/src/lib/data.ts`、`ui/src/lib/archive.ts`、`ui/src/lib/bjt.ts`、`ui/src/lib/share-card.ts`。

Inferred from current behavior:
- 项目能运行在 GitHub Pages 上，是因为所有可变数据生成都发生在 deploy 前。
- Archive 是从已发布站点恢复并滚动写入的静态数据集，不是数据库。

Not implemented / Not confirmed:
- 访客端写入、账号、评论、播放器服务、数据库和实时音乐 API 调用未实现。
- Markdown-only 文档变更不要求全量本地 build。
