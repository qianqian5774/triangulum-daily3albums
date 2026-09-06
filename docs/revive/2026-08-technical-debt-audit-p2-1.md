> **Historical / superseded:** this dated P2.1 audit records a previous code state and proposed follow-up work. It is not the current debt register; verify present source before using any finding.

# Triangulum Daily P2.1 Technical Debt Audit

## 1. Executive conclusion

本次审计未发现 P0。发现 3 项 P1，均位于 recommendation runtime 的“声明行为与生产调用顺序”之间：

1. Pages workflow 虽在 build 前恢复 archive seed，但 `cmd_build()` 在把 seed 复制到输出目录之前就读取 history，因此干净 runner 上的跨日 artist/theme cooldown context 为空。
2. `min_confidence` 与 `ambiguity_gap` 虽通过 CLI 传递并写入 public JSON，`run_dry_run()` 却显式丢弃两者；文本匹配结果没有按这两个阈值过滤。
3. `history.dedupe_same_rg_days` 没有进入 production hard filter；历史 album keys 被收集但没有参与候选筛选，recent release-group IDs 也因 `cooling_penalty=None` 不影响抽样。

当前最重要的 source-of-truth 漂移是 recommendation runtime config：同一行为同时由 `config/config.yaml`、`AppConfig`、`cfg.raw`、CLI defaults 和硬编码常量描述，其中若干值碰巧相同但配置并不生效。P2.2 应先恢复“历史上下文进入选择流程”和“配置状态可判定”，再统一 schedule/schema 等跨层事实源。P2.3 才处理组件拆分、错误类型、dead code 与 CSS 组织。

本轮是只读审计。除本文外未修改 Python、TypeScript、CSS、config、workflow、tests、fixtures、README 或 foundation。现有五份本地 foundation 修改未被 stash、恢复、暂存或提交。

## 2. Audit scope and evidence basis

审计覆盖：

- `config/config.yaml`、`config/endpoint_policies.yaml`、`.env.example`；
- `daily3albums/` 的 CLI、candidate pipeline、normalization、constraints、artifact writer、adapters 和 request broker；
- `today.json`、archive JSON、`index.json`、`meta.json`、`recommendation-observability.json` 的写出、解析和验证；
- `ui/src/` 的路由、状态、组件、数据解析、BJT、Share Card 和 CSS；
- `.github/workflows/ci.yml`、`.github/workflows/pages_daily.yml`、package scripts 与 `scripts/`；
- Python/UI tests、fixtures、active README、项目文档和 foundation 背景。

重要结论均以当前源码、配置、测试和 workflow 为准。`docs/revive/`、`docs/legacy/`、`docs/foundation/_snapshots/` 和 `docs/archive/` 只作为历史区域，不用于单独证明当前行为。

执行的验证：

- `\.venv\Scripts\python.exe -m pytest -p no:cacheprovider`：61 passed；
- `C:\Users\11836\AppData\Local\nvm\v22.13.0\npm.cmd --prefix ui test`：11 files、40 tests passed；
- 静态追踪 config keys、imports、CLI entrypoints、workflow steps、package scripts、public schema 和 UI component references。

未运行 production build、Pages deployment、Playwright、performance audit 或外部网络探测；这些检查不属于本次 Markdown-only 审计的必要证据。

## 3. System map

```text
config + environment
        |
        v
daily3albums.cli:cmd_build()
        |
        +--> RequestBroker --> Last.fm / MusicBrainz / Discogs / ListenBrainz
        |
        +--> dry_run.run_dry_run() --> merge --> normalize --> score
        |
        +--> hard filters --> weighted sampling --> enrichment
        |
        +--> artifact_writer.write_daily_artifacts()
                  |
                  +--> data/today.json
                  +--> data/archive/<date>/<run_id>.json + legacy date alias
                  +--> data/index.json
        |
        +--> data/recommendation-observability.json

Vite build --> ui/dist ------------------------------+
web static files ------------------------------------+--> _build/public
Pages workflow --> data/meta.json -------------------+

browser --> HashRouter --> Today Page / Archive Page
        --> fetch static JSON only
        --> Treatment Viewer / Share Card / Ambient Overlay
```

职责边界总体清楚：外部音乐 API 只在 build-time；浏览器只读取静态 JSON 和资源；GitHub Actions 负责编排、验证和发布。主要边界问题不是架构越界，而是 generator 内部的 config/selection/history 顺序，以及 schema validation 分散。

## 4. Product constants and sources of truth

### Source-of-truth matrix

| Concern | Current sources | Actual authority | Drift risk | P2.2 recommendation |
| ------- | --------------- | ---------------- | ---------- | ------------------- |
| BJT unlock schedule | `cli.py:_beijing_slot/_slot_label/_slot_window_start`；`ui/src/lib/bjt.ts:SLOT_SCHEDULE`；Share Card versions；copy/tests/README | Python 和 TypeScript 各自执行，tests 只验证当前相等 | Medium；跨语言必要重复，但没有共享契约证据 | 保留两端实现，增加一份小型 canonical schedule fixture/contract test；不要引入代码生成框架 |
| Slots/day and picks/slot | Python loops/validators；UI parser；self-check；tests | `cmd_build()` + `validate_today()` + `self_check` | Low-Medium；目前一致为 3×3 | 用 public contract tests 对齐，不必抽象成通用配置系统 |
| Share Card versions | `ui/src/lib/share-card.ts`、SVG template、tests | `SHARE_CARD_VERSIONS` | Low；UI 内部集中，SVG 是必要静态重复 | 保持 UI 常量；用现有 template test 继续验证时间文案 |
| Archive retention | `config.yaml:history.archive_retention_days`、`AppConfig`、artifact writer default、restore workflow `--max-days 7`、UI default 7 | 生产写出由 config 控制；restore 仍硬编码 7 | Medium | 让 workflow restore 从同一明确值取得 retention，或增加一致性检查 |
| Album cooldown | `history.dedupe_same_rg_days`、history loader、recent IDs | production path 没有历史 album hard filter | High | 先决定它是 active hard rule 还是移除/标记 reserved；不得继续保持“声明 active、实际无效” |
| Artist cooldown | config `dedupe_same_artist_days: 7`；`ARTIST_COOLDOWN_DAYS = 7` | 代码常量；config 未读取，且生产 seed 顺序使 history 常为空 | High | 先修复 history input 时序，再选择 config 或代码常量作为唯一 authority |
| Theme cooldown | `THEME_COOLDOWN_DAYS = 3`；foundation/observability wording | 代码常量 | Medium-High；无 config key，且受 history 时序影响 | 明确列为 active product rule，并与 history seed lifecycle 一起验证 |
| Product timezone | config/env `timezone`/`DAILY3ALBUMS_TZ`；Python `_beijing_now()`；UI Intl timezone | 实际固定 Asia/Shanghai；loaded `cfg.timezone` 不参与 build date | Medium，配置看似可切换但产品实际不可切换 | 将 timezone 配置标为 informational/deprecated，或只保留固定产品常量 |
| Output schema version | `config.yaml:output_schema_version`；Python hardcoded `"1.0"`；validators | Python hardcoded值 | Medium | 选择一个 authority，并增加 version compatibility policy |
| Release SLA target | workflow `--target-time 08:00`；`release_sla_summary.py` default；README | workflow explicit input | Low | 保持显式参数和单测；不必与 UI schedule强行生成共享代码 |

必要跨语言重复不自动构成 technical debt。BJT schedule 在 Python 与 TypeScript 中分别执行是合理的；风险来自缺少 contract-level 对齐，而不是“出现了两次”。

## 5. Configuration effectiveness matrix

| Config key | Declared in | Read by | Production effect | Status | Evidence | Recommended action |
| ---------- | ----------- | ------- | ----------------- | ------ | -------- | ------------------ |
| `schema_version` | `config/config.yaml:1` | 无 | 无 | deprecated/misleading | 运行时 schema 分别硬编码 | 删除或明确仅为旧配置版本 |
| `output_schema_version` | `config/config.yaml:2` | 无 | 无；issue 使用 `"1.0"` | misleading | `cli.py:1954-1969` | P2.2 选择唯一 authority |
| `timezone` | `config.yaml:9` | `load_config()` | 被加载但 build 使用固定 `_beijing_now()` | partially_active/misleading | `config.py:97-99`；`cli.py:269-272,1628` | 明确固定产品时区，不暗示可配置 |
| `random_seed_strategy` | `config.yaml:10` | 无 | 无；代码直接构造 date/slot/theme seed | reserved/misleading | `cli.py:1653-1659,1873-1882` | 标记 reserved 或删除 |
| `decade_mode` | `config.yaml:11` | `load_config()`、warning | 只控制 legacy warning；selection 不使用 decade | deprecated | `config.py:116-123`；`cli.py:1587-1591` | 保留明确 deprecated 状态或清除残留 |
| `history.archive_retention_days` | `config.yaml:18` | `AppConfig`、artifact writer call | 控制写出 index retention | active | `config.py:119,142`；`cli.py:2092-2097` | 与 workflow restore 的 7 对齐 |
| `history.dedupe_same_rg_days` | `config.yaml:20` | 无 | 无历史 album hard filter | misleading | `constraints.py:58-98` 收集 keys；筛选未查询 `history.album_keys` | P1 后续任务先定义并实现/退役 |
| `history.dedupe_same_artist_days` | `config.yaml:23` | 无 | 代码硬编码 7；干净 runner history 为空 | misleading | `constraints.py:12`；`cli.py:1641-1643,1825-1833` | P2.2 统一 authority 并补 production-order test |
| `normalizer.min_confidence` | `config.yaml:30` | 无 | 无；CLI default 0.80 被传递后丢弃 | misleading | `dry_run.py:318-345` | P1 后续任务恢复真实过滤或停止输出该约束 |
| `normalizer.ambiguity_gap` | `config.yaml:32` | 无 | 无；CLI default 0.06 被丢弃 | misleading | `dry_run.py:318-345` | 与 confidence 同一任务处理 |
| `normalizer.hard_ambiguity_policy` | `config.yaml:34` | 无 | 无 | reserved/misleading | 全仓仅配置声明 | 标记 reserved 或移除 |
| `normalizer.top_k` | `config.yaml:35` | 无 | 无 | reserved | 全仓仅配置声明 | 移除或改成真实参数名 |
| `normalizer.mb_max_queries_per_candidate` | `config.yaml:36` | `AppConfig`、dry run | 限制 text-search query attempts | active | `config.py:107`；`dry_run.py:198-205` | 保留 |
| `normalizer.mb_max_candidates_per_slot` | `config.yaml:37` | `AppConfig`、dry run | 限制 normalization candidate count | active | `dry_run.py:490-512` | 保留 |
| `normalizer.mb_time_budget_s_per_slot` | `config.yaml:38` | `AppConfig`、dry run | 限制 slot normalization wall time | active | `dry_run.py:490-509` | 保留 |
| `normalizer.weights.*` | `config.yaml:39-44` | 无 | 无 | reserved/misleading | scoring function不读取 | 标记 reserved 或删除 |
| `global_exclusions.*` | `config.yaml:49-51` | 无 | 无；实际由 `allow_types` 和代码检查决定 | misleading | `_type_flags_from_cfg()` 只读 `allow_types` | P2.2 合并为一个类型策略入口 |
| `slots.*.require_cover` | `config.yaml:61,64,67` | 无 | 无；cover 是 enrichment/fallback，不是 selection filter | misleading | `cli.py:1983-2019` | 改名为 reserved policy 或删除 |
| `slots.*.weights` | `config.yaml:62,65,68` | 无 | 无；`_score()` 硬编码公式 | misleading | `dry_run.py:263-299` | Recommendation quality baseline 决定是否启用；本轮不调权重 |
| `allow_types.*` | `config.yaml:73-78` | `_type_flags_from_cfg()` | 控制 production primary type filter | active | `cli.py:1091-1115,1813-1818` | 保留并删除重复无效 exclusion 声明 |
| `themes.rotation/items` | `config.yaml:83-109` | 无 | 无；main build 使用 `tag_pool` | reserved/misleading | `cli.py:305-311,1653-1660` | 明确 reserved 或迁出 active config |
| `tag_pool` | `config.yaml:111-322` | `_get_tag_pool()` | 生产 slot tag 尝试池 | active | `cli.py:305-311,1653-1660` | 保留 |
| `candidates.lastfm.per_page/pages_per_call/deepcut_min_page` | `config.yaml:324-327` | 无 | 无；adapter固定 limit 50，deepcut 使用 page offset | misleading | `dry_run.py:350-378` | 删除或接入真实行为前标记 inactive |
| `candidates.lastfm.lastfm_page_start/max_pages` | `config.yaml:328-329` | `AppConfig`、dry run | 控制 Last.fm page range | active | `config.py:101-103`；`dry_run.py:350-359` | 保留；移除 build fallback duplicate |
| `candidates.discogs.enabled` | `config.yaml:331` | `AppConfig`、dry run | 有 token 时控制 Discogs source | active | `config.py:111-115`；`dry_run.py:387-425` | 保留 |
| Discogs page settings | `config.yaml:332-336` | `AppConfig` | `discogs_*` keys active；`per_page` 仅兼容 fallback | partially_active | `config.py:113-115` | 只保留 canonical key names |
| `candidates.listenbrainz.count/deepcut_min_offset` | `config.yaml:337-339` | 无 | 无；count/offset 硬编码 | misleading | `dry_run.py:370-371,426-469` | P2.2 接入或移除 |
| `scoring.multi_source_bonus` | `config.yaml:342` | 无 | 无；代码硬编码 `6.0` | misleading | `dry_run.py:263-265` | Recommendation baseline 后决定 authority |
| rank threshold scoring keys | `config.yaml:343-345` | 无 | 无；代码硬编码 18/60/25 | misleading | `dry_run.py:266-287` | 同上 |
| `scoring.temperature_by_slot` | `config.yaml:346-349` | 无 | 无；`cmd_build()` 硬编码相同值 | misleading | `cli.py:1873-1882` | P2.2 选择 config 或代码常量 |
| `scoring.mb_normalize_budget_cap` | `config.yaml:350` | 无 | 无 | deprecated/misleading | 无读取引用 | 删除或标记 deprecated |
| `scoring.mb_prefilter_topn` | `config.yaml:351` | `load_config()` fallback | 当前被 `coarse_top_n_per_slot` 覆盖 | partially_active/misleading | `config.py:110` | 只保留一个 key |
| `scoring.coarse_top_n_per_slot` | `config.yaml:352` | `AppConfig`、dry run | 控制 light prefilter top N | active | `cli.py:1612,1704`；`dry_run.py:486-489` | 保留并改名清晰化可另议 |
| `build.max_tag_tries_per_slot` | `config.yaml:356` | `AppConfig`、build | 控制每 slot tag attempts | active | `cli.py:1653-1660` | 保留 |
| `build.lastfm_max_pages` | `config.yaml:357` | 仅作为 fallback | 被 candidate key 覆盖 | partially_active/misleading | `config.py:102` | 删除 duplicate fallback |
| `build.ui_build_timeout_s` | `config.yaml:358` | `AppConfig`、subprocess | 控制本地 one-command UI build timeout | active | `cli.py:2051-2069` | 保留 |

## 6. Generator and recommendation runtime findings

### TD-01 — history seed 恢复晚于 history/cooldown 读取

- Severity：P1。
- 当前行为：`cmd_build()` 在 `cli.py:1641-1643` 从 `_build/public/data` 读取 recent IDs 和 history；完成生成、UI copy 和 data reset 后，才在 `cli.py:2083-2084` 把 `DAILY3ALBUMS_HISTORY_SEED_DIR` 复制进输出。
- Production path：workflow 在 `.github/workflows/pages_daily.yml:145-172` 先把有效 seed 放入 `.state/pages-history-seed/data`，再把路径作为 env 交给 build；但 build 没有在 selection 前读取该目录。
- 影响：干净 GitHub runner 上 artist/theme history filters 没有历史输入；observability 中的 cooldown rejections 可能长期为零，不能证明没有历史冲突。
- 建议：下一任务先建立一个只读 seed/history input phase，再开始 candidate generation；增加模拟干净 output + external seed 的 integration test。此项属于行为修复，不应与大范围 config 重构混在一个 PR。

### TD-02 — normalization thresholds 被声明、传递和写出，但不执行

- Severity：P1。
- 当前行为：CLI defaults 是 0.80/0.06；config 声明 0.72/0.08，但 config values 未读取。`run_dry_run()` 在 `dry_run.py:344` 执行 `del min_confidence, ambiguity_gap`，随后只要 best match 非空就构造 `NormalizedCandidate`。
- 输出漂移：`cli.py:1928,1965` 仍把 CLI values 写成 `constraints`，会让产物读者误以为这些阈值已应用。
- 测试缺口：现有 61 个 Python tests 全绿，但没有验证低 confidence/ambiguous match 会被 runtime threshold 拒绝。
- 建议：独立 P1 修复任务先定义 hint/direct-MBID/text-search 三条路径的置信语义，再恢复 threshold/policy；不要在该任务中调整 scoring weights。

### TD-03 — album history dedupe 名存实亡

- Severity：P1。
- 当前行为：`load_history_index()` 收集 `album_keys`，但 `cmd_build()` 只检查当日 `used_album_keys`；`_load_recent_stable_ids()` 只读 archive 顶层 `picks`，而 production issue 的顶层 `picks` 仅代表当前时段的 3 张。即使读到 recent IDs，weighted sampling 也传入 `cooling_penalty=None`。
- 影响：`history.dedupe_same_rg_days: 7` 不会阻止跨日专辑重复；配置注释还写着“60 天内不重复”，与实际 key value 7 自相矛盾。
- 建议：先决定 hard dedupe 的正式天数和失败策略，再实现并测试；不要把 recommendation quality 权重调整夹带进来。

### 其他 runtime findings

- `_score()` 硬编码 multi-source bonus、rank thresholds 和 deepcut penalty；config 中同名值只是镜像，修改不会生效（P2）。
- slot temperature 在 `cmd_build()` 中硬编码 9/10/14，config 同值不生效（P2）。
- `themes.items` 与 slot weights 没有进入 main build；`tag_pool` 才是真实 theme/tag source（P2）。
- `--n` 在 build 中被提升为至少 200，`--topk` 被提升为至少 fetch limit；workflow 文案称输入“接进 build 参数”虽然字面正确，但常用小值几乎不改变 candidate window（P2，operator semantics）。
- `split_slots` 参数在 production build 默认 true，但 `cmd_build()` 自己固定循环三个 slots，传给 `run_dry_run()` 时固定 `split_slots=False`；`--no-split-slots` 不改变这条主编排（P2，CLI surface misleading）。
- Discogs 和 ListenBrainz 是 soft sources；失败会记录有限 diagnostics 并继续。该设计合理，但 broad `except Exception` 降低了错误分类精度（P2.3）。
- enrichment 的 cover/MusicBrainz detail/Wikipedia failure 多数降级为缺失 metadata；当前 observability 有 attempted/success，缺少明确的 provider failure/no-data 区分（P2.3）。

## 7. Public schema and validation findings

### Schema map

| Artifact | Writer | Python validation | Browser parsing/usage | Finding |
| --- | --- | --- | --- | --- |
| `today.json` | `artifact_writer.write_daily_artifacts()` | `validate_today()` + `self_check._validate_today()` | `parseTodayIssue()` | 三套手写 contract，required fields 不完全相同 |
| archive JSON | 同 today issue | seed restore 使用 `validate_today()`；self-check只验证 current archive | `loadArchiveDay()` + `parseTodayIssue()` | retained historical files不由 self-check逐项复验；seed restore承担主要门槛 |
| `index.json` | artifact writer | seed restore、self-check各自验证 | `parseArchiveIndex()` | browser会过滤坏 item；self-check会失败，错误语义不同 |
| `meta.json` | Pages workflow inline Python | 无 | UI 不读取 | public artifact 无 consumer/validator，当前是运维元数据 |
| `recommendation-observability.json` | `cli.py` | self-check只验证核心 count；summary script兼容旧字段 | UI 不读取 | build-time diagnostics contract独立，方向合理但 schema 未集中 |

### Findings

- Severity P2：`validate_today()` 要求 `rg_mbid` 和 cover URL，却不要求 pick title/slot enum；self-check 要求 title 和非空 slot，却不要求 `rg_mbid`；TypeScript 要求 slot 为三个 role 之一、title 和 cover URL，并静默丢弃不合格 pick。
- Severity P2：`parseTodayIssue()` 只要最终仍有至少一个 pick 就可返回；production self-check normally 阻止少于 3×3 的列表，但某个 pick 的非法 slot enum 仍可能在浏览器被丢弃而 Python self-check通过。
- Severity P2：schema version 只检查“非空字符串”或被直接透传，没有显式 version dispatch、migration 或拒绝未知 version 的策略。
- Severity P2：`loadArchiveDay()` 对 run-specific path 的 HTTP、JSON 和 schema 任意错误都 catch 后回退 legacy date alias；可用性较好，但会掩盖“文件缺失”和“文件存在但无效”的区别。
- Severity P3：`meta.json` 当前没有 browser consumer，也不由 self-check验证。若仅供人工/运维读取，应在文档中明确；若声称用于前端 cache/version alignment，则实现不一致。
- Not debt：`recommendation-observability.json` 不进入 browser runtime 是合理的静态 build diagnostics boundary。

P2.2 不需要引入跨语言代码生成框架。优先建立一组 canonical JSON fixtures/contract tests，明确 required/optional/version policy，再评估是否值得使用 JSON Schema。

## 8. UI state and component-boundary findings

| Area | Current responsibility and input | State ownership | Structural finding | Recommended phase |
| --- | --- | --- | --- | --- |
| App/HUD | BJT clock、theme、global HUD、Project Info、routes | `App` + `HudContext` | App 与 routes 都每 500ms 推导 BJT；context value含完整 HUD，routes用 ref 规避 effect feedback | P2.3 small refactor |
| Today Page | data fetch/fallback、slot unlock、timeline、Viewer、Share、Ambient、Time Lab、signals、transitions、idle | `TodayRoute` 约 1,031 lines、17+ local states/多组 timers | 业务状态、network recovery、debug clock、preload、navigation和DOM presentation高度混合 | P2.3 before major UI implementation |
| Archive Page | index + all retained issues、HUD status、BJT state、render | `ArchiveRoute` | 业务读取与完整列表DOM渲染同组件；当前 eager `Promise.all` | P2.3；性能改动仍属独立 backlog |
| Album Card / `SlotCard` | pick presentation、cover state、links/select | component local | Viewer trigger与卡片 presentation接口相对清楚 | No blocking action |
| Treatment Viewer | active pick navigation、keyboard/swipe、async cover state、dialog | overlay component | 420 lines但核心行为已封装，shell/cover分离清楚；不需为未知视觉方案预拆 | Future UI implementation only when required |
| Share Card Dialog | version/language/theme/export、image readiness、canvas DOM | dialog local | data derivation和export presentation耦合，381 lines；version logic已在 lib 分离 | P2.3 incremental extraction |
| Ambient Overlay | overlay presentation + exit | Today owns open state | 简单边界；性能风险已记录但本轮不处理 | Non-blocking backlog |
| Time Lab/debug | URL/session debug time + UI controls | App 与 Today 均读取/更新 | debug BJT state存在两套定时推导 | P2.3 shared clock service/hook |

对未来较大 UI 改造真正的通用阻塞是：TodayRoute 同时拥有数据恢复、BJT业务状态、overlay navigation 和视觉 transition；HUD state 在 App 与 route 之间通过 mutable partial updates 协作；测试中部分 policy 直接搜索源码字符串/CSS片段。它们会让任何视觉替换意外触碰业务行为。

以下不是阻塞：当前 Album Card 形态、Viewer overlay 形态、现有颜色或动画语言。未来视觉概念尚未确定，本报告不建议新的组件命名、卡牌/手牌结构或 presentation architecture。

## 9. CSS and presentation-layer findings

当前 `ui/src/styles.css` 为 2,747 行单文件，统计到 22 组 keyframes、26 行 animation、22 个 z-index 声明、41 行 hex color 和 24 个 `!important`。另有 Tailwind theme tokens、CSS custom properties 和大量 JSX arbitrary utilities，形成三层并存：

1. Tailwind semantic extensions；
2. `:root`/theme CSS variables；
3. component/global selectors 和 JSX 中的具体值。

Findings：

- P2：day-theme adapter 在 `styles.css:1411-1492` 使用 18 个左右 `!important` 覆盖 Tailwind class family，说明 theme semantic layer与utility class耦合。
- P2：responsive override 集中在 900/767/430 三个手写 media blocks，同时 JSX 使用 `sm/md/lg/xl` Tailwind breakpoints；两套 breakpoint authority 增加覆盖链追踪成本。
- P2：HUD、Viewer、Share、Ambient、transition 和 page layout 都在同一 global stylesheet；未来替换一个视觉区域时难以界定删除范围。
- P3：多个 z-index scale（10、20、50、60、70、80、90、120及局部负值）没有集中 layering contract。
- P3：颜色/spacing/radius/shadow 已有部分 token，但仍有 hardcoded CSS/JSX；这是“设计系统未完全建立”，不是当前功能阻断。
- Not debt：同一 selector 在 base 与 mobile media 中重复属于必要 responsive override，不能仅凭重复次数判定 stale style。
- Not debt：Reduced Motion block覆盖主要持续动画，现有 40 个 UI unit tests包含源码/CSS policy guards；它们不是完整视觉验证，但提供当前回归门槛。

P2.3 可按职责把 global foundations、theme adapter、layout、overlay 和 feature styles分段/拆文件，但不应在没有新视觉方案时设定新 token 数值或重写 CSS。

## 10. Workflow, scripts, and validation findings

- P2：CI/Pages 使用 Node 24，当前固定本地工具链为 Node 22.13.0。二者均可能成功，但 runtime major drift 会降低“本地通过”等同“CI通过”的可信度。
- P2：Pages workflow 的 `n/topk` inputs 对常用值语义弱；需要在 CLI层明确 effective values 或收窄/退役 inputs。
- P2：recommendation observability summary 和 build metrics summary 都是 `continue-on-error: true`。metrics/summary 非阻断本身合理，但 summary renderer损坏可能只在日志中出现，缺少单独 health signal。
- P3：`meta.json` 用 workflow inline Python 写出，既不经过 generator schema，也不经过 self-check；职责与 consumer 不清晰。
- P3：workflow 内仍有“方案A核心/附加”等历史实现注释，和 current-state runbook 风格不一致，但不影响行为。
- Not debt：Pages workflow 重跑 Python/UI tests 与 PR CI 有重复成本，但它作为 daily production gate可发现 schedule时的依赖/环境问题，当前不建议仅为去重删除。
- Not debt：Doctor 已从 CLI、package scripts 和 active workflow 退出；仅在 AGENTS、legacy docs和防回归 test中出现，属于有意保留。
- Not debt：build metrics、recommendation observability、browser smoke和performance audit职责独立，没有被 Doctor 包裹。

脚本入口状态：

- Active：`build_metrics.py`、`golden_check.py`、`recommendation_observability_summary.py`、`release_sla_summary.py`、`restore_static_archive_seed.py`、`self_check.py`。
- Manual-only：`update_golden.ps1`，但它依赖 global `python`，与本机固定工具链规则冲突；P3。
- No references/empty：`bootstrap_pages.ps1`；高置信 dead file。
- One-off asset helper：`make_placeholder.py` 生成 `web/assets/placeholder.webp`，当前 UI/生成器使用 `assets/placeholder.svg`；P3 cleanup candidate。

## 11. Dead code and historical residue

### Dead-code confidence table

| Candidate | Reference search | Runtime entrypoint check | Test/workflow check | Confidence | Recommendation |
| --------- | ---------------- | ------------------------ | ------------------- | ---------- | -------------- |
| `daily3albums/alerter.py` | 文件为空；无 imports | CLI 不引用 | tests/workflows 不引用 | High | P2.3 删除空模块；SMTP env另行清理 |
| `daily3albums/engine.py` | 文件为空；无 imports | CLI 编排在 `cli.py` | 无测试引用 | High | P2.3 删除 |
| `daily3albums/r2_state.py` | 文件为空；无 imports | 无 CLI command | 无 workflow引用 | High | P2.3 删除；R2 env标记 deprecated |
| `daily3albums/image_optimizer.py` | 文件为空；无 imports | cover adapter直接返回 URL | 无测试引用 | High | P2.3 删除 |
| `daily3albums/log_jsonl.py` | 文件为空；无 imports | logger不引用 | 无测试引用 | High | P2.3 删除 |
| `ui/src/components/BioClock.tsx` | 仅自定义义；无 import | `FLAGS.bioClock` 未消费 | 无 test引用 | High | P2.3 删除或重新确认产品需求；不要因 flag=true认定 active |
| `FLAGS.bioClock/fullscreen/i18n` | 只有声明 | UI不读取 | 无 test覆盖其行为 | High | P3 删除 inactive flags |
| `scripts/bootstrap_pages.ps1` | 空文件 | 无 package/CLI入口 | 无 workflow/docs引用 | High | P3 删除 |
| `scripts/make_placeholder.py` + `web/assets/placeholder.webp` | helper自引用 | production fallback为 SVG | 无 tests/workflow调用 | Medium-High | 确认无手工资产流程后删除 |
| `_threshold_steps()` | 只有定义 | 无调用 | 无 test直接覆盖 | High | 与 threshold P1 修复一起处理，不先删除意图证据 |
| `_weighted_sample()` | 只有定义；production用 unique-artists版本 | 无 runtime调用 | 无 test引用 | High | P2.3 删除或合并 |
| `_now_date_in_tz()` | 只有定义 | build用 `_beijing_now()` | 无 test引用 | High | P3 删除 |
| `_ensure_nonblank_index_html()` | 只有定义 | build未调用 | 无 test调用 | High | P3 删除；同时评估 builtin fallback |
| `ui/public/brand/slot-window-set-vertical.svg` | 仅被未消费 CSS variable引用 | DOM/CSS不使用 variable | tests不验证 | Medium-High | 标记 stale asset；与未来视觉任务分离清理 |
| root `docs/art-direction.md` / `art-assets-spec.md` | active-looking标题与明确旧视觉方向 | 不影响 runtime | 不在 legacy/revive/snapshot | Medium | 不删除；先给文档状态/authority分类，避免与“未来视觉未定”冲突 |

`docs/archive/REVIEW_REPORT.md` 中已修复或过时的 finding 位于明确 archive 区域，不计 active debt。`docs/revive/`、`docs/legacy/` 和 foundation snapshots 同理。

## 12. Error-semantics findings

| Area | Current semantics | Ambiguity/risk | Severity | Recommendation |
| --- | --- | --- | --- | --- |
| History loading | malformed date/JSON被 `continue` 静默跳过 | “无历史”与“历史损坏”相同 | P2 | 返回 structured warnings/counts；production seed validation继续 hard gate |
| Artifact index load | parse/schema error回退空 index | 本地无 seed路径可能把损坏视为首次历史 | P2 | 区分 missing、empty-allowed、corrupt |
| Discogs/ListenBrainz | source failure后继续，记录有限 diagnostics | soft failure合理，但 broad exception丢失原因 | P2 | 保留 soft source，增加 provider/stage/error class |
| Cover/MB detail/Wikipedia | exception/no relation/no result多降级为 `None` | 外部失败与真实缺失 metadata混合 | P2 | observability区分 unavailable、not_found、request_failed |
| Browser archive fallback | run path任意错误后尝试 date alias | file missing与schema invalid被合并 | P2 | fallback保留，但记录 primary failure type |
| Today network recovery | stale date/fetch/parse均进入 SIGNAL_LOST并使用 last-good/archive | 用户可用性良好，但 UI message不能定位根因 | P3 | 保持用户降级；debug/telemetry层保留细分 error kind |
| Summary steps | `continue-on-error` | diagnostics renderer失败不阻断 deploy | P3 | 在 workflow summary或issue中显式 warning |

## 13. P2.2 source-of-truth candidates

按优先级排序：

1. **History input lifecycle**：让 validated seed 在 candidate selection 前成为只读 history source；建立干净 runner integration test。
2. **Recommendation config status**：为每个 key显式区分 active/reserved/deprecated；优先处理 thresholds、album/artist/theme cooldown、type policy。
3. **Scoring/sampling authority**：在 recommendation quality baseline之后，决定 scoring constants/temperature 是代码常量还是 config；本阶段不调数值。
4. **Candidate budget keys**：消除 `coarse_top_n`/`mb_prefilter_topn`、candidate/build Last.fm pages、Discogs aliases 和无效 LB keys。
5. **Public contract fixtures**：对齐 Python writer、seed validator、self-check 和 TypeScript parser 的 required/optional/version语义。
6. **Product schedule contract**：保留 Python/TypeScript各自实现，用共享fixture/contract test验证 08:00/12:30/16:00、3×3和Share Card版本。
7. **Archive retention**：对齐 config、restore workflow和UI fallback；不为单一数值引入复杂生成系统。
8. **Environment contract**：清理 ALERT/SMTP、R2、ListenBrainz token等声明与 workflow names，标记 active build secrets。

其中第 1、2 项包含当前 P1 行为，建议在正式 P2.2 大整理前先拆成两个小而可验证的修复任务。

## 14. P2.3 small-refactor candidates

按优先级排序：

1. 把 TodayRoute 的 BJT clock/data recovery 与纯 presentation 分离，保持现有 UI不变。
2. 收敛 App/HUD/Today/Archive 的 500ms clock ownership，避免重复推导和 context/ref workaround。
3. 为 external soft failures建立 structured result/error kinds，先不改变降级策略。
4. 将 public schema validation helpers按 artifact集中，并增加 cross-layer fixtures。
5. 分拆 `styles.css` 为 foundation/theme/layout/feature sections或文件，不改变设计 token数值。
6. 删除高置信空模块、dead helpers、inactive flags和空脚本。
7. 把 Share Card export orchestration从381行 dialog中抽出可测逻辑。
8. 清理 workflow历史注释和 fixed-toolchain不一致的 `update_golden.ps1`。

## 15. Non-blocking backlog

- root art-direction/assets docs的 authority/status标记；不阻塞代码和新视觉研究。
- `meta.json` consumer/validator说明。
- stale brand SVG、WEBP placeholder和one-off helper清理。
- CSS z-index contract、低风险命名与注释整理。
- workflow summary failure warning。
- Archive progressive rendering、Ambient layers、startup CLS继续保留在既有性能 backlog；本轮不实施也不重新审计。
- 未来视觉系统的颜色、字体、网格、动画和组件形式；必须等待明确视觉目标。

## 16. Confirmed non-issues

- 没有 visitor-side external music/data API；静态 GitHub Pages架构边界保持清楚。
- Doctor 已退役，无 active CLI/workflow/package入口残留。
- Archive seed restore 本身有 provider validation、baseline和atomic promotion；本次问题是 generator读取时序，不是否定 restore机制。
- Same-day published archive lock、historical byte immutability和retention写出有现有 tests覆盖。
- `tag_pool`、MB budgets、Discogs enable/page settings、`allow_types`、max tag tries、UI timeout和archive retention均有真实生产读取路径。
- Build Metrics 与 Recommendation Observability职责独立，public observability JSON不是browser runtime API。
- BJT schedule、每天9张、三时段和Share Card版本在当前源码/tests/README中一致。
- Treatment Viewer的overlay、navigation和async cover边界已封装；不需要为了未知视觉方向预设新组件体系。
- 历史目录中的旧时间、Doctor或旧 finding 是有意保存的记录，不属于 active technical debt。
- Python 61 tests和UI 40 tests全绿；本报告没有把未运行的build/browser/deployment检查写成通过。

## 17. Recommended execution order

1. **P1 fix A：history seed before selection**。只调整history input lifecycle和对应integration tests；不改算法权重、不做config大重构。
2. **P1 fix B：normalization threshold truthfulness**。明确并实现/退役 confidence、ambiguity、policy；同步产物语义和tests。
3. **P1 fix C：album dedupe contract**。决定正式天数和hard/soft行为，使用真实seed fixture验证跨日重复。
4. **P2.2-A：active config inventory cleanup**。把 active/reserved/deprecated状态落实到config surface，保持已验证行为。
5. **P2.2-B：public schema contract fixtures/version policy**。
6. **P2.2-C：schedule/retention/environment contract checks**。
7. **P2.3-A：UI clock/state ownership小步拆分**，不得夹带视觉改版。
8. **P2.3-B：error semantics与dead code清理**。
9. **Recommendation quality baseline**，之后才决定 scoring/weights是否配置化或调参。
10. **Future UI implementation**，等待单独确认视觉概念后开始。

停止条件结论：

- P0：无。
- P1：3 项，分别为 history seed读取时序、normalization thresholds无效、album history dedupe无效。
- 最重要的 source-of-truth 漂移：recommendation runtime config与实际调用路径。
- 不阻塞未来视觉设计：dead code、config aliases、meta consumer、workflow注释、schema fixture和大多数CSS组织问题。
- 仍不确定：正式 album cooldown天数/是否hard rule；normalization对hint/direct MBID路径应采用何种threshold；root art docs未来是否仍具authority；`meta.json`是否有仓库外consumer。
- 下一项工程任务的明确边界：只修复 validated history seed 在selection前可读，并用干净runner fixture证明 artist/theme history filters生效；不同时实施threshold、album dedupe、scoring/config重构、UI或视觉改动。
