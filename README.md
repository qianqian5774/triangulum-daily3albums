# Triangulum Daily 3 Albums

[English](README.en.md) | 中文

Triangulum Daily 3 Albums 是一个每天推荐三张专辑的静态站点和生成系统。

我最开始做它，是想给自己一个每天听专辑的入口：不要总被流媒体平台和社交媒体的推荐逻辑推着走，而是每天看到几张不那么热门、但可能有意思的专辑。后来我发现，如果这个东西能稳定放到网上，让更多人每天打开看一眼，也是一件很好的事。所以这个仓库记录的是 Daily 3 Albums 项目的生成、发布和维护实现。

## 它做什么

系统每天生成 3 张专辑推荐，并发布成一个可以直接访问的静态网站。访问者看到的是当天内容、按北京时间解锁的三个时段，以及过去推荐的归档。

核心目标很简单：

- 每天给出 3 张值得听的专辑。
- 尽量避开过于主流、过于熟悉的推荐结果。
- 让推荐内容可以长期稳定地自动生成和发布。
- 保留归档，方便回看过去每天出现过的专辑。

## 它怎么运转

Daily 3 Albums 由两个部分组成：

- Python 生成器：读取配置、调用外部音乐数据源、筛选候选专辑、生成站点需要的 JSON 数据。
- 前端静态站点：读取生成好的数据，在浏览器里展示当天推荐、归档和详情页。

每天的自动流程大致是：

1. GitHub Actions 在北京时间清晨运行一次构建。
2. 生成器根据配置和缓存获取候选专辑。
3. 系统筛选出当天 3 张专辑，写入 `today.json` 和 archive 数据。
4. 前端构建为静态文件。
5. GitHub Pages 发布 `_build/public` 中的站点文件。

站点不依赖运行中的后端服务。发布完成后，访问者看到的页面都是静态资源。

## 每日时段

站点按北京时间 Asia/Shanghai 展示不同状态：

- 00:00-05:59：当天内容尚未开放。
- 06:00-11:59：开放第 1 张专辑。
- 12:00-17:59：开放第 2 张专辑。
- 18:00-23:59：开放第 3 张专辑。

06:00 / 12:00 / 18:00 的切换由浏览器运行时判断，不需要在每个时段重新部署。

## 主要功能

- 每日 3 张专辑推荐。
- 按北京时间分时段解锁。
- 今日页面、归档页面和专辑详情页面。
- 基于 Last.fm、MusicBrainz 等外部数据源补充音乐信息。
- 本地 SQLite cache，减少重复请求和外部 API 压力。
- 生成后的 `self_check`，用于检查当天数据、归档和关键输出是否一致。
- `doctor` 命令，用于检查配置、环境、时区和外部服务基础可用性。
- `debug_time` 参数，用于本地验证不同时段的页面状态。

## 项目结构

```text
daily3albums/      Python 生成器和 CLI
config/            标签、数据源和端点策略配置
scripts/           维护和自检脚本
ui/                前端静态站点
docs/              运维记录、复健记录和审计文档
_build/public/     本地生成的最终静态站点输出
```

`_build/public` 是最终发布目录。前端开发示例数据和生产生成数据需要区分，不要直接把 `ui/public/data` 当成生产输出。

## 维护者本地命令

这些命令用于维护者本地验证当前项目状态。更完整的运行记录见 `docs/runbook.md` 和 `docs/revive/`。

```bash
npm --prefix ui ci
npm --prefix ui test
npm --prefix ui run build
daily3albums doctor
daily3albums build --verbose --out ./_build/public
python scripts/self_check.py --path ./_build/public
```

本地预览：

```bash
python -m http.server --directory _build/public 8000
```

## debug_time

本地调试时可以用 `debug_time` 模拟北京时间：

```text
?debug_time=YYYY-MM-DDTHH:MM:SS
```

HashRouter 场景也支持：

```text
/#/?debug_time=YYYY-MM-DDTHH:MM:SS
```

常用来检查 05:59 / 06:00 / 12:00 / 18:00 / 跨日等状态。

## 运行边界

- 生产 CI 使用 Python 3.11。本地较新的 Python，例如 3.14，可以作为开发环境，但不能替代 CI 3.11 验证。
- 产品时间固定为北京时间 Asia/Shanghai。`config.timezone` 和环境变量用于让本地、CI 和生成器对齐，不表示站点支持多时区产品模式。
- `daily3albums build` 默认会构建 UI 并写入 `_build/public/data`。如果已经单独构建过 UI，可以使用 `--skip-ui-build` 复用已有 `ui/dist`，但不要在缺少 `ui/dist` 的环境使用。
- 浏览器或 CDN 可能缓存 `today.json`。关键边界会使用 cache-busting 请求；如果取回的数据不是北京时间当天，UI 应进入安全降级态并重试。
- `require_cover: true` 当前表示优先选择有封面的候选，不是封面缺失就让构建失败。Cover Art Archive 无封面时可退回 Last.fm 图片；仍无图片时使用 `assets/placeholder.svg`。

## 当前状态

项目正在围绕稳定发布和长期无人值守运行继续维护。近期工作重点包括构建链路一致性、缓存和 API 失败可解释性、静态输出自检，以及最终发布到正式域名。
