# R6 — TD-02B Formal Normalization Policy Audit

Status: implementation and local deterministic acceptance complete; CI/merge and the next natural generated production run remain pending.

## Scope audit

The original R6 instruction had one material evidence conflict: it required deterministic per-slot replay for three natural generated samples, while the first two Pages artifacts had expired and their candidate-level rows were no longer recoverable. GitHub Actions still retained aggregate summaries, but those summaries cannot reconstruct candidate identities, runner identities, scores, or exact selection order.

The approved minimal revision is therefore:

- use the persistent aggregate Actions summaries for runs `29288927379` and `29372212022`;
- perform complete candidate-row policy replay for retained run `29454605202`;
- use a sanitized fixture for critical identity/ambiguity scenarios that the old shadow schema did not retain;
- add a new candidate-level, sanitized artifact with 30-day retention;
- do not recover expired artifacts;
- complete production acceptance with the first natural generated run after merge.

No other material conflict was found. R6 does not change recommendation scoring, temperatures, source merging, cooldowns, tag rotation, public pick schema, retention, schedule, provider retry/backoff, UI, or the Stage 0–3 fallback order. R8 is not entered.

## Formal policy

`config.normalizer` is the sole production authority. Policy version: `td02b-v1`.

| Setting | Value |
|---|---:|
| Strict minimum confidence | `0.82` |
| Hard confidence floor | `0.78` |
| Ambiguity gap | `0.08` |
| Title identity floor | `0.60` |
| Artist identity floor | `0.50` |
| Distinct-runner ambiguity action | `hard_reject` |

Policy tiers:

- `strict`: verified direct release-group entity plus title/artist identity, verified release-to-release-group conversion, verified external release-group hint, or safe strict text match at/above the strict threshold;
- `borderline`: safe text match between hard and strict confidence floors, a safe cleaned-loose/title-only query, or a low-gap runner proven to represent the same cleaned work/artist;
- `hard_reject`: identity mismatch, confidence below the hard floor, unsupported path/strategy, or low-gap ambiguity against a distinct or unproven runner.

Selection order:

1. apply the normalization policy before existing recommendation filters;
2. apply existing type, same-day, album cooldown, and artist cooldown filters to the strict tier;
3. when fewer than three strict candidates remain, admit only the highest-ranked eligible borderline candidates needed to reach three;
4. never admit a hard reject into Stage 0, Stage 1 expansion, Stage 2 artist relaxation, or Stage 3 bounded album relaxation;
5. retain the existing single-page Stage 1 expansion and all existing request budgets.

The legacy CLI options `--min-confidence` and `--ambiguity-gap` remain parse-compatible but are ignored with an explicit warning. They are not a second runtime authority.

## Evidence matrix

All three runs were natural scheduled runs with `generation_mode=generated`, `candidate_funnel_rerun=true`, `final_picks_source=candidate_funnel`, Stage 0 selection, no candidate-scope expansion, and zero additional requests.

| Run | Themes | Evidence level | CLI-shadow rejects | Config-shadow rejects | Final picks shadow-impacted |
|---|---|---|---:|---:|---:|
| `29288927379` | hypnagogic pop / gabber / happy hardcore | persistent aggregate summary | 4 | 3 | 1 |
| `29372212022` | goa trance / bedroom pop / emo | persistent aggregate summary | 8 | 5 | 2 |
| `29454605202` | lo-fi house / progressive rock / no wave | complete 54-row replay plus sanitized critical fixture | 6 | 1 | 1 |

Across the three summaries, the old CLI reference (`0.80 / 0.06`) rejected 18 rows (13 low confidence, 5 ambiguous); the old config shadow (`0.72 / 0.08`) rejected 9 rows (3 low confidence, 6 ambiguous). Each reference would have affected three final picks in total. These are historical shadow comparisons, not the formal policy result.

Run `29454605202` complete replay:

- all 54 retained candidate rows are replayed;
- slot 0 gap-zero candidate `29ff1628-8523-4a82-ab6a-823e792174d4` becomes `hard_reject` under the approved distinct-runner critical fixture;
- the remaining eligible slot 0 set is exactly `4748ad7f-7973-4e98-bd76-a09de7885fd5`, `ac6330e4-da62-4c2b-b3b0-c2266bb4bdd2`, and `baaa6aae-78b8-4a40-800c-475a4ed60701`;
- slot 1 and slot 2 previous final picks remain inside their strict eligible pools;
- replay remains Stage 0 with zero additional requests.

The fixture records its limitation explicitly: the old artifact retained confidence/gap/path/eligibility/final flags, but not title/artist similarity, runner identity, score, or artist keys. It marks old matcher identity checks as prevalidated and fixture-enriches only the approved gap-zero distinct-runner critical case.

## Observability and artifact retention

Generated recommendation observability now reports:

- `normalization_policy_enforced=true`;
- policy version and `config.normalizer` authority;
- candidate tier and reason;
- identity similarities and runner equivalence fields;
- strict, borderline, and hard-reject counts;
- borderline admission/final-pick impact and strict-pool shortage;
- score and artist keys needed for future deterministic replay.

Reused published archives remain explicitly ineligible for production normalization samples because their candidate funnel is not rerun.

The workflow creates `.state/normalization-evidence.json` through an allowlist-only sanitizer and uploads it as an independent `actions/upload-artifact` artifact with `retention-days: 30`. It excludes raw provider responses, query strings, titles, artist display names, image URLs, secrets, caches, and logs. The Pages artifact and deployed public schema are unchanged.

The recommendation summary renderer continues to support the old `observed_not_enforced` shadow schema and renders the new enforced tier summary when present.

## Acceptance evidence

Completed locally:

- full Python suite: passed;
- UI unit suite: 16 files / 104 tests passed;
- production UI build: passed;
- deterministic replay: 54 / 54 candidate rows evaluated;
- fixture build/integration coverage: passed, including no hard-reject admission and borderline-only-on-shortage behavior;
- sanitizer allowlist coverage: passed;
- legacy shadow summary compatibility: passed.

Real network-backed static generation was attempted with the repository CLI. The run encountered repeated MusicBrainz `ConnectTimeout` provider failures under the existing request/error semantics; this is recorded separately from code acceptance and does not justify changing retries, budgets, or tools in R6. A successful full generation/self-check remains required through CI and the next natural production run.

## Remaining gates

Before R6 is production-accepted:

1. open a Draft PR and pass repository CI;
2. mark ready, squash-merge, and sync `main`;
3. update the formal roadmap to the approved three-sample evidence model and mark R6 code complete / production acceptance pending;
4. snapshot and update the five local Foundation documents without staging or committing them;
5. verify the next natural generated run is not a reused archive, reports `normalization_policy_enforced=true`, produces nine picks, passes self-check/deploy, and uploads the 30-day normalization evidence artifact;
6. record that production acceptance, then stop without entering R8.
