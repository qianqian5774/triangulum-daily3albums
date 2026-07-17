# R4 Schedule, Retention, Environment And Runtime Contract Audit

> 本文是 R4 合并前能够确认的点时审计证据，不替代源码、配置、fixtures、测试、workflow 及 `docs/foundation/` 作为当前状态权威。

## Scope

R4 收口以下跨层事实源，不改变产品时间、archive retention 天数、部署频率、推荐结果或公开 JSON contract：

- BJT schedule、每日 3 slots、每 slot 3 picks 与 Share Card 版本；
- archive retention 在 config、writer、restore、index 与 UI fallback 之间的一致性；
- build-time provider credentials、内部控制变量、测试/审计变量和废弃声明的分类；
- Node 22 本地验证与 Node 24 CI/Pages 之间的 supported runtime contract。

Canonical schedule fixture 位于 `tests/fixtures/product_schedule.json`。Python 和 TypeScript 各自保留实现；fixture 只提供共享 contract evidence，不引入生成器、跨语言代码生成或新的 runtime dependency。

## Schedule contract

产品时区固定为 `Asia/Shanghai`。它不是 YAML 或 visitor-side 可切换项。

| BJT interval | UI state | Writer slot | Share Card version |
| --- | --- | --- | --- |
| 00:00:00–07:59:59 | `OFFLINE` | slot 0 prepared for the first unlock | none available |
| 08:00:00–12:29:59 | `SLOT0` | 0 | `0800`, 3 albums |
| 12:30:00–15:59:59 | `SLOT1` | 1 | `1230`, 6 albums |
| 16:00:00–23:59:59 | `SLOT2` | 2 | `1600`, 9 albums |

UI 的 Offline State 与 writer 的 pre-08:00 slot 0 preparation 是不同职责：生成器在清晨准备第一时段 payload，浏览器在 08:00 前仍不展示该 slot。该差异由同一 fixture 分别声明 `ui_state/ui_slot_id` 与 `writer_slot_id`，不是 consumer drift。

Fixture 同时固定：

- 3 slots per day；
- 3 picks per slot；
- Python JSON window labels `08:00-12:29`、`12:30-15:59`、`16:00-23:59`；
- UI display labels 使用对应 en dash 形式；
- Share Card IDs `0800/1230/1600` 及 3/6/9 album counts。

Python tests 直接读取 fixture 验证 `_beijing_slot()`、`_slot_label()`、`_slot_window_start()` 和 current 3×3 fixture。TypeScript tests 读取同一文件验证 `BJT_TIMEZONE`、`PRODUCT_SCHEDULE`、所有左右边界和 `SHARE_CARD_VERSIONS`。

Python product clock 优先使用 `ZoneInfo("Asia/Shanghai")`。当宿主缺少 IANA tzdata 时，fallback 现在使用命名为 `Asia/Shanghai` 的固定 UTC+8 aware datetime，不再退回无时区的 host-local datetime。这不改变 BJT 产品时间；它消除 host timezone 对产品日期/slot 的意外 authority。

## Archive retention authority

Archive retention 保持 7 个有数据的唯一日期，不是保证连续 7 个自然日。

| Layer | Authority / behavior |
| --- | --- |
| Config | `config/config.yaml` 的 `history.archive_retention_days: 7` 是 production writer 输入 authority。 |
| Config loader | `AppConfig.archive_retention_days` 读取并最小限制为 1。 |
| Writer | `write_daily_artifacts()` 接收 config value，index 只保留最近 7 个唯一日期，并写出 `archive_retention_days=7`；模块 default 7 只服务直接调用 fallback。 |
| Restore script | `DEFAULT_ARCHIVE_RETENTION_DAYS=7`；CLI `--max-days` 默认 7。 |
| Pages workflow | restore 显式传入 `--max-days 7`。 |
| Public index | current index fixture 与 production-style build 均写出 7。 |
| UI | `getRecentArchiveEntries()` 优先读取 index value；字段缺失时 fallback 仍为 7，并按 date 去重。 |

`tests/test_r4_contract.py` 对上述 tracked authorities 做一致性检查；UI test 单独固定 fallback。R4 不把 retention 迁入新配置系统，不修改 archive lifecycle、published archive lock、date alias byte policy 或 legacy archive compatibility。

## Environment variable classification

### Active production/build inputs

| Variable | Status | Consumer |
| --- | --- | --- |
| `LASTFM_API_KEY` | required secret | Last.fm candidate requests |
| `MB_USER_AGENT` | required secret/value | MusicBrainz and Wikipedia build-time requests |
| `DISCOGS_TOKEN` | optional secret | Discogs candidate source when config enables it |
| `DAILY3ALBUMS_PAGES_BASE_URL` | optional repository variable/local override | published archive seed provider |
| `DAILY3ALBUMS_HISTORY_SEED_DIR` | active workflow-internal path | validated archive seed loaded before candidate selection |
| `DAILY3ALBUMS_FORCE_ARCHIVE_REWRITE` | active manual safety escape | requires exact confirmation value; absent from normal Pages path |
| `TZ` | workflow process environment alignment | CI/Pages set `Asia/Shanghai`; Python/UI product clock remains the product authority |

`.env.example` and the Pages job-level environment now declare only the active provider inputs applicable to those surfaces. Existing machines or repository settings may still contain removed names; unknown environment variables are ignored and do not create a compatibility failure.

### Active test, diagnostics and runner inputs

- `DAILY3ALBUMS_FIXTURES_DIR` / `DAILY3ALBUMS_FIXTURES_STRICT`：deterministic HTTP fixtures；
- `DAILY3ALBUMS_BUILD_METRICS_DIR`：build metrics output override；
- `RUNNER_TEMP`、`GITHUB_RUN_ID`、`GITHUB_RUN_ATTEMPT`、`GITHUB_STEP_SUMMARY`：GitHub runner metrics/summary context；
- `GITHUB_SHA`、`GITHUB_REPOSITORY` and other GitHub-provided metadata：build identity/provider defaults；
- `PLAYWRIGHT_WEB_ROOT`、`PLAYWRIGHT_CHROMIUM_CHANNEL`、`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`：local browser validation controls；
- `PERF_BASE_URL`、`PERF_CPU_RATE`、`PERF_SETTLE_MS`、`PERF_FPS_SAMPLE_MS`、`PERF_BROWSER_CHANNEL`、`PERF_SCENARIOS`、`PERF_DATE`：independent performance audit controls。

Workflow step-local names such as `INPUT_N`, `INPUT_TOPK`, `INPUT_TAG`, `ARCHIVE_RECOVERY_CACHE_KEY`, `RELEASE_SLA_STARTED_AT`, `DEPLOY_OUTCOME` and `EVENT_NAME` are shell adapter inputs, not application configuration or reusable secrets.

### Deprecated or removed declarations

The following names had no current consumer and were removed from `.env.example`, the `Env` dataclass or the Pages job declaration as applicable:

- `ALERT_SMTP_*` and workflow `SMTP_*`；
- `R2_*`；
- `LISTENBRAINZ_TOKEN`、`LISTENBRAINZ_USER_TOKEN`、`LISTENBRAINZ_USERNAME`；
- `OPENAI_API_KEY`；
- `LASTFM_SHARED_SECRET`；
- `DISCOGS_CONSUMER_KEY`、`DISCOGS_CONSUMER_SECRET`、`DISCOGS_USER_AGENT` and Discogs OAuth endpoint variables。

ListenBrainz remains an unauthenticated soft build-time candidate path in current code; removing unused token/username declarations does not disable it. SMTP/R2/OpenAI capabilities remain unimplemented and are not restored by R4.

## Node and runtime support contract

`ui/package.json` and the root package entry in `ui/package-lock.json` declare:

```text
node >=22 <25
```

This means Node majors 22, 23 and 24 are supported for the tracked UI toolchain. The current machine continues to use the fixed Node 22.13.0/npm path from `AGENTS.local.md`; CI and Pages continue to use Node 24. `tests/test_r4_contract.py` verifies that tracked workflow Node majors remain inside the declared range.

The `engines` range is a compatibility contract, not an instruction to install or switch Node. R4 does not modify local NVM state, absolute toolchain paths or `AGENTS.local.md`. Python remains governed independently by `pyproject.toml` with `requires-python >=3.11` and CI/Pages Python 3.11.

## Behavior invariance evidence

R4 does not change schedule values, retention value, recommendation configuration, candidate requests/budgets, scoring, sampling, cooldown, fallback, public JSON fields or UI presentation.

The only runtime behavior correction is the Python clock fallback on hosts without IANA tzdata: it now preserves the already-authoritative UTC+8 product time instead of inheriting host-local time.

Evidence available before merge:

- deterministic golden check passed with the existing recommendation fixture；
- full Python tests passed, including R3 public contract and R4 cross-layer contract tests；
- full UI unit tests passed on fixed local Node 22；
- production UI build passed；
- a production-style full build completed with the existing provider/request path；
- `scripts/self_check.py` passed against the generated site；
- generated `today.json` remained complete 3×3, index retention remained 7, and today/run-specific/date-alias bytes had the same SHA-256；
- source diff contains no Album Card/CSS/layout/recommendation/public-contract changes。

An additional local `browser:smoke` probe started successfully after pointing `PLAYWRIGHT_WEB_ROOT` at the task's `._build/public`. Desktop passed. Its three mobile cases reported animated HUD marquee descendants outside the viewport while the measured page-level `overflowDelta` remained 0; R4 does not change the relevant DOM/CSS/animation, so this pre-existing probe sensitivity is recorded but not "fixed" by changing visual behavior in R4.

## Local tests and PR CI

Confirmed locally before PR:

- Python: 183 passed, 23 skipped；
- UI unit: 81 passed；
- production UI build: passed；
- deterministic golden check: passed；
- production-style full build: passed；
- static-site self-check: passed。

PR CI status at this audit revision: pending. CI green remains the Ready/merge gate; the final CI and merge result belong in the external post-merge R4 completion report, not a post-merge rewrite of this document.

## Explicit non-goals

- no product schedule, retention-day or deploy-frequency change；
- no public JSON schema or archive compatibility change；
- no recommendation, TD-02B, request-budget or observability policy change；
- no backend, database or visitor-side external music API；
- no UI redesign, CSS cleanup, Album Card/Viewer/Archive rewrite or performance work；
- no local Node install, removal, switch or `AGENTS.local.md` update；
- no SMTP, R2, OpenAI or authenticated ListenBrainz implementation；
- no automatic transition to R6, TD-02B or later stages。

## Production acceptance

`R4 production acceptance: completed`.

Scheduled Pages run `29538888750` provides the independent production
evidence:

- event `schedule` ran on a `main` commit containing R4;
- the job environment used `TZ=Asia/Shanghai`, Python `3.11.15` and Node
  `24.18.0`, all inside the declared project contracts;
- the custom-domain archive provider restored and validated seven dates and
  fourteen run-specific/alias files before candidate generation;
- the generated current artifact kept `archive_retention_days=7`, seven
  unique index dates, complete 3×3 output and matching current archive aliases;
- UI build, Python/UI tests, static generation, self-check, Pages artifact
  upload and deploy all succeeded;
- release SLA summary classified the natural run as `on_time`, with build
  start and deploy finish expressed in Asia/Shanghai relative to the 08:00
  target.

The deployed UI was then read in a browser at BJT 16:05. It reported the
`16:00–23:59` product window, the current BJT date, and the expected third
slot content. No host-timezone or runtime-contract drift was observed. This
closes R4 only; it does not substitute for R3, R5 or normalization acceptance.
