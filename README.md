# Triangulum Daily

English (default) | [中文](#中文)

Nine albums a day. Three release windows, three albums at a time. No endless feed or chart-chasing—just a few daily openings into somewhere less familiar.

**Live site:** [triangulumdaily.space](https://triangulumdaily.space/)

Triangulum Daily is a continuously maintained, build-time generated music-discovery product. A Python pipeline selects and validates nine albums each Beijing-time day; a React/Vite interface reveals them across the 08:00, 12:30, and 16:00 windows; GitHub Actions publishes the resulting static JSON, archive, and assets to GitHub Pages.

The production site has no application backend and visitor browsers do not call external music-data APIs. Recommendation cooldowns and bounded fallbacks, public JSON contracts, archive recovery, regression tests, release observability, performance baselines, and the agent operating constraints in [`AGENTS.md`](./AGENTS.md) are maintained as repository-level engineering practices.

The complete English product and engineering README is available in [`README.en.md`](./README.en.md). The Chinese README follows below.

---

## 中文

每天九张专辑。三个时段，每次三张。不追热点，不刷榜单，也不制造无限信息流——只给一天留几个听见别处的入口。

**在线站点：** [triangulumdaily.space](https://triangulumdaily.space/)

## 这是什么

Triangulum Daily 是一个按照有限日常节奏运行的音乐发现产品。它以北京时间为准，每天发布九张专辑，分三个时段逐步出现：

| 北京时间 | 内容 |
| --- | --- |
| 00:00–07:59 | Offline State |
| 08:00 | 第一时段，三张专辑 |
| 12:30 | 第二时段，三张专辑 |
| 16:00 | 第三时段，三张专辑 |

限制本身就是产品的一部分。Triangulum Daily 不想成为另一个无限目录，也不会不断猜测下一次点击。它每天只留下一小组唱片，让人有时间去听，并把近期的每日 issue 保存在静态归档中。

公开产品目前包括：

- **Today Page**：当天 issue，按三个时段逐步揭示。
- **Treatment Viewer**：从 Album Card 打开的专辑覆盖层，不是独立详情路由。
- **Archive Page**：从静态 archive 文件读取的近期每日推荐。
- **Share Card**：只根据当前已经解锁的时段生成分享图。
- **Ambient Overlay**：用于沉浸或待机浏览的覆盖层。

## 一个持续运行的静态产品

这个仓库是正式站点的源码，不是一次性数据导出。GitHub Actions 每天定时重新生成并发布；在生成之前，workflow 会先恢复上一次已经发布的 archive，使推荐历史可以跨越无状态 runner 延续。

```text
构建期音乐数据源
        ↓
Python 候选收集、归一化、选择与补充 metadata
        ↓
经过验证的 today.json、七日静态 archive 与构建证据
        ↓
React/Vite production bundle
        ↓
GitHub Pages
```

部署后的站点没有应用后端、数据库、账号系统或访客写入路径。浏览器只读取版本化静态 JSON 与资源；外部音乐服务只由构建期 generator 使用，不是访客端运行时 API。

### 每日生成与推荐保护

Generator 从配置好的 Last.fm、Discogs 与 ListenBrainz adapter 取得候选，以 MusicBrainz release group 归一化专辑身份，补充可获得的 metadata 与封面链接，再为每个时段选出 `Headliner`、`Lineage` 和 `DeepCut` 三个角色。

推荐逻辑有明确边界，也留下可检查的证据：

- 版本化 normalization policy 把严格匹配、有限的 borderline 情况与 hard reject 分开处理。
- 正常策略禁止同日重复艺人，并执行专辑与艺人七日 cooldown、主题三日 cooldown。
- 候选不足时才进入分阶段 fallback：多取一页候选、按文档缩短 artist cooldown，最后每天至多允许一张来自四至七日专辑窗口的结果。专辑与艺人的三日底线仍然保留，hard reject 不会被 fallback 放入结果。
- Provider 请求统一经过 request broker，执行各服务的 rate limit、有限重试、backoff、缓存、稳定错误分类和诊断 URL 脱敏。
- Build Metrics 与 Recommendation Observability 记录候选漏斗、拒绝原因、provider 结果、fallback、metadata 覆盖与发布时间，但不把浏览器变成 telemetry 客户端。

活动策略位于 [`config/config.yaml`](./config/config.yaml)，provider 行为位于 [`config/endpoint_policies.yaml`](./config/endpoint_policies.yaml)。最终事实仍以实现和测试为准。

### 静态 archive 与恢复

当前 retention contract 是七个不重复日期。Generator 会原子写入 run-specific archive 与字节完全一致的日期 alias，验证完整 issue，再更新 archive index。某一天已经成功发布的 issue 默认保持不可变，除非一次明确的恢复操作允许重写。

每日 workflow 在选择推荐前从已发布站点恢复 archive history。恢复工具会检查 index、issue identity、schema 与 alias bytes；刷新数据无效时保留 last-good seed。这份历史既供 Archive Page 展示，也参与推荐 cooldown。

## Repository contracts

仓库里有几组小而明确的 contract，用来防止 generator、静态产物、浏览器与维护流程彼此漂移：

- [`tests/fixtures/product_schedule.json`](./tests/fixtures/product_schedule.json) 是 Python 与 TypeScript 共用的日程证据，固定 BJT Offline 时段、三个解锁时间、三个 slots、每 slot 三张专辑与 Share Card 揭示状态。
- [`tests/fixtures/public_contract/manifest.json`](./tests/fixtures/public_contract/manifest.json) 保存 Python 与 TypeScript 共用的 current / legacy JSON cases。
- 当前 Today 与 archive 文档使用 schema `1.0`，必须是完整 3×3、稳定 role 值、release-group MBID 与经过检查的 archive identity。
- [`AGENTS.md`](./AGENTS.md) 记录 agent-assisted work 必须遵守的静态架构边界、产品术语、验证层、生成物边界与 Git hygiene。
- [`docs/foundation/`](./docs/foundation/) 解释长期有效的架构和运行决定；[`docs/revive/`](./docs/revive/) 与 [`docs/legacy/`](./docs/legacy/) 保存历史背景，但不能替代当前源码与测试。

这些不是愿望清单。跨越 contract 的改动，应当同时处理实现、fixture、测试与长期文档。

## 测试、发布检查与可观测性

当前维护把不同产品面拆成独立验证层：

| 验证层 | 覆盖内容 |
| --- | --- |
| Python `pytest` | 配置、provider、normalization、cooldown/fallback、archive 写入与恢复、public contract、observability、release SLA |
| Vitest UI tests | 日程计算、严格静态数据解析、Today 恢复状态、viewer/share 行为、路径与组件策略 |
| Production UI build | TypeScript 与 Vite production output |
| Static build + `self_check.py` | 最终站点结构、public JSON、archive identity 与必要资源 |
| Playwright | 真实浏览器中的 mobile、Today state、viewer cover、product clock、record-shop、visual 与 smoke 场景 |
| Performance audit | Today、Archive、Treatment Viewer、Ambient 与 Share 的生产基线和 regression budgets |

CI 在 push 与 pull request 上运行 Python 和 UI tests。每日 Pages workflow 会再次执行这些 gate，恢复 archive history，生成生产站点，运行 static self-check，发布经过脱敏的 normalization evidence，总结 build/recommendation metrics，部署 Pages，并报告是否满足 08:00 BJT release target。定时构建失败时，workflow 可以创建带 run link 的 repository issue。

性能 harness 与测量限制见 [`PERFORMANCE.md`](./PERFORMANCE.md)，日常恢复命令见 [`docs/runbook.md`](./docs/runbook.md)。

## 本地开发

环境要求：

- Python 3.11 或更高版本
- Node.js `>=22 <25`
- npm
- 真实数据构建需要 Last.fm API key 与 MusicBrainz user agent；Discogs token 可选

安装项目与 UI 依赖：

```bash
python -m venv .venv
python -m pip install -e ".[test]"
npm --prefix ui ci
```

把 [`.env.example`](./.env.example) 复制为 `.env`，填写构建期 provider credentials。不要提交 `.env` 或生成物。

常用验证命令：

```bash
python -m pytest
npm --prefix ui test
npm --prefix ui run build
daily3albums build --verbose --out _build/public
python scripts/self_check.py --path _build/public
npm --prefix ui run browser:smoke
npm --prefix ui run performance:audit
```

应按照改动选择最小但完整的验证层。Browser smoke 要求已有 `_build/public`；performance audit 会探测配置的生产站点，并把本地证据写入被忽略的目录。`_build/`、`ui/dist/`、缓存、日志和本地 evidence 都是生成物，不提交。

### 仓库结构

```text
daily3albums/       Python generator、adapters、contracts 与 artifact writer
ui/                 React/Vite UI、unit tests 与 browser checks
config/             recommendation 与 endpoint policies
tests/              Python tests 与跨运行时 fixtures
scripts/            self-check、恢复、metrics、observability 与 audit 工具
.github/workflows/  CI 与每日 Pages production workflow
docs/               runbooks、foundation docs 与历史证据
```

产品已经更名为 Triangulum Daily，但技术 package 与 repository 暂时保留历史名称 `daily3albums` / `triangulum-daily3albums`。

## Agent-assisted maintenance

Codex 是维护流程的一部分，但仓库证据仍然是 authority。我会用它检查不熟悉的代码路径、追踪 production failure、审查 diff、补充测试、核对实现与 contract，并整理运行文档。[`AGENTS.md`](./AGENTS.md) 对这类工作给出明确约束：除非经过讨论，不跨越静态架构边界；保留工作区中的无关改动；不提交生成物；按风险选择验证范围。

产品与编辑判断不会交给 agent。推荐规则、三个发布时段、恢复行为、数据边界和交互方向都需要由 maintainer 决定；agent 产生的改动也需要阅读、测试、修改，再通过同一个仓库流程提交。

## 为什么我还在继续做它

Triangulum Daily 最开始完全源于好奇：如果每天只给人几张唱片，会不会比无限推荐更有意思？我的工作和长期经验在内容、音乐、研究、采访与编辑，并不来自传统 software-engineering 路径。过去我不会觉得，独立维护一个软件产品是自己很有机会做到的事。

真正把它做出来，需要我不断决定产品究竟是什么：为什么一天是三个时间窗口，推荐与 fallback 应该怎样工作，数据和 archive 如何组织，构建失败以后怎样恢复，以及页面应该要求听者投入怎样的注意力。我最近也在重新设计 UI 与 interaction system，自己找参考、画 interaction sketches，并反复研究实体唱片式浏览、翻转、揭示、空间和动画之间的关系。

Codex 对这个项目重要，是因为它让我在真实维护循环里学习：读代码、理解故障、修改设计、检查结果、发现错误，再继续推进。很多事情仍然需要我一点点逼自己理解并作出决定；但以前属于“我大概做不了”的事情，现在已经成为实际运行、也能够继续维护的软件。

这个项目不是从 fork、tutorial project 或 UI clone 开始的。它的产品概念、推荐方式与交互方向，都是从 Triangulum Daily 自身的问题里逐步发展出来的。

---

Made for slower listening.

One day, nine albums. Three at a time.
