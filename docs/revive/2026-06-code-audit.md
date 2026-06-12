# 2026-06 代码审计：长期无人值守运行风险

审计方式：只做静态代码审计；没有做功能开发、重构、构建、安装依赖、外部探测或提交。阅读范围包括 `README.md`、`AGENTS.md`、`docs/runbook.md`、`docs/revive/2026-06-local-baseline.txt`、`.github/workflows/pages_daily.yml`、`pyproject.toml`、`config/`、`daily3albums/`、`scripts/`、`ui/src/`、`ui/package.json` 和 `ui/package-lock.json`。

Python 兼容性结论：当前 shell 是 Python 3.14.0，GitHub Actions 固定 Python 3.11。`daily3albums/`、`scripts/`、`doctor/` 下 Python 文件用 3.11 语法规则静态解析通过，没有明显“本地 3.14 能跑、CI 3.11 语法直接失败”的问题。剩余风险主要是依赖和运行行为没有做 3.14 矩阵覆盖。

## P0：必须马上修，否则会影响稳定运行

### P0-1：页面打开后会持续高频请求 `today.json`

- 问题：`TodayRoute` 看起来会在生产页面每 500ms 重新拉取一次 `data/today.json`，而不是只在首次加载、焦点恢复、可见性变化、slot 边界或重试时请求。
- 证据：
  - `ui/src/routes/Today.tsx:141-149` 每 500ms 更新 `bjtNow`。
  - `ui/src/routes/Today.tsx:299-340` 让 `storeLastGood` 依赖 `bjtNow.parts`，进而让 `loadIssue` 依赖 `storeLastGood`。
  - `ui/src/routes/Today.tsx:347-350` 的“Load exactly once” effect 实际会在 `loadIssue` 身份变化时重跑。
  - `ui/src/lib/data.ts:4-15` 每次 fetch 都使用 `{ cache: "no-store" }`。
  - `docs/revive/2026-06-local-baseline.txt:845-875` 在短时间本地预览里出现连续 `GET /data/today.json`。
- 影响：一个闲置页面每天可产生约 172,800 次 JSON 请求。它会破坏“静态站点轻量自治”的设计，给 CDN/浏览器缓存造成不必要压力，并掩盖真正的边界刷新逻辑是否可靠。
- 复现：从 `_build/public` 启动静态服务器，打开 `/` 后不操作，观察 server log 是否持续出现 `GET /data/today.json`。
- 修法：让 `storeLastGood` 保持稳定，不依赖 `bjtNow.parts`。可在 callback 内部用 `getBjtNowParts(loadDebugTime())` 计算 fetched-at，或存普通 wall-clock 时间。然后补一个回归检查，证明 idle 页面不会持续 refetch。
- 验证：修复后重复本地 `http.server` 预览；排除 React dev/StrictMode 影响后，生产页面空闲时不应每 500ms 请求 `today.json`。

## P1：建议近期修

### P1-1：`debug_time` 文档和 HashRouter 参数读取疑似不一致

- 问题：README 示例和本地基线使用 `/?debug_time=...`，但前端使用 `HashRouter`，并从 React Router 的 `location.search` 读取参数。HashRouter 下更可靠的形式通常是 `/#/?debug_time=...`。
- 证据：
  - `ui/src/main.tsx:7-12` 使用 `HashRouter`。
  - `ui/src/App.tsx:65-75` 只从 router location search 读 `debug_time`。
  - `README.md:80-107` 文档写的是 `/?debug_time=...`。
  - `docs/revive/2026-06-local-baseline.txt:876-914` 只证明这些地址能打开，没有证明模拟时间确实生效。
- 影响：跨 slot、跨日和 OFFLINE 边界 QA 可能是假阳性。页面返回 200 不代表 debug time 被前端状态机采用。
- 修法：读取 `window.location.search` 和 router `location.search` 两处，或把文档和测试统一改为 hash query 形式。补一个集成测试覆盖文档给出的 URL。
- 验证：分别打开 05:59 和 06:00 的 debug URL，断言 UI 状态发生预期变化，而不只是页面能打开。

### P1-2：`ui/public/data` seed 数据会进入生产输出和 archive index

- 问题：Vite 会把 `ui/public/data` 复制到 `ui/dist/data`；`daily3albums build` 再把 `ui/dist` 复制到 `_build/public`；随后 `write_daily_artifacts` 读取已有 seed `data/index.json` 并追加当天 run。当前 `_build/public/data/index.json` 已包含 `dev-seed-*` 条目。
- 证据：
  - `ui/public/data/index.json` 包含 `dev-seed-20260119` 和 `dev-seed-20260118`。
  - `ui/dist/data/` 构建后含相同 seed JSON。
  - `daily3albums/cli.py:1294-1299` 复制 `web/`、复制 `ui/dist`、再写生成产物。
  - `daily3albums/artifact_writer.py:96-132` 保留旧 index items 并追加当前 run。
  - 当前 `_build/public/data/index.json` 含 2026-06-12 生成条目和 dev seed 条目。
- 影响：公开 archive 可能展示开发/演示数据。这正是 `README.md:42` 警告的 `_build/public`、`ui/dist`、`ui/public/data` 混淆。
- 修法：生产构建不要把 seed JSON 放在 `ui/public/data`；或者让生成器在写产物前清理/接管 `_build/public/data`。如果 Vite dev 仍需要示例数据，移到 dev-only 路径。
- 验证：构建后 `data/index.json` 只包含真实生成 run；`_build/public` 内不应出现 `dev-seed` run_id。

### P1-3：Doctor 通过目前会给出过强信心

- 问题：`daily3albums doctor` 只打印 `DOCTOR`、timezone、`config=OK`、`env=OK`，没有验证必要 secret，也没有执行 probe。`doctor/run_doctor.py` 的 render QA 是占位实现，只写 `today.desktop.json`，没有用 Playwright/local server 跑 today/archive/detail 的 desktop/mobile 审计。
- 证据：
  - `daily3albums/cli.py:38-45`
  - `doctor/run_doctor.py:172-215`
  - `doctor/run_doctor.py:269`
  - `AGENTS.md:190-260` 要求真实 Playwright render QA、network/layout/data/a11y 证据和 fingerprint。
- 影响：“doctor 通过”目前不能作为端到端无人值守证据。它会漏掉渲染错误、陈旧数据、运行时外部资源问题，以及 P0 的 `today.json` 高频请求。
- 修法：要么停止把 `daily3albums doctor` 当作端到端 doctor；要么把 `python -m doctor.run_doctor` 补到 `AGENTS.md` 合约要求。
- 验证：doctor 应产出 today/archive/detail x desktop/mobile 的全部 JSON 审计文件，并能对真实 render/data/network 异常报 issue。

### P1-4：`self_check` 有价值，但覆盖不够无人值守

- 问题：`scripts/self_check.py` 检查文件存在、JSON 结构、archive 存在和明显绝对路径；但不检查 `today.json.date` 是否等于当前北京时间日期，不渲染 UI，不检查 dev seed 污染，不检查运行时外部图片/data 失败。
- 证据：
  - `scripts/self_check.py:33-62`
  - `scripts/self_check.py:125-159`
- 影响：CI 可能在“结构合法但日期错误或 archive 污染”的情况下通过。
- 修法：先加小而确定的静态检查：BJT 日期对齐、生成 index 中无 `dev-seed`、严格 3 slots x 3 picks、seed `today.json` 没有穿透。完整视觉/网络/a11y 放到 doctor。
- 验证：人为放入错误日期 `today.json` 或 `dev-seed` index 条目，确认 self_check 失败。

### P1-5：外部 API 失败处理对“坏部署”安全，但连续运行韧性偏薄

- 问题：请求代理已有串行限速、退避、重试和 negative cache。Discogs 是软源，失败会降级为空列表。但 Last.fm 和 MusicBrainz 仍是硬依赖，部分应用层错误会以普通 `RuntimeError` 逃逸，而不是受控的 per-tag 失败。
- 证据：
  - `daily3albums/request_broker.py:371-388`, `512-615`
  - `config/endpoint_policies.yaml`
  - `daily3albums/adapters.py:127-129`
  - `daily3albums/dry_run.py:333-336`, `363-365`
  - `daily3albums/cli.py:1014-1026`, `1160-1177`
- 影响：Last.fm 应用层错误、缺 secret、坏 JSON、候选池耗尽都可能让当天构建失败。GitHub Pages 通常会保留上次部署，这比部署坏数据安全，但当前没有明确的 last-known-good 策略或用户可见 stale 说明。
- 修法：继续把 Last.fm/MusicBrainz 当硬门槛，但让失败受控、可报告。考虑定义“保留上次部署”或“复用 last-known-good 并展示 stale banner”的显式策略。
- 验证：用 fixture 模拟 Last.fm JSON error 和 MusicBrainz timeout，确认 CI 失败信息清晰且产出可操作证据。

### P1-6：Actions `.state` cache 可能长期增长

- 问题：workflow 缓存 `.state`，只清理旧 `*.jsonl`，不清理 `.state/cache.sqlite`。SQLite 过期行只有在再次访问同一 cache key 时才会删除。
- 证据：
  - `.github/workflows/pages_daily.yml:104-117`
  - `daily3albums/request_broker.py:141-157`
  - `daily3albums/request_broker.py:393-426`
- 影响：长期 tag 轮转和大量唯一 URL 会让 Actions cache 逐步变大，影响恢复速度和可靠性。
- 修法：在保存 cache 前加一个小维护步骤：删除过期 rows，必要时 `VACUUM`。
- 验证：维护前后检查 SQLite row count 和文件大小。

### P1-7：workflow_dispatch 手动参数通过 `eval` 执行

- 问题：`workflow_dispatch` 的 `tag` 被拼到 shell 字符串，再通过 `eval` 执行。
- 证据：`.github/workflows/pages_daily.yml:126-138`
- 影响：定时任务不受影响，但有手动触发权限的协作者可让 tag 字符串变成 shell 执行语义。这是可避免的运维风险。
- 修法：用 shell array 组装命令，移除 `eval`。
- 验证：用包含空格和引号的 tag 手动触发，确认它作为一个 CLI 参数传入，而不是执行 shell 语法。

## P2：可选优化

### P2-1：把 Python 3.14 本地环境和 CI 3.11 的边界写清楚

- 现状：`pyproject.toml` 要求 `>=3.11`，Ruff target 是 `py311`，Actions 固定 3.11。静态 3.11 语法解析通过。
- 风险：本地 3.14 成功不证明依赖 wheel 和行为在 3.11 上一致；CI 3.11 成功也不证明未来 3.14 长期可用。
- 建议：生产 CI 继续固定 3.11。等 P0/P1 修完后，再加非阻断 3.14 兼容 job。

### P2-2：本地和 CI 构建链路基本一致，但 UI 会构建两次

- 现状：README 本地流程和 Actions 都先跑 UI 构建，然后 `daily3albums build` 内部又跑一次 `npm --prefix ui run build`。
- 风险：主要是耗时和噪音，不是正确性。双构建会让“独立 UI build 是否必要”不清晰。
- 建议：后续再决定由 `daily3albums build` 完全拥有 UI build，或给 CI 增加未来的 `--skip-ui-build`。不要在 P0/P1 前改。

### P2-3：`timezone` 配置被硬编码 Asia/Shanghai 部分绕过

- 现状：`config/config.yaml` 声明 `timezone: "Asia/Shanghai"`，Actions 也设置 `TZ` / `DAILY3ALBUMS_TZ`；但构建日期计算使用 `_beijing_now()`，硬编码 `ZoneInfo("Asia/Shanghai")`。
- 风险：产品定义就是北京时间时风险较低。只有当维护者以为 `config.timezone` 可自由切换时才会困惑。
- 建议：要么文档说明这是产品级固定行为，要么把日期计算统一走已加载配置。

### P2-4：`require_cover: true` 不是硬约束

- 现状：配置写每个 slot `require_cover: true`，但生成 picks 可退回 Last.fm 图片或 `assets/placeholder.svg`。
- 风险：内容质量问题，不是稳定性问题。
- 建议：后续明确 `require_cover` 是“必须有非 placeholder 封面”，还是“优先有封面，允许 placeholder”。

### P2-5：`npm audit` 数量不足以判断当前静态站实际风险

- 现状：本地基线里 `npm --prefix ui ci` 报 8 个漏洞：4 moderate、3 high、1 critical。基线没有保存 advisory 明细。
- 锁文件观察：运行时依赖很小，主要是 `react`、`react-dom`、`react-router-dom`、`framer-motion`、`html2canvas`、`clsx`、`tailwind-merge` 及少量传递依赖。Vite、esbuild、Vitest、Playwright、PostCSS、Rollup、Babel 在 `package-lock.json` 中属于 dev/build-time。
- 风险：如果漏洞集中在 dev/build 工具，当前静态站 runtime 暴露面低于 audit 总数；但构建供应链风险仍然存在。`npm audit fix --force` 可能带来比当前漏洞更大的回归。
- 建议：做依赖修复前，先保存完整 `npm --prefix ui audit --json`，再单独跑并记录 `npm --prefix ui audit --omit=dev`。优先修 production-runtime advisory，构建工具升级要配 UI smoke。

## 不建议现在做的事

- 不建议先盲跑 `npm audit fix --force`。它可能升级大版本并引入 UI/build 回归，而且不能解决 P0 的高频 `today.json` 请求。
- 不建议在修 P0/P1 前重构生成器、router 或数据 schema。
- 不建议为了缓存刷新问题引入后端。当前静态模型可以成立，前提是刷新触发有边界、生成数据干净。
- 不建议继续把 `daily3albums doctor` 通过当作端到端健康证据，直到 doctor 实现符合 `AGENTS.md`。
- 不建议默认每次清空整个 `.state` cache。它对限流有价值，应改成 TTL 清理。

## 下一步最小改动建议

1. 修 `TodayRoute` 的 `today.json` 高频请求，并加一个证明 idle 页面不会持续 refetch 的回归检查。
2. 修 `debug_time` 的 HashRouter 参数读取，或统一更新文档和测试到正确 hash query URL。
3. 阻止 `ui/public/data` seed JSON 进入生产输出，并让 `self_check` 断言生成的 `data/index.json` 不含 `dev-seed`。
4. 扩展 `self_check`：BJT 日期对齐、当前 run archive 一致性、严格 3 slots x 3 picks。
5. 把 workflow 里的 `eval` 改成 shell array。
6. 在 Actions cache 保存前增加 SQLite TTL 清理。
7. 保存完整 npm audit 明细，按 runtime 与 dev/build 分层处理依赖漏洞。
