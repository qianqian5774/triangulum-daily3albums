# 2026-06 Project Root Inventory Audit

审计日期：2026-06-12  
项目路径：`D:\projects\triangulum-daily3albums`  
当前分支检查结果：`## main...origin/main`  
范围：只盘点根目录与二级目录，不删除、不移动、不修改源码、配置、依赖、构建产物。

## 总览结论

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `daily3albums/`, `scripts/`, `tests/`, `config/`, `ui/src/`, `ui/package*.json`, `.github/` | 源码/配置/测试 | tracked | Python 生成器、脚本、测试、前端源码、CI 配置 | 是 | 是 | 否 | 项目核心文件，107 个 Git 跟踪文件主要集中在这些路径 |
| `.env`, `.state/`, `.venv/`, `ui/node_modules/`, `.pytest_cache/`, `__pycache__/`, `_build/`, `ui/dist/`, `daily3albums.egg-info/` | 本地生成物/依赖/缓存/构建产物 | ignored | 本地环境、缓存、依赖、构建输出 | 视本地需要 | 否 | 可按需清理 | 已被 `.gitignore` 或 `.git/info/exclude` 忽略，通常可重建；清理前注意 `.env` 和 `.state/cache.sqlite` 的本地价值 |
| `logs/adapters.log`, `logs/build.log`, `run_ambient_debug.txt` | 日志/调试输出 | tracked | 历史运行日志或 API cache debug 记录 | 需人工确认 | 需人工确认 | 不建议自动清理 | 这类文件更像生成物，但当前已纳入版本控制 |
| `web/` | 静态页面/历史遗留候选 | tracked | 旧静态入口或占位 Web 资源 | 需人工确认 | 需人工确认 | 不建议自动清理 | 当前主构建链路看起来由 `ui/` 与 `_build/public` 承担，`web/` 是否仍有发布用途需确认 |
| `docs/revive/` | 复健文档目录 | mixed | 审计、基线和阶段性记录 | 是 | 视文档策略 | 否 | 已有文件被跟踪，但本机 `.git/info/exclude` 又忽略整个目录，新报告也会被本地忽略 |

核心发现：

- `git ls-files` 当前跟踪 107 个文件。
- `git ls-files --others --exclude-standard --directory` 为空；写报告前没有非忽略的未跟踪文件。
- 被忽略项主要是本地环境、缓存、构建输出和 Codex 本地目录。
- 需要重点人工确认的不是未跟踪垃圾，而是已经 tracked 的疑似产物：`logs/adapters.log`、`logs/build.log`、`run_ambient_debug.txt`、以及可能是旧入口的 `web/`。
- `.gitignore` 输出中 `run_ambient_debug.txt` 一行疑似带 NUL 字符，`git check-ignore --no-index run_ambient_debug.txt` 未命中；如果未来想忽略该文件，需要修正规则并先决定是否从版本控制移除。

## 顶层目录清单

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.git/` | Git 内部目录 | local | Git 仓库元数据 | 是 | 否 | 否 | 必需的版本库内部状态，不属于项目提交内容 |
| `.github/` | CI 配置 | tracked | GitHub Actions workflow，含 CI 与 Pages daily 构建 | 是 | 是 | 否 | 发布和验证链路依赖 |
| `.codex/` | Codex 本地目录 | ignored by `.git/info/exclude:12` | Codex 会话/环境本地信息 | 视本地需要 | 否 | 可 | 本地工具目录，不应进入仓库 |
| `.pytest_cache/` | 测试缓存 | ignored by `.git/info/exclude:16` | pytest 运行缓存 | 否 | 否 | 可 | 可由测试重新生成 |
| `.state/` | 本地运行缓存 | ignored by `.gitignore:7` | `cache.sqlite` 与备份缓存，约 21.45 MB | 视本地运行需要 | 否 | 可谨慎清理 | 用于 API/cache 状态；删除会失去本地缓存但不应提交 |
| `.venv/` | Python 虚拟环境 | ignored by `.gitignore:1` | 本地 Python 依赖环境，约 63.75 MB | 视本地需要 | 否 | 可 | 可按 `pyproject.toml` 重建 |
| `_build/` | 构建输出 | ignored by `.gitignore:6` | 生成后的静态站点 `_build/public`，约 788.93 KB | 视验证需要 | 否 | 可 | 应由 `daily3albums build` 重新生成，不应提交 |
| `config/` | 配置 | tracked | 业务配置和 endpoint policy | 是 | 是 | 否 | 生成器运行依赖 |
| `daily3albums/` | Python 源码包 | mixed: tracked + ignored `__pycache__` | CLI、适配器、请求 broker、构建逻辑 | 是 | 是 | 否 | 核心源码；`__pycache__` 可清理 |
| `daily3albums.egg-info/` | Python packaging 产物 | ignored by `.gitignore:19` | editable/install 生成的元数据 | 否 | 否 | 可 | 可由安装过程重新生成 |
| `docs/` | 文档 | mixed: tracked + ignored local revive files | runbook、UI 文档、复健记录 | 是 | 视文档策略 | 否 | 正式文档应保留；本机排除规则会隐藏新增 `docs/revive/` 文件 |
| `doctor/` | Doctor 包 | tracked | `python -m doctor.run_doctor` 的体检入口 | 是 | 是 | 否 | 项目定义的诊断工具 |
| `logs/` | 日志目录 | tracked | `.gitkeep`、`adapters.log`、`build.log` | 需人工确认 | 需人工确认 | 只建议清理日志内容前先决策 | 当前日志文件已跟踪，不是普通 ignored 运行物 |
| `scripts/` | 工具脚本 | mixed: tracked + ignored `__pycache__` | self_check、golden check、placeholder 等 | 是 | 是 | 否 | 项目维护脚本；缓存可清理 |
| `tests/` | Python 测试 | mixed: tracked + ignored `__pycache__` | 单测、fixtures、golden 数据 | 是 | 是 | 否 | 验证链路依赖；缓存可清理 |
| `ui/` | 前端项目 | mixed: tracked + ignored `node_modules`, `dist` | React/Vite 静态站前端 | 是 | 是 | 否 | 源码和 lockfile 应保留；依赖和 build 输出不提交 |
| `web/` | 静态 Web 资源 | tracked | `index.html`、`archive.html`、placeholder、空 favicon | 需人工确认 | 需人工确认 | 不建议自动清理 | 可能是旧静态入口或占位资源，需确认是否仍被发布/引用 |

目录大小与时间摘要：

| 路径 | 子目录数 | 文件数 | 总大小 | 创建时间 | 修改时间 |
|---|---:|---:|---:|---|---|
| `_build/` | 5 | 12 | 788.93 KB | 2026-02-09 08:01:52 | 2026-02-09 08:01:52 |
| `.codex/` | 1 | 1 | 1.59 KB | 2026-06-12 22:18:44 | 2026-06-12 22:18:44 |
| `.git/` | 295 | 703 | 1.10 MB | 2026-02-09 02:02:01 | 2026-06-12 23:48:04 |
| `.github/` | 1 | 2 | 10.71 KB | 2026-02-09 02:02:03 | 2026-02-09 02:02:03 |
| `.pytest_cache/` | 2 | 5 | 2.83 KB | 2026-06-12 23:05:06 | 2026-06-12 23:05:06 |
| `.state/` | 0 | 2 | 21.45 MB | 2026-02-09 03:18:57 | 2026-06-12 23:12:16 |
| `.venv/` | 1190 | 4280 | 63.75 MB | 2026-02-09 03:02:21 | 2026-02-09 03:02:21 |
| `config/` | 0 | 2 | 9.21 KB | 2026-02-09 02:02:03 | 2026-02-09 07:59:36 |
| `daily3albums/` | 1 | 26 | 376.10 KB | 2026-02-09 02:02:03 | 2026-06-12 23:37:07 |
| `daily3albums.egg-info/` | 0 | 6 | 1.47 KB | 2026-02-09 03:04:27 | 2026-02-09 03:06:52 |
| `docs/` | 1 | 8 | 169.29 KB | 2026-02-09 02:02:03 | 2026-06-12 17:44:09 |
| `doctor/` | 0 | 2 | 10.44 KB | 2026-02-09 02:02:03 | 2026-06-12 17:17:15 |
| `logs/` | 0 | 3 | 2.98 MB | 2026-02-09 08:03:29 | 2026-02-09 08:28:08 |
| `scripts/` | 1 | 8 | 36.75 KB | 2026-02-09 02:02:03 | 2026-06-12 23:37:07 |
| `tests/` | 4 | 33 | 138.83 KB | 2026-02-09 02:02:03 | 2026-06-12 23:37:07 |
| `ui/` | 832 | 5633 | 112.28 MB | 2026-02-09 02:02:03 | 2026-06-12 23:12:14 |
| `web/` | 1 | 4 | 2.08 KB | 2026-02-09 02:02:04 | 2026-02-09 02:02:04 |

## 顶层文件清单

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.env` | 本地密钥/环境配置 | ignored by `.gitignore:13` | 本地 API key、运行环境变量 | 是，本地保留 | 否 | 不建议直接删 | 可能含密钥；只在报告中标注，不读取内容、不提交 |
| `.env.example` | 示例环境配置 | tracked | 展示必需环境变量格式 | 是 | 是 | 否 | onboarding 和 CI/本地配置参考 |
| `.gitattributes` | Git 配置 | tracked | Git 属性规则 | 是 | 是 | 否 | 仓库基础配置 |
| `.gitignore` | Git 忽略规则 | tracked | 排除虚拟环境、缓存、构建产物、密钥 | 是 | 是 | 否 | 需要维护；其中 `run_ambient_debug.txt` 规则疑似编码异常 |
| `AGENTS.md` | 项目/代理说明 | tracked | Codex/doctor 计划与项目约束 | 是 | 是 | 否 | 诊断与协作规则依赖 |
| `pyproject.toml` | Python 项目配置 | tracked | `daily3albums` 包、依赖、CLI、pytest/ruff 配置 | 是 | 是 | 否 | Python 构建和 CLI 入口依赖 |
| `README.md` | 主说明文档 | tracked | 中文项目说明 | 是 | 是 | 否 | 维护者入口 |
| `README.en.md` | 英文说明文档 | tracked | 英文项目说明 | 是 | 是 | 否 | 文档入口 |
| `REVIEW_REPORT.md` | 历史审计/评审文档 | tracked | 旧 review 报告 | 需人工确认 | 需人工确认 | 不建议自动清理 | 若仍是项目记录则保留；若过期应通过单独变更处理 |
| `run_ambient_debug.txt` | 调试日志 | tracked | API cache/debug 记录，约 79.50 KB | 需人工确认 | 需人工确认 | 不建议自动清理 | 内容形如 Last.fm/MusicBrainz cache hit 日志；更像历史运行产物 |

顶层文件大小与时间摘要：

| 路径 | 大小 | 创建时间 | 修改时间 |
|---|---:|---|---|
| `.env` | 1.58 KB | 2026-02-09 02:51:53 | 2026-02-09 03:32:13 |
| `.env.example` | 509 B | 2026-02-09 02:02:01 | 2026-01-16 20:58:32 |
| `.gitattributes` | 18 B | 2026-02-09 02:02:01 | 2026-01-16 21:32:32 |
| `.gitignore` | 224 B | 2026-02-09 02:02:01 | 2026-01-17 06:15:58 |
| `AGENTS.md` | 10.74 KB | 2026-02-09 02:02:01 | 2026-01-25 01:22:12 |
| `pyproject.toml` | 1.58 KB | 2026-02-09 02:02:01 | 2026-01-19 02:25:14 |
| `README.en.md` | 4.04 KB | 2026-02-09 02:02:01 | 2026-02-09 06:46:39 |
| `README.md` | 4.82 KB | 2026-02-09 02:02:01 | 2026-01-25 07:08:42 |
| `REVIEW_REPORT.md` | 8.06 KB | 2026-02-09 07:59:36 | 2026-02-09 07:59:36 |
| `run_ambient_debug.txt` | 79.50 KB | 2026-02-09 02:02:01 | 2026-01-17 08:10:21 |

## Git 跟踪文件说明

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| 全仓库 | Git index | tracked: 107 files | 当前版本控制基线 | 是 | 已提交/应继续管理 | 否 | `git ls-files` 统计为 107 |
| `.github/` | CI | tracked: 2 | CI 与 Pages workflow | 是 | 是 | 否 | 自动化构建发布依赖 |
| `daily3albums/` | Python 源码 | tracked: 13 | 生成器与 CLI | 是 | 是 | 否 | 项目核心 |
| `docs/` | 文档 | tracked: 6 | runbook、UI notes、revive baseline/audit | 是 | 视策略 | 否 | 已有 revive 文档被跟踪，但本地 exclude 会影响新增文件 |
| `logs/` | 日志 | tracked: 3 | `.gitkeep`、历史构建/adapter 日志 | 需人工确认 | 需人工确认 | 不建议自动清理 | 已跟踪日志不像源码，建议单独决策 |
| `scripts/` | 脚本 | tracked: 5 | 检查与维护脚本 | 是 | 是 | 否 | 维护链路依赖 |
| `tests/` | 测试 | tracked: 15 | pytest fixtures/golden/test cases | 是 | 是 | 否 | 回归验证依赖 |
| `ui/` | 前端 | tracked: 46 | React/Vite 源码、public seed、package lock、测试 | 是 | 是 | 否 | 静态站前端依赖 |
| `web/` | 静态文件 | tracked: 4 | 旧/占位静态资源 | 需人工确认 | 需人工确认 | 不建议自动清理 | 是否仍为有效入口需确认 |

当前已跟踪的 `docs/revive/` 文件：

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `docs/revive/2026-06-code-audit.md` | 审计文档 | tracked | 代码审计基线 | 是 | 是 | 否 | 后续修复依据 |
| `docs/revive/2026-06-local-baseline.txt` | 复健记录 | tracked | 本地基线验证记录 | 是 | 是 | 否 | 运行证据 |

## Git 未跟踪/忽略文件说明

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| 非忽略未跟踪文件 | Git others | none | 无 | 不适用 | 不适用 | 不适用 | `git ls-files --others --exclude-standard --directory` 输出为空 |
| `.codex/` | 本地工具目录 | ignored by `.git/info/exclude:12` | Codex 本地环境记录 | 视本地需要 | 否 | 可 | 不属于项目源文件 |
| `.env` | 本地密钥配置 | ignored by `.gitignore:13` | 本地运行 secret/config | 是，本地保留 | 否 | 谨慎 | 可能含敏感信息 |
| `.pytest_cache/` | pytest 缓存 | ignored by `.git/info/exclude:16` | 测试缓存 | 否 | 否 | 可 | 可重建 |
| `.state/` | SQLite cache | ignored by `.gitignore:7` | API/cache 状态 | 视本地需要 | 否 | 可谨慎清理 | 可重建但会损失缓存命中 |
| `.venv/` | Python venv | ignored by `.gitignore:1` | 本地 Python 依赖 | 视本地需要 | 否 | 可 | 可重建 |
| `_build/` | 静态输出 | ignored by `.gitignore:6` | production build 输出 | 视验证需要 | 否 | 可 | 生成器接管 |
| `daily3albums.egg-info/` | packaging 产物 | ignored by `.gitignore:19` | editable install 元数据 | 否 | 否 | 可 | 可重建 |
| `daily3albums/__pycache__/` | Python bytecode | ignored by `.gitignore:2` | Python 缓存 | 否 | 否 | 可 | 可重建 |
| `scripts/__pycache__/` | Python bytecode | ignored by `.gitignore:2` | Python 缓存 | 否 | 否 | 可 | 可重建 |
| `tests/__pycache__/` | Python bytecode | ignored by `.gitignore:2` | Python 缓存 | 否 | 否 | 可 | 可重建 |
| `ui/dist/` | UI build 输出 | ignored by `ui/.gitignore:2` | Vite build 产物 | 视验证需要 | 否 | 可 | 可由 `npm --prefix ui run build` 重建 |
| `ui/node_modules/` | Node 依赖 | ignored by `ui/.gitignore:1` | npm 安装目录 | 视本地需要 | 否 | 可 | 可由 lockfile 重建 |
| `docs/revive/2026-06-progress-snapshot.md` | 本地进度文档 | ignored by `.git/info/exclude:14` | Codex/修复阶段记录 | 需人工确认 | 视策略 | 可 | 被本地 exclude 隐藏，但可能有记录价值 |
| `docs/revive/2026-06-progress-summary.md` | 本地进度文档 | ignored by `.git/info/exclude:14` | Codex/修复阶段记录 | 需人工确认 | 视策略 | 可 | 被本地 exclude 隐藏，但可能有记录价值 |

## 本地生成物与缓存

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.state/cache.sqlite` | SQLite cache | ignored | API/cache 主库，12.75 MB | 视本地运行需要 | 否 | 可谨慎清理 | 清理会失去缓存，可能增加外部 API 请求 |
| `.state/cache.sqlite.bak` | SQLite backup | ignored | 旧缓存备份，8.71 MB | 需人工确认 | 否 | 可 | 看起来是历史备份，清理前确认无回滚价值 |
| `.pytest_cache/` | 测试缓存 | ignored | pytest 运行记录 | 否 | 否 | 可 | 可重建 |
| `daily3albums/__pycache__/` | Python 缓存 | ignored | Python bytecode | 否 | 否 | 可 | 可重建 |
| `scripts/__pycache__/` | Python 缓存 | ignored | Python bytecode | 否 | 否 | 可 | 可重建 |
| `tests/__pycache__/` | Python 缓存 | ignored | Python bytecode | 否 | 否 | 可 | 可重建 |
| `daily3albums.egg-info/` | packaging 产物 | ignored | editable install 元数据 | 否 | 否 | 可 | 可重建 |

## 构建产物与旧生成产物

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `_build/public/` | production static output | ignored | `daily3albums build --out .\_build\public` 的最终站点 | 视本地验证需要 | 否 | 可 | 应由生成器重建 |
| `ui/dist/` | Vite build output | ignored | 前端 build 产物，约 369.61 KB | 视本地验证需要 | 否 | 可 | 可由 npm build 重建 |
| `ui/public/data/` | 前端 public 示例/静态数据 | tracked | 本地开发 seed 或 public 数据输入 | 是 | 是，若项目仍需要 dev seed | 否 | 当前在 Git 中，不能当作临时产物清理 |
| `web/` | 旧静态资源候选 | tracked | 静态 HTML/placeholder/favicon | 需人工确认 | 需人工确认 | 不建议自动清理 | 可能被旧流程引用；需确认与 `ui/`、`_build/public` 的关系 |
| `run_ambient_debug.txt` | 调试日志 | tracked | ambient tag API/cache 调试输出 | 需人工确认 | 需人工确认 | 不建议自动清理 | 若只是旧生成日志，应通过单独变更移出 Git |
| `logs/adapters.log` | 运行日志 | tracked | adapter/API 构建日志，约 2.93 MB | 需人工确认 | 需人工确认 | 不建议自动清理 | 已跟踪且体积较大，可能污染仓库历史 |
| `logs/build.log` | 运行日志 | tracked | build 日志，约 55.22 KB | 需人工确认 | 需人工确认 | 不建议自动清理 | 已跟踪，需确认是否作为证据保留 |

## 依赖目录与虚拟环境

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.venv/` | Python 虚拟环境 | ignored | 固定本地 Python/CLI 环境 | 视本地需要 | 否 | 可 | 可按 `pyproject.toml` 重建；不要提交 |
| `ui/node_modules/` | Node 依赖 | ignored | 前端 npm 依赖，约 111.68 MB | 视本地需要 | 否 | 可 | 可按 `ui/package-lock.json` 重建 |
| `ui/package-lock.json` | lockfile | tracked | npm 依赖锁定 | 是 | 是 | 否 | 可复现安装依赖 |
| `pyproject.toml` | Python 项目配置 | tracked | Python 依赖与工具配置 | 是 | 是 | 否 | 可复现安装 Python 包 |
| `daily3albums.egg-info/` | packaging 产物 | ignored | 本地 editable install 元数据 | 否 | 否 | 可 | 安装过程生成 |

## Codex 本地目录

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.codex/` | Codex 本地目录 | ignored by `.git/info/exclude:12` | Codex 环境/会话本地文件，约 1.59 KB | 视本地需要 | 否 | 可 | 本地工具目录，不属于项目 |
| `.codex/environments` | Codex 子目录 | ignored | 环境记录 | 视本地需要 | 否 | 可 | 本地生成 |

## 可清理候选清单

下面只是候选，不代表本次应删除；本次审计未做任何清理。

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.pytest_cache/` | 缓存 | ignored | pytest cache | 否 | 否 | 可 | 可重建 |
| `daily3albums/__pycache__/` | 缓存 | ignored | Python bytecode | 否 | 否 | 可 | 可重建 |
| `scripts/__pycache__/` | 缓存 | ignored | Python bytecode | 否 | 否 | 可 | 可重建 |
| `tests/__pycache__/` | 缓存 | ignored | Python bytecode | 否 | 否 | 可 | 可重建 |
| `daily3albums.egg-info/` | packaging 产物 | ignored | install metadata | 否 | 否 | 可 | 可重建 |
| `_build/` | 构建产物 | ignored | production output | 视本地验证需要 | 否 | 可 | 可重建 |
| `ui/dist/` | 构建产物 | ignored | frontend output | 视本地验证需要 | 否 | 可 | 可重建 |
| `ui/node_modules/` | 依赖目录 | ignored | npm deps | 视本地需要 | 否 | 可 | 可重建但重装耗时 |
| `.venv/` | 依赖目录 | ignored | Python deps | 视本地需要 | 否 | 可 | 可重建但重装耗时 |
| `.state/cache.sqlite.bak` | 缓存备份 | ignored | 旧 SQLite 备份 | 需人工确认 | 否 | 可 | 历史备份，确认无回滚价值后可删 |
| `.codex/` | 本地工具目录 | ignored | Codex 本地状态 | 视本地需要 | 否 | 可 | 不影响仓库源码 |
| `docs/revive/2026-06-progress-snapshot.md` | 本地过程文档 | ignored | 阶段记录 | 需人工确认 | 视策略 | 可 | 如果不需要保留过程记录，可清理；否则应调整文档策略 |
| `docs/revive/2026-06-progress-summary.md` | 本地过程文档 | ignored | 阶段记录 | 需人工确认 | 视策略 | 可 | 同上 |

## 不建议删除的文件

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `.env` | 本地密钥配置 | ignored | 外部 API 和本地配置 | 是，本地保留 | 否 | 不建议直接删 | 删除会影响本地运行；如需轮换密钥应手动处理 |
| `.env.example` | 示例配置 | tracked | 环境变量模板 | 是 | 是 | 否 | onboarding 需要 |
| `.github/workflows/*.yml` | CI workflow | tracked | CI/Pages 自动化 | 是 | 是 | 否 | 长期无人值守运行依赖 |
| `config/*.yaml` | 业务配置 | tracked | 标签、端点策略等 | 是 | 是 | 否 | 构建链路依赖 |
| `daily3albums/` | 源码 | tracked | 核心生成器 | 是 | 是 | 否 | 核心功能 |
| `scripts/self_check.py` | 检查脚本 | tracked | 产物自检 | 是 | 是 | 否 | 构建验证依赖 |
| `tests/` | 测试 | tracked | 回归测试 | 是 | 是 | 否 | 修改后验证依赖 |
| `ui/src/`, `ui/package.json`, `ui/package-lock.json` | 前端源码/依赖声明 | tracked | React/Vite 前端 | 是 | 是 | 否 | UI 构建依赖 |
| `docs/runbook.md`, `docs/revive/2026-06-code-audit.md`, `docs/revive/2026-06-local-baseline.txt` | 文档 | tracked | 运维和复健证据 | 是 | 是 | 否 | 后续维护上下文 |
| `AGENTS.md` | 项目规则 | tracked | doctor 计划与协作约束 | 是 | 是 | 否 | 当前项目约束来源 |

## 建议后续更新 `.gitignore` 或 `.git/info/exclude` 的项目

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `run_ambient_debug.txt` | 调试日志 | tracked, not ignored | API/cache debug 记录 | 需人工确认 | 需人工确认 | 不建议自动清理 | `.gitignore` 中疑似存在无效 NUL 编码规则；若决定不再跟踪，应修正规则并单独移出 Git |
| `logs/*.log` | 运行日志 | tracked, not ignored | 运行/构建日志 | 需人工确认 | 需人工确认 | 不建议自动清理 | 当前 `.git/info/exclude` 只忽略 `logs/adapter_requests.log`；建议决定是否改为忽略运行日志，仅保留 `logs/.gitkeep` |
| `docs/revive/` | 文档目录 | mixed, local ignored | 复健/审计文档 | 是 | 视策略 | 否 | 本机 `.git/info/exclude` 忽略整个目录，但已有 revive 文档被跟踪；若审计文档要提交，应移除或收窄本地 exclude |
| `doctor/runs/` | 未来 doctor 产物 | currently not present | doctor run artifacts | 否 | 否 | 可 | 若启用新版 doctor，会产生报告/截图/日志；建议未来明确忽略产物目录 |
| `ui/artifacts/screenshots/` | UI 截图产物目录 | partially tracked README | screenshot evidence | 视策略 | 只提交说明或基线 | 可 | 若未来产生大量截图，应明确忽略生成截图、保留 README 或基线 |

## 需要人工确认的未知文件

| 路径 | 类型 | 当前状态(tracked/untracked/ignored) | 用途 | 是否应保留 | 是否应提交 | 是否可清理 | 理由 |
|---|---|---|---|---|---|---|---|
| `logs/adapters.log` | 运行日志 | tracked | adapter/API 日志，约 2.93 MB | 需确认 | 需确认 | 不自动清理 | 体积较大且内容可能包含外部请求上下文；需判断是否作为证据保留 |
| `logs/build.log` | 运行日志 | tracked | build 日志，约 55.22 KB | 需确认 | 需确认 | 不自动清理 | 运行产物性质明显，但已跟踪 |
| `run_ambient_debug.txt` | 调试日志 | tracked | ambient tag cache debug 输出，约 79.50 KB | 需确认 | 需确认 | 不自动清理 | 开头为 Last.fm/MusicBrainz cache hit 记录，像历史 debug 文件 |
| `web/` | 旧静态资源 | tracked | 简单 HTML、placeholder、空 favicon | 需确认 | 需确认 | 不自动清理 | 可能已被 `ui/` 与 `_build/public` 替代，也可能仍是 fallback |
| `REVIEW_REPORT.md` | 历史 review 文档 | tracked | 旧评审报告 | 需确认 | 需确认 | 不自动清理 | 若过期可迁移/归档，但不应在本轮盘点中处理 |
| `.state/cache.sqlite.bak` | cache 备份 | ignored | SQLite 旧备份，约 8.71 MB | 需确认 | 否 | 可 | 忽略的本地备份；确认不需要回滚后可清理 |
| `docs/revive/2026-06-progress-snapshot.md` | 本地过程文档 | ignored | 阶段快照 | 需确认 | 视策略 | 可 | 被本地 exclude 隐藏，可能有上下文价值 |
| `docs/revive/2026-06-progress-summary.md` | 本地过程文档 | ignored | 阶段摘要 | 需确认 | 视策略 | 可 | 同上 |

## 审计命令记录

```powershell
git status -sb --ignored
git ls-files
git check-ignore -v .venv ui/node_modules node_modules .pytest_cache .codex _build ui/dist .state logs doctor/runs docs/revive/2026-06-progress-snapshot.md 2>$null
Get-ChildItem -Force | Sort-Object PSIsContainer,Name | Select-Object Mode,Length,CreationTime,LastWriteTime,Name
Get-Content -LiteralPath .gitignore
Get-Content -LiteralPath ui\.gitignore
Get-Content -LiteralPath .git\info\exclude
Get-ChildItem -LiteralPath docs\revive -Force | Sort-Object Name | Select-Object Mode,Length,CreationTime,LastWriteTime,Name
PowerShell aggregate stats for top-level and second-level entries using Get-ChildItem -Recurse with aggregate counts only
git check-ignore -v --no-index .env .state/cache.sqlite .state/cache.sqlite.bak daily3albums.egg-info daily3albums/__pycache__ scripts/__pycache__ tests/__pycache__ ui/node_modules ui/dist _build .codex .pytest_cache logs/adapters.log logs/build.log run_ambient_debug.txt docs/revive/2026-06-progress-snapshot.md docs/revive/2026-06-progress-summary.md 2>$null
Get-Content -LiteralPath pyproject.toml
Get-Content -LiteralPath ui\package.json
Get-ChildItem -LiteralPath logs -Force | Sort-Object Name | Select-Object Mode,Length,CreationTime,LastWriteTime,Name
Get-ChildItem -LiteralPath .state -Force | Sort-Object Name | Select-Object Mode,Length,CreationTime,LastWriteTime,Name
git ls-files --others --exclude-standard --directory
git ls-files --others --ignored --exclude-standard --directory
Get-Content -LiteralPath run_ambient_debug.txt -TotalCount 12
Get-ChildItem -LiteralPath web -Force -Recurse | Sort-Object FullName | Select-Object Mode,Length,CreationTime,LastWriteTime,FullName
git ls-files | Measure-Object
git ls-files | ForEach-Object { ($_ -split '[\\/]', 2)[0] } | Group-Object | Sort-Object Name | Select-Object Name,Count
git ls-files logs run_ambient_debug.txt web docs/revive
```
