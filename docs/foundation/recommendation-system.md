# Recommendation System

本文说明当前专辑推荐实现。它面向后续算法维护，不是产品宣传文案。

## Daily Structure

当前每天生成 9 张专辑：

- 3 个 BJT slot
- 每个 slot 3 张专辑
- 北京时间 06:00、12:00、18:00 解锁

当前窗口：

- slot 0：06:00-11:59
- slot 1：12:00-17:59
- slot 2：18:00-23:59

`today.json` 包含完整 3 个 slots。top-level `picks` 是 build-time 当前 slot 的 picks。前端会读取完整 slots，并按浏览器当前 BJT 状态控制 Today Page 可见内容。Archive Page 渲染历史 slots，不受当天解锁门控影响。

## Theme, Genre, And Tag

当前 build 主流程以 `config/config.yaml` 中的 `tag_pool` 作为每个 slot 的主要主题池。每个 slot 用 `date_key:slot_id` hash 到 tag pool 起点，再最多尝试 `build.max_tag_tries_per_slot` 个 tag，当前配置为 8。

`themes.items` 仍存在于配置中，但当前 `cmd_build()` 主流程主要从 `tag_pool` 选 tag。除非代码改成直接使用 `themes.items`，否则不要把它写成当前 active schedule。

每个 slot 的 `theme` 是实际选中的 tag。issue 顶层 `theme_of_day` 来自显式 `--theme`，否则来自 CLI `--tag`，否则是 `"auto"`。它不一定等于人工策展的每日主题名。

MusicBrainz tags 会在 detail enrichment 后合并进每个 pick。它们是 metadata，不是当前显式的 genre balancing 目标。

当前 cooldown：

- 同日已采用的 theme key 会通过 `used_theme_keys` 被避开。
- 跨日 theme cooldown 为 3 天，即 `THEME_COOLDOWN_DAYS`。
- 除 tag 选择、tag cooldown 和 metadata tags 外，源码中未见显式 genre 均衡模型。

## Candidate Sources

### Last.fm

Last.fm 是必需候选来源。生成器按 tag 和 page 调用 `tag.getTopAlbums`，候选字段包括 title、artist、可选 MBID、rank 和 image URL。

### Discogs

Discogs 是可选候选来源。只有 `DISCOGS_TOKEN` 存在且配置启用时参与。它提供 search candidates 和 source ranks，可以通过 multi-source bonus 和 rank signals 影响候选得分。

Discogs detail enrichment 当前没有写入最终公开 pick JSON。

### ListenBrainz

ListenBrainz 是软性的可选候选来源。dry-run 会尝试 sitewide release-group stats 和 metadata，按 tag 过滤，并提供 release-group MBID hints。失败会被忽略。

### MusicBrainz

MusicBrainz 是归一化和 enrichment 来源。它通过直接 MBID、release-to-release-group 或 fallback search 把候选映射到 release-group ID，并提供最终公开数据使用的 release-group details。

MusicBrainz 当前不是普通候选来源，而是核心识别层。

## Normalization And Metadata Enrichment

候选归一化优先使用现有 MBID hints：

1. 把 Last.fm MBID 当作 release-group MBID 尝试。
2. 必要时把它当作 release MBID，再解析到 release-group。
3. 使用 ListenBrainz 提供的 release-group hint。
4. fallback 到 MusicBrainz release-group search，包括 strict、cleaned、loose 和 title-only 查询。

最终 pick item 可以包含：

- release-group MBID
- title 和 artist credit
- artist MBIDs
- first release year
- primary type
- album key、artist keys、style/theme keys
- Last.fm/config tag 与 MusicBrainz tags
- MusicBrainz rating 和 votes
- 从 MusicBrainz URL relation 获取的 Wikipedia overview
- cover metadata
- MusicBrainz link 和 YouTube search link
- mapping confidence、score 和 reason

字段允许缺失。MusicBrainz rating 缺失时写 `null`，UI 显示 missing metadata。Wikipedia overview 缺失时写 `null`，UI 显示 empty overview。封面按 Cover Art Archive、候选图片、`assets/placeholder.svg` 退回。

## Filtering Rules

当前 build 的硬过滤包括：

- 排除 Various Artists。
- 只允许配置允许的 primary type。当前配置允许 Album 和 EP，不允许 compilation、live、single 等非目标类型。
- 同日 album key 不重复。
- 同日 artist 不重复。
- 7 天 artist cooldown，即 `ARTIST_COOLDOWN_DAYS`。
- 3 天 theme cooldown，即 `THEME_COOLDOWN_DAYS`。
- 候选必须完成 MusicBrainz 归一化才能进入最终 eligible pool。

重要边界：

- 历史 album cooldown 当前未确认是硬过滤。代码会收集历史 album keys，也会读取 recent release-group IDs，但当前 weighted sampling 调用没有传入 cooling penalty。
- `history.dedupe_same_rg_days` 存在于配置中，但当前审阅到的 build 主流程没有把它作为历史专辑硬冷却执行。
- `require_cover` 存在于 slot 配置中，但当前行为是软性 cover preference/fallback。Cover Art Archive 可以失败，候选图片和 `assets/placeholder.svg` 都是有效退路。

如果某个 slot 在配置的 tag attempts 和 fetch windows 后仍找不到 3 个 eligible candidates，build 会以 candidate-pool exhaustion diagnostics 失败，而不是编造 picks。

## Scoring And Sampling

当前得分由 `daily3albums/dry_run.py::_score()` 计算，主要信号包括：

- multi-source bonus
- rank shape，包括 head peak 和 tail boost
- DeepCut top-rank penalty
- MusicBrainz quality bonus，包括 release-group ID、Album primary type 和 release date
- 基于 seed 和 album key 的 deterministic jitter

MusicBrainz 归一化前有轻量 prefilter，会给 MBID hint 和 release-group hint 小幅加分。`coarse_top_n_per_slot`、`mb_max_candidates_per_slot` 和 `mb_time_budget_s_per_slot` 控制预筛选和归一化工作量。

最终 slot selection 使用 deterministic `random.Random` seed，seed 来自 date、slot id 和 theme key。抽样用 softmax weights，并在抽样集中保持 unique artists。抽到 3 张后按 score 降序排序，再分配角色标签。

配置中存在 `slots.*.weights`、`scoring.multi_source_bonus` 和 `scoring.temperature_by_slot`。但当前审阅到的主 build 路径使用 `dry_run.py` 中的硬编码得分公式，并在 `cmd_build()` 中硬编码 slot temperature 为 9.0、10.0、14.0。维护时以代码实现为准。

## Slot Role Labels

每个产品 slot 中的 3 张 pick 使用这些角色标签：

- Headliner
- Lineage
- DeepCut，UI 显示为 Deep Cut

当前 `cmd_build()` 行为是：每个 slot 先加权抽样出 3 个 eligible candidates，再按 score 降序排序，依次标为 Headliner、Lineage、DeepCut。

因此这些标签当前更接近轻量策展/UI 角色，不是强算法约束。UI copy 会解释角色意图，但 build 主流程没有显式按年代选择 Lineage，也没有完整 smallness model 来选择 DeepCut。

`daily3albums/dry_run.py` 的 split-slot helper `_pick_slots()` 有另一套 Lineage 年份逻辑，但当前 daily build 没有用它分配最终角色。

## Current Shortcomings

当前明确短板：

- 小众度没有显式建模。现有近似来自 rank、tail boost、DeepCut offset/penalty 和 weighted sampling。
- 地区、语言、性别、年代均衡没有显式建模。
- 最终 pick JSON 中 `popularity` 当前为 `null`。
- Discogs detail enrichment 尚未完整写入最终公开 JSON。
- MusicBrainz 和 Wikipedia 覆盖率可能让 metadata 更完整的发行更容易显得“质量高”。
- 推荐可观测性仍是后续方向：candidate counts、source share、rejection reasons、metadata missing rate、最终 9 张的 year/region/language coverage、enrichment success rate 等应先被报告，再调整算法权重。

## Source basis

Verified from source:
- 每日 issue 结构和 3-slot validation：`daily3albums/artifact_writer.py`、`scripts/self_check.py`、`ui/src/lib/types.ts`。
- BJT slot 行为：`daily3albums/cli.py` 和 `ui/src/lib/bjt.ts`。
- tag selection 与 build loop：`daily3albums/cli.py`。
- 候选、归一化、得分和抽样输入：`daily3albums/dry_run.py`、`daily3albums/adapters.py`、`daily3albums/constraints.py`。
- Slot role 渲染和文案：`ui/src/components/SlotCard.tsx`、`ui/src/components/TreatmentViewerOverlay.tsx`、`ui/src/strings/copy.ts`。
- 配置值：`config/config.yaml`。

Inferred from current behavior:
- Headliner / Lineage / DeepCut 当前主要是 UI/策展标签，因为 build 主流程按 sampled score order 分配。
- 当前推荐容易偏向 metadata 完整的候选，因为最终 picks 依赖 MusicBrainz 归一化和 details。

Not implemented / Not confirmed:
- 显式 smallness score 未实现。
- 地区、语言、性别、年代均衡未实现。
- 完整 Discogs detail enrichment 写入公开 JSON 未实现。
- `history.dedupe_same_rg_days` 作为历史专辑硬冷却未确认实现。
