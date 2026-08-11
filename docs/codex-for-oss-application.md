# Codex for Open Source application

Prepared against the current OpenAI application form and the public repository state on 2026-08-11. This is application working copy, not a claim of acceptance or eligibility.

## Applicant and project

| Field | Answer |
| --- | --- |
| First name | Yang |
| Last name | Liu |
| Email associated with ChatGPT account | [photographer.qianqian@gmail.com](mailto:photographer.qianqian@gmail.com) |
| GitHub username | [qianqian5774](https://github.com/qianqian5774) |
| Public repository | [qianqian5774/triangulum-daily3albums](https://github.com/qianqian5774/triangulum-daily3albums) |
| Role | Primary maintainer |
| Interested in | Project API credits |
| OpenAI Organization ID | `org-GkQl0cVtSjqRBh1M6XULrCGc` |

## Free-text fields

Character counts include spaces and punctuation in the answer paragraph only. They are measured as Unicode code points; all three answers use ASCII characters, so the code-point and UTF-16 counts are identical.

### 1. Why does this repository qualify?

> Triangulum Daily is a public, non-fork music-discovery product that publishes nine albums daily to GitHub Pages. Its history has 100+ commits, 60 merged PRs, CI on pushes/PRs, and 270+ Actions runs; scheduled builds succeeded through August 10, 2026. Tests cover recommendation cooldowns/fallbacks, public JSON contracts, archive recovery, UI state, and releases. External adoption is still small; the evidence is active maintenance, a running system, and reusable maintainer practices.

**Character count:** 486 / 500

### 2. How will you use API credits for your project?

> Credits would support real maintainer work: triaging daily build failures; reviewing PRs and diffs; checking recommendation, archive, schedule, and public-JSON regressions; validating releases against tests, self-checks, build metrics, and release-SLA evidence; investigating provider, normalization, cooldown, and recovery failures; and keeping tests, runbooks, contracts, and small reusable maintenance scripts accurate. I would add automation only when it is reviewable and repository-backed.

**Character count:** 495 / 500

### 3. Anything else we should know?

> I am a solo primary maintainer from a content, music, research, and editing background, without a traditional software-engineering path. Triangulum began with a question: could a few albums a day be more interesting than an endless feed? Codex helps me learn by reading, testing, debugging, and deciding in a real system. I maintain its pipeline and am redesigning its record-like browsing and interactions. It is not a fork, tutorial, or UI clone; its direction grew inside this project.

**Character count:** 488 / 500

## Public evidence behind the answers

- The repository is public and is not marked as a fork. Its public Git history contains more than 100 commits.
- GitHub's pull-request API reported 63 PR records, 60 merged, with merged maintenance work through PR #65.
- GitHub Actions reported more than 270 workflow runs. Recent scheduled `Build and Deploy Pages (Daily)` runs, including the 2026-08-10 run, completed successfully.
- The live static contract at [`/data/today.json`](https://triangulumdaily.space/data/today.json) was serving the 2026-08-11 issue when this draft was prepared.
- CI, the daily production workflow, Python tests, UI unit tests, Playwright checks, static self-checks, recovery scripts, metrics, recommendation observability, and release-SLA reporting are present in the repository.
- The repository currently has limited external adoption. No claim about users, stars, forks, downloads, downstream dependents, or ecosystem reach is made in this application.

Relevant repository entry points:

- [CI workflow](../.github/workflows/ci.yml)
- [Daily Pages workflow](../.github/workflows/pages_daily.yml)
- [Recommendation and archive constraints](../daily3albums/constraints.py)
- [Static artifact writer](../daily3albums/artifact_writer.py)
- [Public JSON contract](../daily3albums/public_contract.py)
- [Published archive restore](../scripts/restore_static_archive_seed.py)
- [Static site self-check](../scripts/self_check.py)
- [Performance baseline](../PERFORMANCE.md)
- [Maintainer and agent operating constraints](../AGENTS.md)

## Official references

- [Codex for Open Source program](https://developers.openai.com/community/codex-for-oss)
- [Application form](https://openai.com/form/codex-for-oss/)
- [Program terms](https://learn.chatgpt.com/docs/codex-for-oss-terms)
