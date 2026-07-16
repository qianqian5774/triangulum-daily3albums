# R7B Python / Build-time Error Semantics Audit

## Scope conclusion

R7B is an internal error-semantics refactor for Python generation, archive seed/history loading, provider adapters, enrichment, and workflow summary scripts. The implementation does not change recommendation selection, request policy, retry/cache/rate limiting, public JSON contracts, normalization shadow, UI code, or workflow schedules.

The pre-implementation audit found no dependency or ownership conflict that required stopping the task. R3 remains the public-contract validation authority; R1/R6 remain the normalization authority; `RequestBroker` remains the transport, cache, retry, rate-limit, and URL-redaction authority.

## Previously unclassified paths

Before R7B, several different conditions converged on `None`, `[]`, a generic `RuntimeError`, or free-form exception text:

- archive seed/history missing, empty, corrupt, contract-invalid, and identity-invalid states;
- Discogs and ListenBrainz legitimate empty responses versus transport failures;
- MusicBrainz detail, Cover Art Archive, and Wikipedia missing/invalid/timeout states;
- candidate-cover and placeholder fallbacks;
- observability artifact missing, legacy, empty, corrupt, invalid, and render failures;
- GitHub summary output failures;
- published archive reuse.

Those representations made it difficult to assert failure meaning without depending on exception wording. R7B adds small typed result/error objects at the existing ownership boundaries and keeps compatibility wrappers where callers still consume the old value shape.

## Stable taxonomy

`OutcomeCode` is the shared vocabulary. `RuntimeOutcome` carries only safe diagnostic fields: code, provider, stage, resource kind, optional HTTP status, cached state, and fallback name. `ProviderResult[T]` pairs an existing return value with its outcome.

| Code | Real trigger | Primary owner |
|---|---|---|
| `success` | A provider or history load returns usable data | Adapter/history loader |
| `missing` | A required local seed/index/archive resource or enrichment identifier/relation is absent | Seed/history/enrichment |
| `legitimate_empty` | A valid provider response or valid history/index contains no relevant entries; empty-history acceptance still requires the existing explicit flag | Adapter/seed/history/summary |
| `provider_not_found` | Provider HTTP status is 404 or 410, including negative-cache results surfaced by `RequestBroker` | RequestBroker mapping, adapter interpretation |
| `request_failed` | A known transport failure occurs without timeout or a provider application error is returned | RequestBroker/adapter |
| `timeout` | The transport cause is a timeout, including URL and socket timeout paths in seed restore | RequestBroker/seed restore |
| `corrupt` | JSON cannot be decoded, response shape cannot be parsed, or an expected JSON resource is not JSON | RequestBroker/adapter/summary/seed/history |
| `invalid_schema` | R3 rejects a public-contract payload for a non-identity rule, or a workflow artifact has an unsupported typed structure | R3 mapping/summary |
| `identity_mismatch` | R3 reports archive date/run identity mismatch | R3 mapping |
| `archive_alias_mismatch` | R3 reports non-byte-identical run-specific and date-alias archives | R3 mapping |
| `fallback_used` | A secondary archive provider succeeds, or cover resolution uses candidate image/placeholder after CAA is unavailable | Orchestration |
| `published_archive_reused` | The archive writer preserves an already published date and replaces the generated run with the published archive | Archive writer orchestration |
| `disabled` | The optional provider path is explicitly disabled | Candidate orchestration |
| `not_configured` | A required provider credential/config value is absent | Candidate orchestration |
| `rate_limited` | HTTP 429 or the Last.fm application rate-limit status is returned | RequestBroker/adapter |
| `unavailable` | A dependent optional input/output is unavailable without being corrupt, such as absent modern fields in a compatible legacy artifact or an unwritable output | Orchestration/summary |
| `recovery_exhausted` | Every configured archive seed provider fails | Seed orchestration |
| `render_failed` | A validated observability payload cannot be rendered | Summary renderer |

Unknown programming exceptions are not converted into soft provider outcomes. Adapter/orchestration wrappers catch only the known `RequestBroker` and provider error types. The summary renderer retains a bounded catch because its explicit responsibility is to classify rendering failure; it does not expose raw exception text.

## Ownership and policy

### Archive seed and history

- `public_contract.py` still decides whether index/archive payloads are valid, which profile applies, and whether archive identity and aliases agree.
- Seed/history code maps `PublicContractError.code` to runtime outcomes and adds safe source/resource/date/run context.
- External history remains validated before candidate generation.
- Empty history still fails unless the existing explicit allow-empty path is used.
- Seed restore still stages before promotion, preserves an existing seed when a provider/staging attempt fails, and retains the date-count baseline guard.
- A failed primary provider remains eligible for the existing fallback sequence; all-provider failure remains hard.

### Provider and enrichment paths

- `RequestBroker` still owns retries, cache behavior, rate limiting, HTTP status handling, and URL query redaction. Its typed errors no longer embed raw provider/parser exception messages.
- Discogs and ListenBrainz adapters distinguish legitimate empty, not found, request failure, timeout, and corrupt response. Candidate orchestration still treats these providers as soft and continues the primary funnel.
- MusicBrainz detail, Wikipedia overview, and Cover Art Archive return typed enrichment results. Enrichment remains post-selection and cannot change pick eligibility or trigger resampling.
- Cover fallback order remains CAA, candidate image, placeholder. Missing overview/rating values remain `null` through the existing writer.

### Workflow summaries

- Recommendation Observability summary distinguishes missing artifact, legacy-compatible unavailable sections, legitimate empty display data, corrupt JSON, invalid structure, render failure, and unavailable summary output.
- Build Metrics and Release SLA diagnostics use stable codes and safe resource/cause-type fields for relevant read/write failures.
- Existing workflow propagation remains unchanged: optional summary/metrics steps keep their prior soft/hard behavior as configured by their callers and workflow `continue-on-error` rules.

## Redaction boundary

Diagnostics do not include Authorization headers, credential objects, cache rows, raw provider bodies, raw exception representations, or complete sensitive URL queries. `RequestBroker.redact_url` remains the URL authority and is reused by archive seed summaries. Tests assert that API-key/token query values and raw exception messages do not enter error strings, while stable codes remain identical across different raw exception messages.

## Behavior-preservation evidence

- The deterministic Golden check still matches the existing checked-in fixture expectation.
- The build integration fixture executes `cmd_build`, validates the generated static site through `scripts/self_check.py`, and verifies deterministic picks/history behavior.
- The compatibility fixture compares provider call arguments, request counts, and every generated public artifact byte-for-byte.
- Existing public-contract fixtures continue to be validated by R3 consumers; R7B only maps their stable contract codes to runtime categories.
- No `today.json`, archive, index, recommendation-observability, or normalization-shadow schema field was added or removed.
- Soft provider failure tests preserve the Last.fm-derived final funnel; enrichment fallback tests preserve selected picks and cover/overview/rating behavior.
- Published archive reuse still follows the archive writer's existing immutability decision and only gains an internal safe outcome for diagnostics.

## Current limits

- Deterministic fixtures and mocks cover the error matrix; they do not establish conclusions about future provider availability or every provider-specific error body.
- Safe summaries intentionally omit raw response and exception detail. Root-cause investigation may still require provider status, stage, request statistics, and separately protected runtime logs.
- Natural production observation and the TD-02B/R6 sample gate remain separate work. R7B does not manufacture or advance those samples.
