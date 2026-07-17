# R3 Public JSON Contract Audit

> 本文是 R3 完成时的点时契约审计证据，不替代源码、fixtures、测试及 `docs/foundation/` 作为当前状态权威。

## Scope

R3 统一以下公开静态 JSON 的 valid / invalid 边界：

- `data/today.json`；
- `data/archive/{date}/{run_id}.json`；
- `data/archive/{date}.json`；
- `data/index.json`。

Contract consumers 是 Python artifact writer/validator、published archive seed restore、`scripts/self_check.py`、TypeScript runtime parser，以及 archive/index loader integration。`data/recommendation-observability.json` 与 `data/meta.json` 不在本契约内，继续由现有专项 consumer 管理。

Canonical fixtures 位于 `tests/fixtures/public_contract/`。`manifest.json` 为每个 case 显式声明 `artifact_kind=today|archive|index`、`profile=current|legacy`、expected outcome 和稳定 error code；Python 与 TypeScript 直接读取同一份 manifest 和 payload/raw-byte 文件。

## Version authority

| Artifact/profile | Supported `output_schema_version` | Authority and behavior |
| --- | --- | --- |
| current today | `"1.0"` | Python writer 固定生成；Python/TypeScript current parser 严格接受 |
| current archive | `"1.0"` | 与 current today 共享 issue/pick/slot contract |
| current index | `"1.0"` | Python writer/validator、seed restore、self-check 与 TypeScript parser 严格接受 |
| legacy archive | `"1"` | 只允许 archive compatibility 与 seed restore；不允许 legacy today |

`output_schema_version` 缺失、类型不是 string 或值未知时明确拒绝。Unknown version 不按 current 尝试解析；版本 authority 不位于 `config.yaml`。R3 不引入 migration framework、跨语言代码生成或新的 runtime dependency。

## Required, optional and nullable matrix

### Current issue

| Path | Policy |
| --- | --- |
| `output_schema_version` | required string、不可 null、必须为 `"1.0"` |
| `date` | required `YYYY-MM-DD` string、不可 null |
| `run_id` | required non-empty string、不可 null |
| `theme_of_day` | required non-empty string、不可 null |
| `now_slot_id` | required integer enum `0|1|2`、不可 null |
| `slots` | required array，固定 3 项、按 `slot_id=0,1,2` 排序 |
| top-level `picks` | required array，固定 3 项，必须与 `slots[now_slot_id].picks` payload-equal |
| `run_at`, `slot`, `constraints`, `generation`, `warnings`, `diagnostics` and other writer metadata | additive/unknown fields；contract 不消费、不删除 |

### Current slot and pick

| Path | Policy |
| --- | --- |
| `slots[*].slot_id` | required integer，完整覆盖且按 `0,1,2` 排序 |
| `slots[*].window_label` | required non-empty string |
| `slots[*].theme` | required non-empty string |
| `slots[*].picks` | required array，固定 3 项 |
| `pick.slot` | required enum，按 `Headliner, Lineage, DeepCut` 完整覆盖 |
| `pick.rg_mbid` | current required non-empty MusicBrainz UUID |
| `pick.title` | required non-empty string |
| `pick.artist_credit` | required non-empty string |
| `pick.cover` | required object |
| `cover.has_cover` | current required boolean |
| `cover.optimized_cover_url` | required non-empty string；placeholder URL 合法 |
| `cover.cover_version`, `cover.original_cover_url` | optional，允许显式 null |
| `first_release_year` | optional number，允许显式 null |
| `tags` | optional array，允许显式 null；UI 将 missing/null 解释为无可展示 tags |
| `musicbrainz`, `links`, `evidence` | optional object，允许显式 null；存在时错误类型拒绝 |
| `reason` | optional string，允许显式 null |

Contract parser 不把 string/number、scalar/array 或非法 enum 相互 coercion。Unknown additive fields 可以忽略，但 required 字段、已知 optional 字段类型、结构、enum 和版本仍严格验证。

### Current index

| Path | Policy |
| --- | --- |
| `output_schema_version` | required string `"1.0"` |
| `items` | required array |
| `items[*].date` | required `YYYY-MM-DD` string |
| `items[*].run_id` | required non-empty string |
| `items[*].theme_of_day`, `items[*].run_at` | optional string，允许 null |
| `items[*].slot` | optional integer，允许 null |
| `archive_retention_days` | optional integer `>=1`，允许 null |

同一 index 不允许重复 `date/run_id`，也不允许同一 date 指向互相冲突的 run。Index entry 不新增 `path`；archive 路径只由 required `date + run_id` 推导。

## Legacy archive compatibility

Legacy profile 只适用于 `artifact_kind=archive` 且 `output_schema_version="1"`。它允许旧 archive 缺少 `slots` 和 RG MBID，但仍要求 date、run id、theme、非空 top-level picks，以及 pick 的合法 role、title、artist、cover URL。

缺少 RG MBID 时，legacy pick 必须保留可计算 stable album identity 的 title + artist，或显式非空 `album_key`。这保留 PR #55 history fallback，但不表示 current writer 可以省略 RG MBID。浏览器 current `today.json` 不进入 legacy parsing；`ui/public/data/today.json` 已迁移为 current 3×3 示例。

R3 不 force rewrite 已发布历史，不改变 archive retention/lifecycle，也不删除 history loader 的 fallback identity。

## Slot and 3×3 policy

Current issue 必须有 3 个有序 slots，每个 slot 正好 3 picks。每个 slot 的 pick role 顺序为 `Headliner, Lineage, DeepCut`。Top-level picks 精确定义为 `now_slot_id` 对应 slot 的 3 picks，不能来自其他 slot 或部分过滤结果。

任一 required pick、slot、role 或 3×3 结构错误会使整份 current document 失败。TypeScript parser 不再过滤坏 pick、坏 slot 或坏 index item 后继续渲染残缺页面。Optional metadata 缺失/null 仍保留合法 pick，并使用现有 UI fallback。

Today contract failure 继续进入现有 Signal Lost / BSOD 路径；archive/index contract failure 继续进入现有 Archive loading error。R3 不重写 UI 文案，也不统一 R7 的 missing/corrupt/timeout/provider/runtime taxonomy。

## Archive/index identity and byte policy

Canonical paths are:

```text
data/archive/{date}/{run_id}.json
data/archive/{date}.json
```

Index identity、推导路径和 archive payload 的 `date/run_id` 必须一致。两个 archive 路径同时存在时必须 byte-identical；即使 JSON 解析结果相同，只要空白、字段顺序或其他字节不同也拒绝。

当前 lifecycle 对单路径缺失的政策：

- seed restore 与 browser archive loader：run-specific 或 alias 任一存在且 contract/identity 合法时可继续；
- retained index archive 的 self-check integration：任一存在即可，两个存在时强制 byte-identical；
- current `today.json` 对应的 writer output/self-check：两条 archive 路径都必须存在，并与 today bytes 一致。

不存在任何路径时使用稳定 `ARCHIVE_MISSING` 类别；payload identity mismatch 使用 `ARCHIVE_IDENTITY_MISMATCH`；alias 字节不同使用 `ARCHIVE_ALIAS_BYTES_MISMATCH`。

## Stable contract error codes

R3 fixtures 覆盖并比较以下稳定类别：

- `MISSING_REQUIRED_FIELD`
- `NULL_REQUIRED_FIELD`
- `EMPTY_REQUIRED_FIELD`
- `WRONG_TYPE`
- `INVALID_DATE`
- `UNKNOWN_SCHEMA_VERSION`
- `UNSUPPORTED_PROFILE`
- `INVALID_SLOT_ID`
- `INVALID_SLOT_ENUM`
- `INVALID_SLOT_COVERAGE`
- `INVALID_3X3_STRUCTURE`
- `TOP_LEVEL_PICKS_MISMATCH`
- `INVALID_RELEASE_GROUP_MBID`
- `MISSING_STABLE_ALBUM_IDENTITY`
- `DUPLICATE_ARCHIVE_IDENTITY`
- `ARCHIVE_MISSING`
- `ARCHIVE_IDENTITY_MISMATCH`
- `ARCHIVE_ALIAS_BYTES_MISMATCH`
- `INVALID_JSON`

User-facing runtime copy remains unchanged; codes are validator/test boundaries, not a new R7 taxonomy.

## Cross-consumer fixture matrix

`valid_legacy` 表示只有 manifest 明确标记的 legacy archive profile 合法。`N/A` 表示 consumer 职责不适用于该 artifact，不以 skip 掩盖同一职责内的差异。

| fixture | Python writer/validator | seed restore | self-check | TypeScript parser/loader | expected |
| --- | --- | --- | --- | --- | --- |
| current_today_valid | valid | N/A | valid | valid | valid |
| current_archive_valid | valid | valid | valid | valid | valid |
| current_index_valid | valid | valid | valid | valid | valid |
| placeholder_cover_valid | valid | N/A | valid | valid | valid |
| optional_metadata_missing_valid | valid | N/A | valid | valid | valid |
| optional_metadata_null_valid | valid | N/A | valid | valid | valid |
| unknown_additive_field_valid | valid | N/A | valid | valid | valid |
| legacy_archive_missing_rg_valid | valid_legacy | valid_legacy | valid_legacy | valid_legacy | valid_legacy |
| missing_required_field | invalid | N/A | invalid | invalid | invalid |
| required_wrong_type | invalid | N/A | invalid | invalid | invalid |
| required_null | invalid | N/A | invalid | invalid | invalid |
| invalid_slot_enum | invalid | N/A | invalid | invalid | invalid |
| duplicate_slot_id | invalid | N/A | invalid | invalid | invalid |
| missing_slot_id | invalid | N/A | invalid | invalid | invalid |
| slots_count_not_three | invalid | N/A | invalid | invalid | invalid |
| slot_picks_count_not_three | invalid | N/A | invalid | invalid | invalid |
| top_level_picks_mismatch | invalid | N/A | invalid | invalid | invalid |
| current_missing_rg_mbid | invalid | N/A | invalid | invalid | invalid |
| invalid_rg_mbid | invalid | N/A | invalid | invalid | invalid |
| unknown_schema_version | invalid | N/A | invalid | invalid | invalid |
| schema_version_wrong_type | invalid | N/A | invalid | invalid | invalid |
| schema_version_missing | invalid | N/A | invalid | invalid | invalid |
| legacy_today_not_supported | invalid | N/A | invalid | invalid | invalid |
| invalid_calendar_date | invalid | N/A | invalid | invalid | invalid |
| optional_metadata_wrong_type | invalid | N/A | invalid | invalid | invalid |
| index_missing_date | invalid | invalid | invalid | invalid | invalid |
| index_missing_run_id | invalid | invalid | invalid | invalid | invalid |
| duplicate_archive_identity | invalid | invalid | invalid | invalid | invalid |
| cover_structure_invalid | invalid | N/A | invalid | invalid | invalid |
| archive_pair_identical | N/A | valid | valid | valid | valid |
| archive_pair_run_only | N/A | valid | valid | valid | valid |
| index_archive_missing | N/A | invalid | invalid | invalid | invalid |
| index_archive_identity_mismatch | N/A | invalid | invalid | invalid | invalid |
| archive_pair_semantic_same_bytes_different | N/A | invalid | invalid | invalid | invalid |
| archive_pair_payload_different | N/A | invalid | invalid | invalid | invalid |
| archive_json_unparseable | N/A | invalid | invalid | invalid | invalid |

Python matrix tests exercise artifact helpers, seed restore adapters and self-check adapters against the manifest. TypeScript matrix tests exercise current/legacy parsers and mock the real archive loader with the same raw bytes. Writer regression additionally verifies that a current production-style payload is not mutated, all three issue files use the expected bytes, alias files are identical, and index entries do not gain `path`.

## Behavior invariance and non-goals

R3 changes only invalid-payload rejection and developer fixture alignment. For current valid writer input it preserves JSON fields, picks, order, role labels, archive bytes and index shape. It does not change recommendation eligibility, normalization, candidate requests/budgets, cooldown, fallback, scoring, temperature, sampling, observability or legal-data UI presentation.

Explicit non-goals:

- no `recommendation-observability.json` or `meta.json` unification;
- no public field expansion or index `path`;
- no recommendation or TD-02B policy;
- no archive retention/lifecycle change or force rewrite;
- no UI visual/error-page redesign;
- no R7 runtime error taxonomy;
- no backend service, JSON Schema framework, migration engine or runtime dependency;
- no automatic transition to R4.

## Validation evidence

The completed R3 change passed:

- full Python tests, including the shared fixture matrix and production-style fixture self-check;
- full UI unit tests, including the same manifest and archive raw-byte loader cases;
- production UI build;
- a full fixed-toolchain `daily3albums build` against real providers with the repository development archive seed as read-only history input;
- `scripts/self_check.py` against that generated static site;
- `git diff --check`.

Natural Pages execution is not a merge prerequisite. After merge, R3 production acceptance remains pending until a natural Pages run on a `main` SHA containing R3 confirms writer, self-check, deploy, current/legacy archive reads and historical byte protection. That acceptance remains separate from R1/TD-02 shadow sample accounting.

## Production acceptance closure

`R3 production acceptance: completed`.

The scheduled Pages run `29538888750` executed on `main` commit
`f295482777de1d2007f4ba3b1edcab4b54b6a37f` and completed its build,
self-check, Pages artifact upload and deploy jobs successfully. The retained
Pages artifact was downloaded and inspected directly before expiry:

- `today.json` uses current `output_schema_version="1.0"`, date
  `2026-07-17`, run id `2026-07-17_slots_4da1da`, three ordered slots and
  exactly three picks per slot;
- `index.json` contains seven unique retained dates, declares retention `7`,
  and points the current date at the same run id;
- the current run-specific archive and date alias have the same SHA-256
  (`F79AC850CF5802F26D0C12AA878947F2E38BE587C33F376DC232C9AB73DC05F9`);
- `scripts/self_check.py` passes against the downloaded production artifact;
- the actual TypeScript `parseTodayIssue`, `parseArchiveIndex` and
  `parseArchiveIssue` functions parse the downloaded production payloads
  without compatibility fallback;
- the production payload is current contract throughout and does not depend
  on legacy `today.json` parsing.

The natural workflow also ran the full Python and UI contract suites on the
production runner, retaining legacy archive fixture coverage without widening
legacy compatibility to Today. A successful writer run after loading seven
validated historical dates, followed by self-check and deploy, exercises the
existing retained-history and alias-byte protection gates. This acceptance
does not change the R3 contract or claim that every invalid/legacy fixture was
encountered in deployed production data.
