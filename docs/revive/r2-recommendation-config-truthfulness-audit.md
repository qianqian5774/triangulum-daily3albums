# R2 Recommendation Config Truthfulness Audit

本文是 R2 完成时的点时审计证据，不替代源码、配置、测试及 `docs/foundation/` 作为当前状态权威。后续实现发生变化时，应重新核对 consumer 和测试，不能把本表当作永久 schema 或 compatibility policy。

## Scope and method

本次逐项核对 `config/config.yaml`、`daily3albums/config.py`、`daily3albums/cli.py`、`daily3albums/dry_run.py`、artifact writer、validation scripts、GitHub workflows 和相关 tests。分类含义：

- `active`：存在真实生产 consumer；如只影响 observability，会明确标记 `active (shadow-only)`。
- `reserved`：有明确未来 owner，但当前没有运行效果。
- `deprecated`：当前配置表面不再推荐使用，parser 仅保留 compatibility fallback 或 warning。
- `removed`：没有生产 consumer、兼容义务或明确未来 owner，已从正式配置表面删除。

R2 不定义 public schema compatibility，不实施 normalization threshold，不改变推荐或请求行为。

## Authority matrix

| config path | status | current consumer | actual runtime effect | current authority | compatibility obligation | R2 action | evidence/tests |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | removed | none | none | Recommendation Observability schema is hard-coded by `cli._new_recommendation_observability()` and checked by `scripts/self_check.py` | none; config loader never read it | removed from YAML | `cli.py`; `self_check.py`; config ignored-field invariance test |
| `output_schema_version` | removed | none | none | public issue writer currently emits `"1.0"`; validators/parsers own contract behavior | none; config loader never read it | removed from YAML; R3 owns future contract policy | `cli.py`; `artifact_writer.py`; UI parser tests; ignored-field invariance test |
| `timezone` | removed | none after R2 | none; changing YAML never changed product time | Python/UI BJT implementations and workflow `TZ`/SLA arguments fix `Asia/Shanghai` | none; old key is harmlessly ignored | removed from YAML, unused `AppConfig.timezone` projection and dead `DAILY3ALBUMS_TZ` workflow env | `_beijing_now()`; `ui/src/lib/bjt.ts`; workflow; ignored-field invariance test |
| `random_seed_strategy` | removed | none | none | date/slot/theme seed strings and SHA-256/random usage are code-owned | none | removed from YAML | `_hash_index()`, `sample_three()`; deterministic build invariance test |
| `decade_mode` | deprecated | `load_config()` compatibility projection; build warning only when legacy decade keys exist | no recommendation constraint or selection effect | no active decade policy | keep reading old configs and warning; default remains `off` | removed from current YAML, compatibility parser retained | `test_config_decade_mode.py`; deprecated compatibility tests |
| legacy `decade_theme`, `day_decade`, `decade_axis` | deprecated | `load_config().ignored_legacy_decade_keys` | warning only | no active decade policy | old config diagnostics | not present in current YAML; detection retained | `config.py`; `test_config_decade_mode.py` |
| legacy `build.min_in_decade`, `build.max_unknown_year` | deprecated | `load_config().ignored_legacy_decade_keys` | warning only | no active decade policy | old config diagnostics | not present in current YAML; detection retained | `config.py`; `test_config_decade_mode.py` |
| `history.archive_retention_days` | active | `load_config()` → `write_artifacts()` | caps archive index to the latest N published dates | YAML canonical key | default 7 if absent | retained and clarified | `artifact_writer.py`; `test_artifact_writer.py`; config truthfulness tests |
| `history.dedupe_same_rg_days` | active | `load_config()` → `CooldownPolicy.album_days` | normal album release-group cooldown window | YAML canonical key | default 7 if absent | retained | `cmd_build()`; cooldown integration tests |
| `history.dedupe_same_artist_days` | active | `load_config()` → `CooldownPolicy.artist_days` | normal artist cooldown window | YAML canonical key | default 7 if absent | retained | `cmd_build()`; cooldown integration tests |
| theme cooldown config | removed / absent | none | none | `constraints.THEME_COOLDOWN_DAYS = 3` | none in YAML | no fake YAML knob added | `constraints.py`; history/cooldown tests |
| `normalizer.min_confidence` | active (shadow-only) | `cmd_dry_run()` / `cmd_build()` → `run_dry_run()` shadow references | computes hypothetical low-confidence rejection only | config reference `0.72`; CLI reference is separate `0.80` | key remains for TD-02A observation | comment corrected; retained | normalization shadow tests; build invariance test |
| `normalizer.ambiguity_gap` | active (shadow-only) | same path as above | computes hypothetical ambiguity rejection only | config reference `0.08`; CLI reference is separate `0.06` | key remains for TD-02A observation | comment corrected; retained | normalization shadow tests; build invariance test |
| `normalizer.hard_ambiguity_policy` | reserved | none | none; does not quarantine, drop or filter | future TD-02B policy work | explicit future owner TD-02B | retained with `reserved/not enforced` comment | repository search; current config assertion |
| `normalizer.top_k` | removed | none | none | MusicBrainz search limit comes from CLI `--mb-search-limit` | none | removed from YAML | repository search; ignored-field invariance test |
| `normalizer.weights.{title,artist,year,type,evidence}` | removed | none | none | adapter matching formula is code-owned | none | removed from YAML | `adapters.py`; ignored-field invariance test |
| `normalizer.mb_max_queries_per_candidate` | active | `load_config()` → `run_dry_run()` → MusicBrainz matcher | caps text-search strategies per candidate | YAML canonical key | default 3 if absent | retained | config tests; dry-run diagnostics tests |
| `normalizer.mb_max_candidates_per_slot` | active | `load_config()` → `run_dry_run()` | caps normalization candidates per slot attempt | YAML canonical key | default 120 if absent | retained | `test_dry_run_prefilter.py`; config tests |
| `normalizer.mb_time_budget_s_per_slot` | active | `load_config()` → `run_dry_run()` | caps per-attempt normalization wall time | YAML canonical key | default 90 seconds if absent | retained | `test_dry_run_prefilter.py`; config tests |
| `global_exclusions.allow_primary_types` | removed | none | none | `allow_types` is the actual primary-type authority | none | removed from YAML | `_type_flags_from_cfg()`; ignored-field invariance test |
| `global_exclusions.exclude_secondary_types` | removed | none | none; secondary type list was not enforced | no active secondary-type YAML policy | none | removed from YAML | `_primary_type_allowed()`; ignored-field invariance test |
| `allow_types.album` | active | `_type_flags_from_cfg()` → `_primary_type_allowed()` | allows/rejects primary type Album | YAML key | default true | retained | type-filter tests / build integration |
| `allow_types.ep` | active | same | allows/rejects primary type EP | YAML key | default false when absent | retained | `_primary_type_allowed()`; config assertions |
| `allow_types.compilation` | active | same | applies only when MusicBrainz primary type string is Compilation; does not inspect secondary types | YAML key | default false | retained with matrix clarification | `_primary_type_allowed()` |
| `allow_types.live` | active | same | applies only when primary type string is Live | YAML key | default false | retained | `_primary_type_allowed()` |
| `allow_types.single` | active | same | allows/rejects primary type Single | YAML key | default false | retained | `_primary_type_allowed()` |
| `themes.rotation` | removed | none | none | no themes rotation production path | none | removed from YAML | `_get_tag_pool()` repository search; ignored-field invariance test |
| `themes.items[*].name` | removed | none | none | `tag_pool` supplies actual tags | none | removed from YAML | repository search |
| `themes.items[*].seed_tags` | removed | none | none | `tag_pool` supplies actual tags | none | removed from YAML | repository search |
| `themes.items[*].adjacent_tags` | removed | none | none | no adjacent-tag expansion path | none | removed from YAML | repository search |
| `tag_pool[*]` | active | `_get_tag_pool()` → slot tag attempt order | defines actual candidate tag pool; date/slot hash determines starting point | YAML list; code default only if missing/empty | default pool retained for missing config | contents unchanged | tag selection and build invariance tests |
| `slots.*.require_cover` | removed | none | none; cover lookup/fallback occurs after selection | cover adapter and placeholder fallback code | none | removed from YAML | `cmd_build()` enrichment path; ignored-field invariance test |
| `slots.*.weights.*` | removed | none | none | score formula and role assignment are code-owned | none | removed from YAML | `_score()`; `cmd_build()` role assignment; build invariance test |
| `candidates.lastfm.lastfm_page_start` | active | `load_config()` → `run_dry_run()` | canonical first Last.fm page | YAML canonical key | fallback to deprecated `page_start`, then 1 | retained | config precedence tests; request ledger invariance |
| `candidates.lastfm.lastfm_max_pages` | active | `load_config()` → `run_dry_run()` | canonical Last.fm pages per normal attempt | YAML canonical key | fallback to deprecated `build.lastfm_max_pages`, then 6 | retained | config precedence tests; request ledger invariance |
| `candidates.lastfm.page_start` | deprecated | `load_config()` fallback only | same as canonical key only when canonical missing | canonical `lastfm_page_start` | legacy config compatibility | absent from current YAML; parser fallback retained | deprecated alias tests |
| `build.lastfm_max_pages` | deprecated | `load_config()` fallback only | same as canonical key only when canonical missing | canonical `candidates.lastfm.lastfm_max_pages` | legacy config compatibility | removed from current YAML; parser fallback retained | deprecated alias tests |
| `candidates.lastfm.per_page` | removed | none | none; adapter call is fixed at 50 by current Last.fm helper path | adapter/code | none | removed from YAML | repository search; ignored-field invariance test |
| `candidates.lastfm.pages_per_call` | removed | none | none | current page loop is code-owned | none | removed from YAML | `dry_run.py`; ignored-field invariance test |
| `candidates.lastfm.deepcut_min_page` | removed | none | none | deterministic deepcut offset is code-owned | none | removed from YAML | `dry_run.py`; ignored-field invariance test |
| `candidates.discogs.enabled` | active | `load_config()` → `run_dry_run()` | enables/disables Discogs candidate source | YAML canonical key | default true | retained | Discogs resilience tests; config tests |
| `candidates.discogs.discogs_page_start` | active | `load_config()` → `run_dry_run()` | canonical Discogs requested page | YAML canonical key | fallback to deprecated `page_start`, then 1 | retained | config precedence tests |
| `candidates.discogs.discogs_max_pages` | active | `load_config()` → `run_dry_run()` | canonical Discogs page cap | YAML canonical key | fallback to deprecated `max_pages`, then 3 | retained | config precedence tests; Discogs tests |
| `candidates.discogs.discogs_per_page` | active | `load_config()` → `run_dry_run()` | canonical Discogs result count, clamped 1–100 | YAML canonical key | fallback to deprecated `per_page`, then 100 | retained | config precedence tests; Discogs tests |
| `candidates.discogs.page_start` | deprecated | `load_config()` fallback only | canonical-equivalent only when canonical missing | `discogs_page_start` | legacy config compatibility | absent from current YAML; parser fallback retained | deprecated alias tests |
| `candidates.discogs.max_pages` | deprecated | `load_config()` fallback only | canonical-equivalent only when canonical missing | `discogs_max_pages` | legacy config compatibility | absent from current YAML; parser fallback retained | deprecated alias tests |
| `candidates.discogs.per_page` | deprecated | `load_config()` fallback only | canonical-equivalent only when canonical missing | `discogs_per_page` | legacy config compatibility | removed from current YAML; parser fallback retained | deprecated alias tests |
| `candidates.discogs.deepcut_min_page` | removed | none | none | deterministic Discogs page offset is code-owned | none | removed from YAML | `dry_run.py`; ignored-field invariance test |
| `candidates.listenbrainz.count` | removed | none | none | count is derived from requested `n` and clamped in `run_dry_run()` | code | none | removed from YAML | `dry_run.py`; ignored-field invariance test |
| `candidates.listenbrainz.deepcut_min_offset` | removed | none | none | offset is deterministically derived from seed/deepcut mode | code | none | removed from YAML | `dry_run.py`; ignored-field invariance test |
| `scoring.coarse_top_n_per_slot` | active | `load_config()` → `run_dry_run(prefilter_topn=...)` | canonical light-prefilter size | YAML canonical key | fallback to deprecated `mb_prefilter_topn`, then 120 | retained | prefilter tests; config precedence tests |
| `scoring.mb_prefilter_topn` | deprecated | `load_config()` fallback only | canonical-equivalent only when canonical missing | `coarse_top_n_per_slot` | legacy config compatibility | removed from current YAML; fallback retained | deprecated alias tests |
| `scoring.coarse_top_n` | removed | none | none | canonical `coarse_top_n_per_slot` | none | not accepted as alias | repository search; removed-field tests |
| `scoring.multi_source_bonus` | removed | none | none | `_score()` hard-coded formula | none | removed from YAML | `_score()`; ignored-field/build invariance tests |
| `scoring.head_keep_max_rank` | removed | none | none | `_score()` hard-coded rank shape | none | removed from YAML | `_score()`; ignored-field invariance test |
| `scoring.tail_boost_start_rank` | removed | none | none | `_score()` hard-coded rank shape | none | removed from YAML | `_score()`; ignored-field invariance test |
| `scoring.deepcut_head_penalty_rank` | removed | none | none | `_score()` hard-coded deepcut penalty | none | removed from YAML | `_score()`; ignored-field invariance test |
| `scoring.temperature_by_slot.*` | removed | none | none | `cmd_build()` uses code constants 9.0/10.0/14.0 | none | removed from YAML | `cmd_build()`; exact artifact/request invariance test |
| `scoring.mb_normalize_budget_cap` | removed | none | none | normalizer candidate/time keys are actual budgets | none | removed from YAML | repository search; ignored-field invariance test |
| `build.max_tag_tries_per_slot` | active | `load_config()` → slot attempt slicing | caps attempted tags per slot | YAML canonical key | default 8 | retained | cooldown/build integration tests; config assertions |
| `build.ui_build_timeout_s` | active | `load_config()` → UI subprocess timeout | bounds production UI build step | YAML canonical key | default 300, clamped ≥1 | retained | `test_cli_ui_timeout.py`; config tests |
| CLI `--min-confidence` / `--ambiguity-gap` | active (shadow-only, non-config) | CLI parser → `run_dry_run()` | supplies separate CLI hypothetical reference `0.80/0.06`; no rejection | CLI defaults | command compatibility | unchanged | normalization shadow tests; exact build invariance test |

## Precedence and compatibility conclusions

Canonical keys always win over retained aliases. Deprecated aliases are read only when their canonical key is absent:

1. `candidates.lastfm.lastfm_page_start` → fallback `candidates.lastfm.page_start`.
2. `candidates.lastfm.lastfm_max_pages` → fallback `build.lastfm_max_pages`.
3. Discogs `discogs_*` keys → fallback `page_start`, `max_pages`, `per_page`.
4. `scoring.coarse_top_n_per_slot` → fallback `scoring.mb_prefilter_topn`.

Removed fields can still appear in an old YAML object without changing the typed active projection because the loader ignores unknown keys. R2 does not promise that all removed fields will remain accepted forever; that parser/schema policy belongs to R3.

## Behavior invariance evidence

The fixed R2 before/after build fixture runs the same candidate/history input twice: once with the pre-R2 dead configuration surface injected and once with the truthfully reduced config. It asserts byte-identical public output trees plus identical candidate-call kwargs and request ledger. This covers final picks/order/roles, attempted and selected tags, candidate/rejection/fallback diagnostics, normalization shadow rows/top-2 values/hypothetical results, Recommendation Observability and public artifacts.

Additional coverage verifies canonical precedence, deprecated alias fallback, active typed values, removed-field non-consumption, deterministic output, request invariance, existing cooldown stages, normalization shadow behavior and backward-compatible artifact rendering.

## Explicit non-goals

- No threshold is enforced.
- No score, temperature, tag, cooldown, candidate cap, query, retry, fallback or role behavior changes.
- No unknown-version handling, schema dispatch or public parser compatibility policy is defined here.
- R3 and TD-02B are not started by this audit.
