# 2026-06 Recommendation Algorithm Audit

审计日期：2026-06-26
范围：只审计当前每日 9 张专辑如何产生，不重写推荐算法。阅读范围包括 `config/config.yaml`、`daily3albums/cli.py`、`daily3albums/dry_run.py`、`daily3albums/adapters.py`、`daily3albums/constraints.py`、`ui/src/components/SlotCard.tsx`、`ui/src/components/TreatmentViewerOverlay.tsx`。

## 总览结论

当前生成链路是“每日 3 个时段 x 每时段 3 张专辑”。每个时段先从 tag pool 确定一个候选主题，再从 Last.fm、可选 Discogs、可选 ListenBrainz 拉候选，使用 MusicBrainz 做 release-group 归一化和详情补全，最后通过硬过滤、打分和加权抽样选出 3 张。

这套算法已经有基础去重、艺人冷却、主题冷却、类型过滤、候选耗尽诊断和 provider 失败诊断。主要短板是：小众度仍主要由榜单 rank、deepcut page offset 和 top-rank penalty 间接表达；地区、语言、性别、多年代均衡没有显式目标；Discogs 目前只补候选，不补最终 metadata；内容质量容易向 metadata 完整的英语/欧美专辑倾斜。

## Theme / Genre / Tag 如何产生

- 配置源：`config/config.yaml` 的 `tag_pool` 是当前主要主题池；`themes.items` 仍存在，但 build 主流程实际按 tag pool 轮转。
- 每个 slot 的初始 tag：`daily3albums/cli.py` 以 `date_key:slot_id` 做 hash，映射到 tag pool 的起点。
- 同日去重：build 维护 `used_theme_keys`，已被当前 slot 采用的 theme 会被排到后面。
- 跨日冷却：`daily3albums/constraints.py` 中 `THEME_COOLDOWN_DAYS = 3`；build 会读取最近 archive history，跳过冷却期内出现过的 theme。
- 容错：每个 slot 最多尝试 `build.max_tag_tries_per_slot` 个 tag，当前配置为 8；候选池耗尽会输出 `candidate_pool_exhausted` 诊断。

## 三个 Slot 如何分配

- 产品 slot 固定为 3 个北京时间窗口：`06:00-11:59`、`12:00-17:59`、`18:00-23:59`。
- build 每次生成全天 3 个 slot，不只生成当前时段；Today Page 再按当前 BJT 解锁可见内容，Archive 不受当天 unlock 限制。
- 每个 slot 独立选 tag、拉候选、过滤和抽样。当天内共享 `used_album_keys`、`used_artist_keys`、`used_theme_keys`，因此同日不同 slot 之间会避免专辑和艺人重复。

## Headliner / Lineage / Deep Cut 如何产生

- `slot_names = ["Headliner", "Lineage", "DeepCut"]`。
- 对每个产品 slot，build 先从 eligible candidates 中用 `_weighted_sample_unique_artists(..., count=3)` 抽 3 张，再按 score 降序排序。
- 排序后的第 1、2、3 张依次标记为 Headliner、Lineage、DeepCut。
- 注意：`daily3albums/dry_run.py` 的 `_pick_slots()` 在 `split_slots` 模式下会把 Lineage 选成最早年份、DeepCut 选成剩余项；但当前 `cmd_build()` 主流程不是直接使用该逻辑，而是按 score 后的顺序 zip slot names。

## 每日 9 张候选池来自哪里

每个 slot 的候选池由 `run_dry_run()` 形成：

- Last.fm：`tag.getTopAlbums` 是硬依赖，按 tag 和 page 拉 top albums。
- Discogs：如果 `DISCOGS_TOKEN` 存在且 `candidates.discogs.enabled` 为 true，用 `database/search` 按 tag 拉 master/album 结果，作为候选源之一。
- ListenBrainz：尝试站内 release-group stats + metadata；失败会被吞掉，属于软候选源。
- MusicBrainz：用于把候选归一化到 release-group，并提供 first-release-date、primary-type、artist MBIDs 等。
- Cover Art Archive：最终 item 阶段按 MusicBrainz release-group 拉封面。
- Wikipedia：最终 item 阶段从 MusicBrainz URL relation 找 Wikipedia URL，再请求 page summary 作为 overview。
- YouTube：不请求 API，只生成搜索 URL。
- Local cache：外部请求走 `RequestBroker`，受 endpoint policy、缓存、重试和限速约束。

## 评分、权重、过滤、Fallback

当前 score 由 `daily3albums/dry_run.py::_score()` 计算，主要包括：

- 多来源加分：候选同时来自多个 source 会加分。
- rank 形状：靠前 rank 有 head peak；尾部 rank 有 tail boost。
- DeepCut 调整：deepcut 模式下，对 rank <= 25 的过热候选扣分，并轻微改变 Last.fm / Discogs page offset。
- MusicBrainz 质量加分：有 release-group id、primary type 为 Album、有发行日期会加分。
- deterministic jitter：按 seed 和 album key 加很小扰动，让同一天同参数可复现。

进入抽样前还有硬过滤：

- 排除 Various Artists。
- 只允许配置允许的 primary type，当前 Album / EP 允许，Compilation / Live / Single 等不允许。
- 同日 album key 不重复。
- 同日 artist key 不重复。
- 7 天 artist cooldown。
- 3 天 theme cooldown。

Fallback：

- MusicBrainz 归一化不足会进 quarantine 记录或被排除。
- Cover Art Archive 缺失时使用候选自带图片；仍没有则使用 `assets/placeholder.svg`。
- MusicBrainz rating 缺失时前端显示 metadata missing。
- Wikipedia overview 缺失时 Treatment Viewer 显示 overview empty。
- Discogs / ListenBrainz 失败时软降级；Last.fm / MusicBrainz 作为硬路径失败会让 build 失败并输出可读诊断。

## 小众度与避免过度主流

已有机制：

- DeepCut slot 使用 deepcut 模式，偏向更深 page，并对过高 rank 扣分。
- `_score()` 同时存在 tail boost，使较靠后的 rank 有机会进入候选。
- weighted sampling 不是纯 top 3，保留一定随机性。

不足：

- 没有显式 popularity 字段，最终 item 的 `popularity` 当前为 null。
- 没有使用 MusicBrainz rating votes、Last.fm playcount、Discogs have/want 等组合成“主流度”指标。
- 没有按地区、语言、年代、性别或场景做配额/软目标。

## 重复控制

- 同专辑重复：通过 MusicBrainz release-group id 或 fallback album key 控制，同日不能重复；历史 archive 会加载 album keys。
- 同艺人重复：优先 MusicBrainz artist MBID，缺失时用归一化 artist_credit；同日不能重复，7 天内不能重复。
- 同 tag / genre 过度重复：slot 内 theme key 不重复；历史 3 天 theme cooldown。
- 几天内不重复：artist 有 7 天硬冷却；theme 有 3 天硬冷却。专辑历史重复有 history index 能力，但当前主流程更强依赖同日 used_album_keys 和 recent ids 读取。

## 缺失与失败处理

| 情况 | 当前行为 |
|---|---|
| 无封面 | Cover Art Archive -> candidate image -> `assets/placeholder.svg` |
| 无 MusicBrainz rating | `musicbrainz.rating = null`，前端显示 missing |
| 无 Wikipedia overview | `overview = null`，前端显示 empty |
| 无 YouTube link | artist/title 缺失时为 null；否则只是搜索 URL |
| Discogs API 失败 | 返回空候选并记录 diagnostics，不让 build 单独失败 |
| ListenBrainz 失败 | 软失败，忽略该源 |
| Last.fm / MusicBrainz 失败 | 硬失败，build 返回失败诊断 |
| 候选不足 | 输出 tags tried、reject counts、top rejection reasons |

## 当前偏差风险

1. Last.fm tag charts、MusicBrainz、Wikipedia 对英语和欧美发行覆盖更完整，容易放大英语/欧美偏差。
2. Wikipedia overview 存在即会让 item 看起来更完整，可能间接偏向更知名专辑。
3. tag pool 虽有 k-pop、j-pop、mpb、ethio-jazz 等入口，但非英语地区不是显式覆盖目标。
4. 没有性别、地区、语言、年代分布的观测指标，无法判断长期是否偏某些群体。
5. DeepCut 的“小众”主要是 rank 和 page 近似值，不等价于真正的小众或被忽视。

## 最值得优化的 5 个点

1. 先增加离线审计输出：每次 build 写入候选数、来源占比、最终 9 张的年代/地区/语言可得字段、缺失字段统计。
2. 把 Discogs 从“候选源”扩展成“离线 enrichment 源”，补 label、country、format、styles、genres、master_id/release_id。
3. 定义明确的 smallness score：结合 Last.fm rank/playcount、MusicBrainz rating votes、Discogs rank 或 have/want 的安全子集，但不要接 marketplace 交易信息。
4. 增加多样性软目标：不要硬配额先行，先对最近 N 天 tag、年代、地区、女性/非欧美覆盖做报告。
5. 让 Headliner / Lineage / DeepCut 语义更稳定：如果 Lineage 确实代表年代脉络，应在 build 主流程显式按年份或 lineage score 选择，而不是仅按 score 排序后的第 2 张。

## 本轮未实现

本轮不改推荐算法，不新增外部运行时 API，不接入完整 Discogs enrichment provider。建议下一轮先做可观测性，再决定权重和多样性策略。
