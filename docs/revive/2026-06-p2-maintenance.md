# 2026-06 P2 Maintenance

日期：2026-06-13
分支：`p2/2026-06-maintenance`
依据：`docs/revive/2026-06-code-audit.md` 的 P2-1 到 P2-5。
原则：小范围、低风险、可验证；不做大重构，不改变数据 schema，不改变 UI 设计。

## 处理结果

| 项目 | 状态 | 处理内容 | 原因 |
|---|---|---|---|
| P2-1 Python 3.14 / CI 3.11 边界 | 仅文档化 | README 中明确生产 CI 固定 Python 3.11，本地 3.14 只是开发环境 | 当前 Actions 固定 3.11，`pyproject.toml` 仍是 `>=3.11`；不增加阻断 3.14 job，避免可选优化影响主 CI |
| P2-2 UI 构建两次 | 已修 | `daily3albums build` 增加 `--skip-ui-build`；Pages workflow 在已跑 `npm --prefix ui run build` 后传入该参数；默认仍会构建 UI | 减少 Pages daily job 的重复 UI build，同时保留一条命令生成 `_build/public` 的能力 |
| P2-3 timezone / Asia/Shanghai | 仅文档化 | README、`config/config.yaml`、`daily3albums/cli.py` 注释明确产品时钟固定为 Asia/Shanghai | 当前产品定义就是北京时间；不引入多时区逻辑，也不把日期计算改成可切换产品行为 |
| P2-4 `require_cover` 语义 | 已修 | 配置注释和 README 明确它是软偏好；新增测试固定无封面时使用 `assets/placeholder.svg` 且 `has_cover=false` | 不改变选片算法，不让封面缺失导致大面积构建失败 |
| P2-5 npm audit 分层 | 已修 | 新增 `docs/revive/2026-06-npm-audit.md`；定向升级 runtime `react-router-dom` 到 `^6.30.4`；production-only audit 清零 | production runtime moderate 漏洞可在 React Router 6.x 内修复；dev/build-time 漏洞记录但不强行大版本升级 |

## 代码与流程变更

| 路径 | 变更 |
|---|---|
| `daily3albums/cli.py` | 增加 `--skip-ui-build`；默认行为不变；缺失 `ui/dist` 时给出明确错误；补充 BJT 固定产品时钟注释 |
| `.github/workflows/pages_daily.yml` | 在已经独立执行 UI build 后，调用 `daily3albums build --skip-ui-build` |
| `README.md`, `README.en.md` | 明确 Python 3.11 生产基线、BJT 固定产品定义、UI build 责任边界、cover fallback 语义 |
| `config/config.yaml` | 注释固定 timezone 和 `require_cover` 的软偏好语义 |
| `tests/test_cli_ui_timeout.py` | 增加 skip UI build 回归测试 |
| `tests/test_cover_policy.py` | 增加 placeholder cover fallback 语义测试 |
| `ui/package.json`, `ui/package-lock.json` | 定向升级 `react-router-dom` 到 `^6.30.4` |
| `docs/revive/2026-06-npm-audit.md` | 记录 npm audit runtime/dev-build 分层 |

## `--skip-ui-build` 边界

- 默认：`daily3albums build --verbose --out ./_build/public` 仍会运行 `npm --prefix ui run build`，保持一键构建。
- CI：Pages workflow 先运行 `npm --prefix ui run build`，再运行 `daily3albums build --skip-ui-build`，复用同一个 `ui/dist`。
- 保护：如果传入 `--skip-ui-build` 但 `ui/dist` 不存在，build 会失败并提示运行 UI build 或去掉该参数。

## npm audit 决策

- `npm --prefix ui audit --omit=dev --json` 处理前有 2 个 moderate：`react-router` / `react-router-dom`。
- 定向执行 `npm --prefix ui install react-router-dom@6.30.4`。
- 处理后 production-only audit 为 0。
- 完整 audit 仍有 6 个 dev/build-time 漏洞，集中在 Vite/Vitest/Rollup/PostCSS/picomatch/esbuild；未运行 `npm audit fix --force`，未做大版本升级。

## 暂缓项

- 不增加 Python 3.14 阻断 CI job。后续如需兼容性观察，可加非阻断 scheduled/manual job。
- 不把 `config.timezone` 扩展成多时区产品配置。
- 不把 `require_cover` 改为硬失败约束。
- 不在本轮升级 Vite/Vitest 大版本。

## 验证计划

本轮完成后运行：

```powershell
npm --prefix ui test
npm --prefix ui run build
python -m pytest
daily3albums doctor
daily3albums build --verbose --out ._build\public
python scripts/self_check.py --path ._build\public
git diff --check
git status -sb
git diff --stat
```
