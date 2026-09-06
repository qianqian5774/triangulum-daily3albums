# Triangulum Daily

[English](./README.md)

每天九张专辑，分三个时段、每次三张。Triangulum Daily 是一个按每日节奏运行的有限音乐发现产品，不是无限信息流。

**在线站点：** [triangulumdaily.space](https://triangulumdaily.space/)

## 每日节奏

所有产品时间均使用 Asia/Shanghai（BJT）。

| BJT 时段 | 可用内容 |
| --- | ---: |
| 00:00–07:59 | Offline State |
| 08:00–12:29 | 3 张专辑 |
| 12:30–15:59 | 6 张专辑 |
| 16:00–23:59 | 9 张专辑 |

每个已发布 issue 都包含三个 slot、每个 slot 三张 pick。浏览器只决定显示 0 / 3 / 6 / 9 张库存；它不会生成推荐，也不会向 provider 请求新的 issue。

## Record Shop

正式产品入口是 `#/` 的 **Record Shop**。

- **Entry Diorama** 是可交互的 Three.js 店外微缩场景，提供六个具名 preset view、受限自由观察/缩放和实体大门。
- 实体门通向正式的 **Record Shop interior**；中央 Daily Device 打开当天库存，店内 HUD 提供最近日期。
- **Today** 使用当前已发布 issue；**History** 在同一店内通过已发布 archive index 与 archive JSON 展示历史 issue。
- **Treatment Viewer** 以覆盖层打开被选择唱片的阅读内容，不创建独立详情路由。
- `#/today` 与 `#/archive` 仍是辅助的静态数据页面；Record Shop 是正式首页体验。

生产环境没有 preview catalog，也没有独立 mock Record Shop catalog。场景只把现有 public issue contract 转换成唱片展示，BJT product clock 决定可见库存。

## 静态数据与封面

Triangulum Daily 是 build-time generated 的 GitHub Pages 静态站。

```text
构建期音乐 provider
        ↓
Python 收集、归一化、选择与补充 metadata
        ↓
经过验证的 today.json + archive JSON + index.json
        ↓
同源封面资源与 manifest
        ↓
React/Vite bundle
        ↓
GitHub Pages
```

浏览器只读取静态 JSON 与资源。站点没有应用后端、数据库、账号、评论、播放器、交易市场或访客写入。Last.fm、MusicBrainz、Discogs、ListenBrainz、Wikipedia、Wikimedia 和 Cover Art Archive 都是构建期输入，不是浏览器端应用 API。

生产构建会把可用封面复制到 `assets/covers/`，并写入 `assets/cover-manifest.js`。UI 优先解析同源映射，图片不可用时使用本地回退。直接加载第三方封面只属于降级资源情况，不是正常生产路径。

当前 issue 从 `data/today.json` 读取。Archive 浏览先读取 `data/index.json`，再读取 run-specific archive JSON 与经过检查的 date alias fallback。当前 issue 恢复沿用应用中的 current → last-good → archive 路径。

## 仓库 contract

- [`tests/fixtures/product_schedule.json`](./tests/fixtures/product_schedule.json) 是 BJT 时段与 3×3 issue 结构的跨运行时日程证据。
- [`tests/fixtures/public_contract/manifest.json`](./tests/fixtures/public_contract/manifest.json) 是 Python / TypeScript 共用 public JSON fixture manifest。
- 已发布 issue 使用现有 schema、稳定 role、release-group identity 与经过检查的 archive identity。
- [`AGENTS.md`](./AGENTS.md) 记录静态架构边界、验证模型、生成物规则与 Git hygiene。
- [`docs/foundation/`](./docs/foundation/) 保存当前长期事实，[`docs/design/`](./docs/design/) 是当前视觉/设计 authority。[`docs/archive/`](./docs/archive/)、[`docs/revive/`](./docs/revive/) 和 [`docs/legacy/`](./docs/legacy/) 只保存历史背景。

## 本地开发与验证

环境要求：

- Python 3.11+
- Node.js `>=22 <25`
- npm
- 真实数据构建需要构建期 provider credentials

```bash
python -m venv .venv
python -m pip install -e ".[test]"
npm --prefix ui ci
```

真实数据构建时将 [`.env.example`](./.env.example) 复制为 `.env`。不要提交 `.env`、`_build/`、`ui/dist/`、cache、日志或本地证据。

按改动范围选择最小验证层：

```text
python -m pytest
npm --prefix ui test
npm --prefix ui run build
daily3albums build --verbose --out _build/public
python scripts/self_check.py --path _build/public
npm --prefix ui run browser:smoke
npm --prefix ui run browser:record-shop
npm --prefix ui run performance:audit
```

每日生产 workflow 名为 **Build and Deploy Pages (Daily)**。它恢复并验证已发布 archive history，执行正常 tests/build/self-check，materialize 封面资源，上传 Pages artifact 并部署。Doctor 已退役，不再作为健康或发布命令。

## 仓库结构

```text
daily3albums/       构建期 generator、provider、contract 与 writer
ui/                 React/Vite UI、Record Shop、tests 与 browser checks
config/             recommendation 与 endpoint policies
tests/              Python tests 与跨运行时 fixtures
scripts/            self-check、archive recovery、metrics 与 observability
.github/workflows/  CI 与每日 Pages production workflow
docs/               当前 foundation/design 文档与历史证据
```

为更慢的聆听而做：一天九张专辑，每次三张。
