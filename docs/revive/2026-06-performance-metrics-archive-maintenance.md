# 2026-06 Performance, Build Metrics, and Archive Maintenance

审计日期：2026-06-26
范围：页面交互性能小范围缓解、GitHub Actions build metrics、Archive 从最近 3 个有数据日期扩展到 7 个有数据日期。

## 阶段结论

本轮没有重写 UI，也没有改变静态站架构。改动集中在三个低风险点：

- Archive retention 从 3 改为配置化 7，并由 `data/index.json` 暴露给前端。
- GitHub Actions 关键步骤通过 `scripts/build_metrics.py` 记录耗时，并在 `$GITHUB_STEP_SUMMARY` 输出产物指标。
- UI 降低部分 overlay / ambient / share export 的常驻渲染成本。

## Archive 7 天历史

定位结果：

- 生成器限制：`daily3albums/artifact_writer.py` 原先只保留 3 个 unique dates 并 prune archive 文件。
- seed 恢复限制：`.github/workflows/pages_daily.yml` 原先调用 `restore_static_archive_seed.py --max-days 3`。
- 前端限制：`ui/src/lib/archive.ts` 原先默认只取最近 3 个 unique dates。
- 文案和测试：`ui/src/strings/copy.ts`、`ui/src/lib/archive.test.ts`、`tests/test_artifact_writer.py`、`tests/test_static_archive_seed.py` 都有 3 天假设。

本轮实现：

- `config/config.yaml` 增加 `history.archive_retention_days: 7`。
- `daily3albums/config.py` 读取该配置。
- `write_daily_artifacts()` 接收 `archive_retention_days`，写入 `data/index.json` 的 `archive_retention_days` 字段。
- 前端 `getRecentArchiveEntries()` 优先使用 `index.archive_retention_days`，少于 7 天时展示实际数量。
- Archive 仍然基于静态 `data/index.json` 和 `data/archive/...json`，不引入后端、数据库或浏览器端写入。

## Build Metrics

新增 `scripts/build_metrics.py`：

- `start`：记录总耗时起点。
- `run --name ... -- <command>`：执行命令并向 `.state/build-metrics/steps.jsonl` 写入 command、exit_code、duration_ms。
- `summarize`：读取 `_build/public`，输出：
  - `public_size_bytes`
  - `public_size_human`
  - `archive_retention_days`
  - `archive_day_count`
  - `archive_album_count`
  - `today_album_count`
  - `generated_at`

Workflow 覆盖：

- Python package install
- npm ci
- UI test
- pytest
- UI build
- archive seed restore
- daily3albums build
- self_check
- total measured duration

Metrics summary 使用 `if: always()` 和 `continue-on-error: true`，避免 metrics 自身问题阻断 Pages 发布。

## 页面性能风险点与缓解

审计到的主要风险：

- Treatment Viewer backdrop 使用全屏 blur，打开/关闭时可能触发较重合成。
- Share Card Dialog 常驻隐藏导出画布，打开弹窗时即存在一份 1080x1440 export DOM。
- Ambient idle mode 同时存在 gradient blur、noise、grid、signal、ghost 多层动画。
- SlotCard mousemove tilt 已有 requestAnimationFrame throttle，但非交互卡片也会进入 handler。

本轮实际改动：

- Treatment Viewer backdrop 改为自定义 `.viewer-backdrop`，降低 blur 强度。
- `.viewer-dialog`、`.share-dialog` 增加 `contain: layout paint`，降低局部 reflow/paint 影响面。
- SlotCard 非交互状态不再处理 mousemove tilt。
- Ambient gradient blur 降低，noise 和 ghost 动画变慢，阴影强度降低。
- Reduced Motion 下隐藏 ambient gradient/noise/signal 层，并关闭相关动画。
- Share Card export root 默认 `display: none`，仅导出时通过 `flushSync` 短暂显示，避免弹窗打开即布局/绘制隐藏大画布。

暂不处理：

- 不移除夜间酸性信号美术。
- 不重写 framer-motion shared layout。
- 不把所有 cover image 本地化；该项留给 metadata/asset pipeline 后续处理。
- 不新增复杂性能采样 harness；本轮用 build/test/browser smoke 验证交互不破。

## 仍需关注

- 外部封面 URL 仍可能让访客浏览器加载远端图片资源。
- `daily3albums doctor` 仍不是完整端到端 render doctor；本轮没有实现 AGENTS.md 中的新 doctor 合约。
- Archive 7 天取决于 GitHub Pages 已发布 index 和 seed 恢复结果；历史不足 7 天时前端只显示实际可用日期。
