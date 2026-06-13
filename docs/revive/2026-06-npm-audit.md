# 2026-06 npm audit 分层记录

日期：2026-06-13
范围：`ui/` 前端依赖
命令：

```powershell
npm --prefix ui audit --json
npm --prefix ui audit --omit=dev --json
```

## 结论

| 层级 | 处理前结果 | 本轮处理 | 处理后结果 | 风险判断 |
|---|---:|---|---:|---|
| production runtime | 2 moderate | 定向升级 `react-router-dom` 到 `^6.30.4` | 0 | 已修；静态站 runtime 依赖不再有 npm audit advisories |
| dev/build-time | 完整 audit 合计 8 个漏洞 | 仅记录，不运行 `npm audit fix --force` | 完整 audit 仍剩 6 个漏洞 | 主要影响本地/CI dev server、测试或构建供应链；需要单独升级 Vite/Vitest/PostCSS/Rollup 链路并做 UI smoke |

本轮允许修改 `ui/package.json` 与 `ui/package-lock.json` 的原因：production runtime 漏洞集中在 `react-router` / `react-router-dom`，可通过 React Router 6.x 小版本升级修复，没有跨大版本。

## Production Runtime

处理前 `npm --prefix ui audit --omit=dev --json`：

| package | severity | advisory | range | fix |
|---|---|---|---|---|
| `react-router` | moderate | `GHSA-2j2x-hqr9-3h42`：same-origin redirect with `//` path open redirect | `>=6.7.0 <6.30.4` | 升级到 `6.30.4` |
| `react-router-dom` | moderate | 受 `react-router` 传递影响 | `6.6.3-pre.0 - 6.30.3` | 升级到 `6.30.4` |

处理动作：

```powershell
npm --prefix ui install react-router-dom@6.30.4
```

处理后 `npm --prefix ui audit --omit=dev --json`：

```json
{
  "vulnerabilities": {
    "info": 0,
    "low": 0,
    "moderate": 0,
    "high": 0,
    "critical": 0,
    "total": 0
  }
}
```

## Dev / Build-Time

处理后完整 `npm --prefix ui audit --json` 仍报告 6 个漏洞：

| package | severity | direct | advisory / title | 当前处理 |
|---|---|---:|---|---|
| `vitest` | critical | yes | `GHSA-5xrq-8626-4rwp`：Vitest UI server arbitrary file read/execute | 暂缓；dev/test 工具，需单独升级 Vitest 并跑 UI test/build |
| `vite` | high | yes | `GHSA-4w7w-66w2-5vf9`, `GHSA-v2wj-q39q-566r`, `GHSA-p9ff-h696-f583`；同时受 `esbuild` advisory 影响 | 暂缓；audit 建议 Vite 8，属于大版本升级 |
| `rollup` | high | no | `GHSA-mw96-cpmx-2vgc`：path traversal arbitrary file write | 暂缓；构建链路传递依赖 |
| `picomatch` | high | no | `GHSA-3v7f-55p6-f55p`, `GHSA-c2c7-rcm5-vvqj` | 暂缓；测试/构建传递依赖 |
| `postcss` | moderate | yes | `GHSA-qx2v-qp2m-jg93`：CSS stringify XSS | 暂缓；dev/build dependency，后续可做补丁升级 |
| `esbuild` | moderate | no | `GHSA-67mh-4wv8-2f99`：dev server request exposure | 暂缓；audit fix 指向 Vite 8 大版本 |

## 未做的事

- 未运行 `npm audit fix --force`。
- 未盲目升级 Vite/Vitest/Rollup 相关大版本。
- 未改变 UI 业务代码或样式。

## 后续建议

1. 单独开依赖维护 PR，把 Vite/Vitest/PostCSS/Rollup 链路作为 build-tool 升级处理。
2. 升级前后至少跑 `npm --prefix ui test`、`npm --prefix ui run build`，必要时补一轮本地静态预览 smoke。
3. 如果暂不升级 dev/build 工具，避免在不可信网络暴露 Vite/Vitest dev server。
