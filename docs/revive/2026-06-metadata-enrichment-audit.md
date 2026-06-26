# 2026-06 Metadata Enrichment Audit

审计日期：2026-06-26
范围：Discogs / Wikipedia / MusicBrainz 当前使用情况、缺口和后续接入计划。没有读取或打印真实 `.env`，没有新增完整 enrichment provider。

## 总览结论

当前 metadata 链路以 MusicBrainz 为核心：MusicBrainz 负责 release-group 归一化、artist MBIDs、first release date、primary type、rating、tags 和 Wikipedia URL relation；Wikipedia 只在离线 build 阶段按 MusicBrainz relation 拉 page summary；Discogs 当前已经有 token 配置、adapter 和候选源接线，但没有把 Discogs detail 字段写入最终公开 JSON。

本轮不建议直接实现完整 Discogs enrichment。更安全的下一步是：先把 Discogs 保持为 daily build 的离线 enrichment，添加缓存、限速、User-Agent 和失败软降级，再逐步把 label/country/format/styles/genres/master_id/release_id 写入 JSON。

## 配置与 Secret 位置

- `.env.example` 包含 `DISCOGS_TOKEN=`，没有真实 token。
- `.github/workflows/pages_daily.yml` 已声明 `DISCOGS_TOKEN`、`DISCOGS_CONSUMER_KEY`、`DISCOGS_CONSUMER_SECRET`、`DISCOGS_USER_AGENT` 等环境变量。
- `daily3albums/config.py` 当前只把 `DISCOGS_TOKEN` 读入 `Env.discogs_token`；consumer key/secret/user-agent 还没有进入 `Env`。
- `config/config.yaml` 中 `candidates.discogs.enabled: true`，并配置 page start、max pages、per_page。

## 当前 Discogs Adapter / Probe / Client

已有代码：

- `daily3albums/adapters.py::discogs_database_search()` 调用 `https://api.discogs.com/database/search`。
- 请求参数当前为 `q=<tag>`、`type=master`、`format=album`、page、per_page。
- 返回模型 `DiscogsSearchItem` 只保留 `title`、`year`、`cover_image`、`master_id`、`resource_url`、`rank`。
- 失败处理是软降级：`RequestFailed` 或其他异常会返回空列表，并写入 diagnostics。

没有看到单独的 Discogs detail enrichment provider，也没有 release/master detail fetch。

## Discogs 是否被 Build Pipeline 使用

被使用，但只作为候选来源：

- `daily3albums/dry_run.py::run_dry_run()` 在 `env.discogs_token and discogs_enabled` 时调用 Discogs search。
- Discogs 结果会转成 Candidate，加入 `sources.add("discogs")` 和 `source_ranks["discogs"]`。
- `_score()` 会给多来源候选加分，因此 Discogs 可影响候选排序。
- `daily3albums/cli.py::cmd_build()` 会把 Discogs diagnostics 写入 slot progress / attempts meta。

没有被使用的部分：

- 最终 `PickItem` 没有 `discogs` 字段。
- `resource_url`、`master_id` 没有写进公开 JSON。
- label、country、format、styles、genres、tracklist、release_id 没有进入数据模型。

卡点判断：当前只实现了 search 级别接线，缺少“根据最终 MusicBrainz release-group / candidate identity 选定 Discogs master/release，再拉 detail 并缓存”的稳定映射层。

## Discogs 适合优先补的字段

适合补入离线 build JSON：

- `label`
- `country`
- `format`
- `styles`
- `genres`
- `tracklist` / `track_count`
- `master_id` / `release_id`
- `discogs_url`

这些字段能帮助解释唱片语境、地区、厂牌和风格，不会把产品导向交易平台。

## Discogs 不建议优先补的字段

不建议接入：

- marketplace price
- have / want 的交易导向解释
- sale history
- seller / listing / marketplace URL
- 任何会让项目看起来像唱片交易推荐的信息

如未来使用 have/want 作为小众度信号，也应只离线聚合成粗粒度、不可反查交易的数值，并在文档中说明限制。

## MusicBrainz Rating 缺失时如何显示

- `musicbrainz_get_release_group_details()` 用 `inc=ratings+tags+url-rels` 拉 rating。
- `_pick_to_issue_item()` 中 rating 缺失时写 `musicbrainz.rating = null`。
- `SlotCard` 和 `TreatmentViewerOverlay` 中 `formatMbRating()` 返回 null 后显示 `treatment.metadata.missing`。

当前 fallback 是清晰的“缺失”文案，不会伪造评分。

## Wikipedia Overview 缺失时如何 Fallback

- MusicBrainz details 中通过 URL relation 提取 Wikipedia URL。
- `_wikipedia_overview_from_url()` 只接受 `wikipedia.org/wiki/` URL，再请求 `/api/rest_v1/page/summary/<title>`。
- 请求失败、无 URL、无 extract 时返回 null。
- 前端 Treatment Viewer 中 overview 为空时显示 `treatment.overview.empty`。

当前不会因为 Wikipedia 缺失导致 build 整体失败。

## Wikipedia / CC BY-SA Attribution

当前公开 JSON 会保存：

- overview text
- `source: "wikipedia"`
- `source_url`
- `license_url: https://creativecommons.org/licenses/by-sa/3.0/`

前端 Treatment Viewer 在有 overview 和 source URL 时显示继续阅读链接，并显示 CC BY-SA license 链接。这个 attribution 对 Treatment Viewer 的可见文本基本够用，但还可以在后续加强：

- 在项目 About 文案中补一句 Wikipedia summary attribution 说明。
- 如果 overview 被复用到 Share Card 或其他导出物，需要把 source/license 一并显示或避免导出 overview。

## 前端运行时外部请求

本轮没有新增访客侧 Discogs、Wikimedia 或 MusicBrainz API 请求。

当前前端 `ui/src/lib/data.ts` 只 fetch 本站静态 JSON：`data/today.json`、`data/index.json`、`data/archive/...json`。不过 `ui/src/lib/covers.ts` 允许 absolute cover URL，因此浏览器可能直接加载 Cover Art Archive / Last.fm 等外部图片资源。这不是新增 API 请求，但仍是静态站完整性风险：外部图片失败会影响封面显示。

建议后续把最终公开 JSON 的 cover URL 尽量指向本地构建产物或明确记录 remote image fallback 风险。

## 后续最小接入方案

1. 只在 daily build 中请求 Discogs / Wikimedia，不在访客浏览器端请求这些 API。
2. 所有请求走 `RequestBroker`，必须缓存、限速、重试有边界。
3. Discogs 请求必须设置明确 User-Agent；如果继续只用 token header，应确认 Discogs policy 是否接受当前 header 组合。
4. 先做 detail adapter，不直接改推荐算法：输入最终 9 张的候选 identity，输出可选 `discogs` metadata。
5. 失败软降级：Discogs detail 失败只记录 diagnostics 和 missing 字段，不让 build 整体失败。
6. 保持敏感信息隔离：不打印 token，不把 token 写入 JSON、日志、文档或测试 fixture。
7. 增加测试：无 token、401/429、cached negative、bad JSON、detail miss、rate cap hit。
8. 增加报告字段：每次 build 输出 Discogs attempted/matched/enriched/failed counts。

## 最小 JSON 形状建议

建议后续在 pick 下添加可选字段：

```json
{
  "discogs": {
    "master_id": 123,
    "release_id": 456,
    "url": "https://www.discogs.com/master/123",
    "labels": ["..."],
    "country": "...",
    "formats": ["Album", "LP"],
    "genres": ["Electronic"],
    "styles": ["Ambient"],
    "track_count": 8
  }
}
```

保持字段可选。前端展示缺失时只显示“missing”，不要把缺失解释成质量差。

## 本轮未实现

本轮没有新增完整 Discogs enrichment provider，没有改变 MusicBrainz/Wikipedia provider 行为，没有新增访客运行时 API 请求。
