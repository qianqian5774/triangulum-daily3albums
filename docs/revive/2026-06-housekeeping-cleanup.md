# 2026-06 Housekeeping Cleanup

日期：2026-06-13  
分支：`housekeeping/remove-stale-root-artifacts`  
范围：仅处理 `logs/adapters.log`、`logs/build.log`、`run_ambient_debug.txt`、`web/`、`REVIEW_REPORT.md`。

## 总览

| 路径 | 检查结果 | 决定 | 删除/移动/保留原因 | 是否发现敏感信息 |
|---|---|---|---|---|
| `logs/adapters.log` | `daily3albums/request_broker.py` 会写入同名日志；没有发现测试、构建、CI 或文档读取当前 tracked 文件内容 | 删除 tracked 文件，保留 `logs/.gitkeep` | 当前文件是历史运行日志，不应作为源码提交；后续由本地运行重新生成并被 `.gitignore` 忽略 | 未发现未脱敏 key；包含外部请求 URL，`api_key` 均为 masked 形式 |
| `logs/build.log` | `daily3albums/cli.py` 会写入同名日志；没有发现测试、构建、CI 或文档读取当前 tracked 文件内容 | 删除 tracked 文件，保留 `logs/.gitkeep` | 当前文件是历史构建日志，不应作为源码提交；后续由本地运行重新生成并被 `.gitignore` 忽略 | 未发现未脱敏 key；包含外部请求 URL，`api_key` 均为 masked 形式 |
| `run_ambient_debug.txt` | `git grep` 未发现当前源码、构建、CI、测试或文档引用 | 删除 tracked 文件 | 只是历史 ambient debug/cache 输出，不被流程依赖 | 未发现未脱敏 key；包含外部请求 URL，`api_key` 为 masked 形式 |
| `web/` | `daily3albums build` 当前仍会复制 `web/` 到输出；`scripts/make_placeholder.py` 写入 `web/assets/placeholder.webp`；`scripts/self_check.py` 检查输出中的 `archive.html` | 保留 | 仍被当前 build/fallback 静态资源流程引用，不能在 housekeeping 中删除 | 未检查到该目录内敏感信息迹象 |
| `REVIEW_REPORT.md` | `git grep` 未发现 README、AGENTS、docs、workflow、源码、脚本、测试或 UI 引用 | 移动到 `docs/archive/REVIEW_REPORT.md` | 内容是历史审计记录，有保留价值，但不应继续占据根目录 | 未发现敏感信息迹象 |

## 引用检查摘要

- `git grep -n -- "adapters.log"`：仅命中 `daily3albums/request_broker.py` 的日志写入路径。
- `git grep -n -- "build.log"`：命中 `daily3albums/cli.py` 的日志写入路径，以及 workflow 文案中的泛称 `build logs`，未发现读取 tracked `logs/build.log`。
- `git grep -n -- "run_ambient_debug.txt"`：无命中。
- `git grep -n -- "REVIEW_REPORT"`：无命中。
- `git grep -n -- "web"` / `git grep -n -- "web/"`：命中 `daily3albums/cli.py` 的 `web/` copy 流程和 `scripts/make_placeholder.py`，因此 `web/` 保留。
- Pages 发布流程上传 `_build/public`；`daily3albums build` 在写入 `_build/public` 前仍会复制 `web/` 与 `ui/dist`。

## 本次变更

| 变更 | 理由 |
|---|---|
| `git rm logs/adapters.log logs/build.log` | 移除历史运行日志，避免后续日志污染仓库 |
| `git rm run_ambient_debug.txt` | 移除历史 debug 输出 |
| `git mv REVIEW_REPORT.md docs/archive/REVIEW_REPORT.md` | 保留历史审计价值，同时清理根目录 |
| 更新 `.gitignore` | 修复 `run_ambient_debug.txt` 规则的异常 NUL 编码；新增 `logs/*.log`；保留 `!logs/.gitkeep` |
| 保留 `web/` | 当前构建链路仍引用 |

## 敏感信息检查

对 `logs/adapters.log`、`logs/build.log`、`run_ambient_debug.txt` 做了关键词抽查：`api_key=`, `api_key`, `Authorization`, `Bearer`, `token`, `secret`, `password`, `LASTFM`, `MUSICBRAINZ`。

结论：

- 三个文件都包含外部请求 URL 或 provider 名称。
- `api_key` 有命中，但提取到的值均为 `***` 或 `%2A` 这类 masked 形式。
- 未发现未脱敏的 Authorization/Bearer/token/secret/password。
- 这些文件仍不建议保留在仓库中，因为它们是运行输出且包含大量外部请求上下文。

## 后续建议

- 如果未来希望彻底移除 `web/`，应先调整 `daily3albums/cli.py` 的 build copy 流程、`scripts/make_placeholder.py`、`scripts/self_check.py` 和相关文档，再单独验证 Pages 输出。
- 如果运行日志需要保留证据，建议写入 `docs/revive/` 的人工摘要，而不是提交原始 `.log`。
- 本机 `.git/info/exclude` 仍忽略 `docs/revive/`，因此本报告在当前环境下会被普通 `git status -sb` 隐藏；若需要提交，需单独处理本地 exclude 或强制添加。
