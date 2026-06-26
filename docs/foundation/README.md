# Project Foundation Docs

`docs/foundation/` 是 Triangulum Daily 3 Albums 的 canonical project docs。这里保存可以长期引用的项目底层说明，面向维护者和后续 Codex 任务，不是产品宣传文案，也不是阶段审计报告。

后续讨论架构、外部 API、推荐算法、构建发布链路或 UI 术语时，优先引用本目录。引用前仍应记住：源码、配置、测试和 workflow 是最终事实来源。

## Documents

- [UI terminology](./ui-terminology.md)
- [Data sources and API boundaries](./data-sources-and-api-boundaries.md)
- [Recommendation system](./recommendation-system.md)
- [Daily build and release pipeline](./daily-build-and-release-pipeline.md)

## Relationship to docs/revive

`docs/revive/` 保存历史审计、恢复笔记和临时任务记录。它适合查找背景、阶段原因和旧问题脉络，但不应继续承担权威项目说明的角色。

从 `docs/revive/` 迁移长期有效内容时，必须先核对当前源码、配置、测试、workflow 或 README。旧审计、聊天摘要和任务说明不能直接写成已实现事实。

## Source of truth

当本目录文档与当前源码、配置、测试或 workflow 冲突时，以当前源码和配置为准。确认差异后应更新本目录文档。

不要把计划、愿望、旧审计结论或一次性任务指令写成已经实现的项目行为。

## Source basis

Verified from source:
- 当前仓库包含 `docs/revive/`、`docs/runbook.md`、`daily3albums/`、`ui/src/`、`config/`、`scripts/`、`tests/` 和 GitHub workflows。
- 当前项目已有稳定的 UI、生成器、数据产物和 Pages 发布实现面。

Inferred from current behavior:
- 独立的 `docs/foundation/` 层能让长期事实比混在 revive 记录中更容易复用。

Not implemented / Not confirmed:
- 本目录不替代源码、测试、workflow 或运行验证作为最终事实来源。
