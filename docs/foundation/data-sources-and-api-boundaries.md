# Data Sources And API Boundaries

Triangulum Daily 3 Albums 是离线生成的静态站。外部音乐服务是 build-time 输入，不是访客浏览器端的应用 API。

## Architecture Boundary

生成器在发布前运行。它获取候选、归一化 metadata、写入静态 JSON、复制 UI bundle，最终把站点输出到 `_build/public`。

发布后的站点由 GitHub Pages 托管。访客浏览器只读取 Pages 上的静态 JSON 和静态资源。访客端不应请求 Last.fm、MusicBrainz、Discogs、ListenBrainz、Wikipedia 或 Wikimedia API 作为应用数据源。

当前浏览器端自动 fetch 的项目数据是：

- `data/today.json`
- `data/index.json`
- `data/archive/{date}/{run_id}.json`
- `data/archive/{date}.json` fallback

如果生成出的公开 JSON 中含有绝对封面 URL，浏览器仍可能加载远端图片。这是外部资源加载风险，不是访客端音乐 API 接入。

当前架构不包含后端、数据库、登录、评论、用户系统、播放器服务、交易市场或访客端写入路径。GitHub Pages 不能在访客打开页面时写入新数据。

## Data Sources

### Last.fm

Last.fm 是必需的 build-time 候选来源。`run_dry_run()` 按 tag 和 page 调用 `tag.getTopAlbums`，候选字段包括 title、artist、可选 Last.fm MBID、rank 和 candidate image URL。

当前必需变量：

- `LASTFM_API_KEY`

Pages workflow 声明了 `LASTFM_SHARED_SECRET`，但当前 Python 配置加载和生成链路没有读取它。

### MusicBrainz

MusicBrainz 是核心识别和 metadata 来源。它用于把候选归一化到 release-group ID、把 release MBID 转成 release-group、做 fallback search，并获取 release-group details。

当前 MusicBrainz 可提供：

- release-group MBID
- artist MBIDs
- first release date / year
- primary type
- rating 和 votes count
- MusicBrainz tags
- URL relations，包括 Wikipedia URL relation

当前必需变量：

- `MB_USER_AGENT`

### Discogs

Discogs 当前是可选 build-time 候选来源。只有 `DISCOGS_TOKEN` 存在且 `candidates.discogs.enabled` 为 true 时才启用。

当前 Discogs search 调用 `database/search`，参数包括 `q=<tag>`、`type=master`、`format=album`、page 和 per_page。返回结果被压缩为 title、year、cover image、master ID、resource URL 和 rank。

当前最终公开 pick JSON 没有 `discogs` detail object，也没有 label、country、format、styles、genres、tracklist、price、marketplace、seller 或 sale-history 字段。

当前 Python 代码读取的 Discogs 变量：

- `DISCOGS_TOKEN`

workflow 中声明但没有完整进入 `Env` 模型的变量，不应写成当前生成器已使用的事实。

### ListenBrainz

ListenBrainz 是软性的可选候选路径。当前 dry-run 流程会尝试 sitewide release-group stats 和 metadata，按 tag 过滤，并在可用时提供 release-group MBID hint。失败会被忽略。

`.env.example` 包含 `LISTENBRAINZ_TOKEN`，Pages workflow 声明了 `LISTENBRAINZ_USER_TOKEN` 和 `LISTENBRAINZ_USERNAME`。但当前候选路径没有明确依赖这些值。

### Wikipedia / Wikimedia

Wikipedia 当前只在 build-time metadata enrichment 中使用。MusicBrainz release-group details 如果带有 Wikipedia URL relation，生成器会检查 `wikipedia.org/wiki/` URL，再请求 Wikipedia REST summary endpoint。

公开 JSON 可能保存 overview text、source、source URL 和 CC BY-SA license URL。没有 relation、请求失败或没有 extract 时，overview 为 `null`，UI 显示 empty overview fallback。

### Cover Images

构建阶段会先按 MusicBrainz release-group 请求 Cover Art Archive。缺失时可退回 Last.fm 或 Discogs 候选图片。仍没有可用封面时，最终 item 使用 `assets/placeholder.svg`。

当前 JSON 可以包含 Cover Art Archive、Last.fm、Wikimedia 等绝对封面 URL。UI 会接受绝对 URL，并把 `http://` 升级为 `https://`。这意味着访客浏览器可能请求远端图片。

远端封面加载是静态站完整性风险，不应误写成访客端 Last.fm、MusicBrainz、Discogs、ListenBrainz 或 Wikipedia API 请求。

## Public JSON Boundary

公开产物包括：

- `today.json`：当前 issue、当前 slot top-level picks、完整 3 slots、运行 metadata、warnings 和 diagnostics。
- archive JSON：按 date/run 保存的 issue payload。
- `index.json`：最近归档条目和 `archive_retention_days`。
- `meta.json`：Pages workflow 写入的 build metadata。
- `recommendation-observability.json`：build-time 推荐链路观测数据，包括候选计数、来源占比、拒绝原因、metadata coverage 和 enrichment success rate。

公开 JSON 不能包含：

- API key、token、secret 或 OAuth credential
- 真实 `.env` 值
- `.state/cache.sqlite` 内部 cache rows
- private logs
- SMTP credential
- R2 credential
- Discogs marketplace price、seller data、sale history 或 listing detail

外部 API 失败应以脱敏的 provider、stage、status、diagnostics 进入 build 日志或诊断，不应泄露 secret 或原始内部状态。

## Cache, Rate Limits, And Retries

外部 HTTP 请求走 `RequestBroker`。它把 cache 写到 `.state/cache.sqlite`，按 `config/endpoint_policies.yaml` 执行 host rate limit，写 adapter logs，缓存 negative responses，并按策略重试暂时性失败。

`.state/cache.sqlite` 是本地/CI build 辅助，不是公开产物，不能提交。

当前实现会在日志中 redacts 敏感 URL query 参数。Discogs 候选失败是软降级。ListenBrainz 失败会被忽略。Last.fm 和 MusicBrainz 是主 build 路径的必需外部来源。

## Environment Variables

以下整理来自 `.env.example` 和当前代码：

| Variable | Current status |
|---|---|
| `LASTFM_API_KEY` | Last.fm 候选获取必需。 |
| `MB_USER_AGENT` | MusicBrainz 请求必需，也用于 Wikipedia summary User-Agent。 |
| `DISCOGS_TOKEN` | 可选。存在且配置启用时使用 Discogs search candidates。 |
| `LISTENBRAINZ_TOKEN` | 出现在 `.env.example`，但当前 dry-run 候选代码没有明确要求它。 |
| `OPENAI_API_KEY` | 出现在 `.env.example`；当前生成链路未确认使用。 |
| `ALERT_SMTP_*` | 出现在 `.env.example`；当前 data/API 主路径不依赖它。 |
| `R2_*` | 出现在 `.env.example`；当前 Pages 静态站路径不需要访客端 R2 访问。 |
| `DAILY3ALBUMS_TZ` | 用于对齐 local/CI 环境时区；产品行为仍固定为 Asia/Shanghai/BJT。 |
| `DAILY3ALBUMS_HISTORY_SEED_DIR` | build-time 归档 seed 目录。 |
| `DAILY3ALBUMS_FIXTURES_DIR` / `DAILY3ALBUMS_FIXTURES_STRICT` | 测试和 fixture 控制。 |
| `DAILY3ALBUMS_PAGES_BASE_URL` | 已发布 Pages base URL 的 seed restore override；custom domain 稳定后可设为 `https://triangulumdaily.space/`。 |

更新文档时不要读取或暴露真实 `.env` 内容。

## Source basis

Verified from source:
- 环境变量加载：`daily3albums/config.py` 和 `.env.example`。
- Last.fm、MusicBrainz、Cover Art Archive、Discogs、ListenBrainz、Wikipedia 调用：`daily3albums/adapters.py`、`daily3albums/dry_run.py`、`daily3albums/cli.py`。
- cache、retry、redaction、rate limit：`daily3albums/request_broker.py` 和 `config/endpoint_policies.yaml`。
- 公开产物写入：`daily3albums/artifact_writer.py` 和 `scripts/self_check.py`。
- 推荐可观测性公开 JSON：`daily3albums/cli.py` 和 `scripts/recommendation_observability_summary.py`。
- 浏览器 fetch 路径：`ui/src/lib/data.ts`、`ui/src/lib/covers.ts`、`ui/src/lib/paths.ts`。
- workflow 环境变量声明：`.github/workflows/pages_daily.yml` 和 `.github/workflows/ci.yml`。

Inferred from current behavior:
- 远端封面图片是静态站资源依赖风险，但不是应用数据 API。
- Discogs 和 ListenBrainz 是软候选来源，不是必需识别来源。

Not implemented / Not confirmed:
- 完整 Discogs detail enrichment 当前未写入公开 pick JSON。
- 访客端请求 Last.fm、MusicBrainz、Discogs、ListenBrainz、Wikipedia 或 Wikimedia API 当前未实现。
- marketplace、price、seller、sale-history、用户账号、评论和播放器系统当前未实现。
