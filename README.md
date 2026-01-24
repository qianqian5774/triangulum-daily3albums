# Triangulum Daily 3 Albums

[English](README.en.md) | 中文

**Triangulum** （黑胶囊）是一个运行在 GitHub Pages 上的**时间确定性静态自动机**，也是一个极其克制的每日音乐推荐系统。

在一个算法无限流的时代，Triangulum 选择回归“有限”与“秩序”。它拒绝实时生成的无限列表，而是每天像派发“处方药”一样，严格按照**北京时间（Asia/Shanghai）** 的早、中、晚三个时段，向访问者解锁当日的三张精选专辑。

### 核心理念：静态托管，动态灵魂

这个项目的工程哲学在于**“一次构建，全天自治”**。它打破了静态站点必须依赖服务器部署才能更新内容的传统限制，通过**运行时时段解锁（Runtime Slot Unlock）** 机制，实现了一个无需后端介入的动态体验：

- **数字新陈代谢**：系统拥有自己的作息。每天 **00:00 (BJT)** 准时进入 `OFFLINE`（休眠）状态，仅保留昨日存档；直到清晨 **06:00 (BJT)** 重新“苏醒”，开始新一天的运转。
- **便当盒架构 (Bento-Box Architecture)**：每天凌晨，GitHub Actions 仅运行**一次**构建任务，将全天三个时段的数据（Slot 0/1/2）预先打包进一个静态 JSON 中。
- **客户端时间主权**：浏览器不再被动等待服务器更新，而是根据**本地计算的北京时间**，自主决定是展示内容还是保持锁定。无论 CDN 缓存在何处，用户看到的永远是“此刻”应有的状态。

---

## 本地构建 + 预览

1)（可选）如果你改动了 UI 代码，先构建 UI：

```bash
npm --prefix ui ci
npm --prefix ui run build
```

2) 生成每日产物（生成器会把运行时 JSON 写入 `_build/public/data`）：

```bash
daily3albums build --verbose --out ./_build/public
```

3) 从 `_build/public` 启动静态预览：

```bash
python -m http.server --directory _build/public 8000
```

然后访问：`http://localhost:8000/`

> 注意：本地测试必须只服务 `_build/public`。不要服务 `ui/public/data`（或 `ui/dist/data`），否则会把 UI seed JSON 当成运行数据，造成“看似正常但数据不刷新/封面不对”等假象。

---

## 运行时解锁窗口（北京时间）

站点在浏览器端用 **北京时间（Asia/Shanghai）** 计算当前状态：

- `OFFLINE`：00:00–05:59
- `SLOT0`：06:00–11:59
- `SLOT1`：12:00–17:59
- `SLOT2`：18:00–23:59

解锁切换是**纯前端行为**：只要当天 `today.json` 已生成并部署，浏览器就会根据北京时间选择展示哪个 slot；到达边界时可无刷新切档（取决于 UI 的运行时状态机实现）。

---

## 定时构建 + 时区（GitHub Actions）

GitHub Pages 工作流每天只跑一次，用于生成并部署“今天”的数据：

- 目标时间：北京时间 **05:17**（Asia/Shanghai）
- Cron（UTC）：`17 21 * * *`（注意：这是 **UTC 前一日 21:17**）
- 可在工作流内部增加小幅抖动（例如 `0–120s`）用于避开同秒拥挤，但**解锁时刻不抖动**
- 工作流时区必须显式指定：`TZ=Asia/Shanghai` 与 `DAILY3ALBUMS_TZ=Asia/Shanghai`

重要：生成器必须用 Asia/Shanghai 计算“今天”的日期键（`today.json.date`），不能用 runner 默认 UTC，否则会出现“生成了 UTC 的日期 → 北京时间错一天”的灾难。

---

## Debug Mode（时间模拟）

开发时不可能等到真实时间边界。使用 `debug_time` 可以瞬间模拟北京时间的“跨 slot / 跨日 / OFFLINE 进入”等所有边界情况。

### 用法

在 URL 后追加：

`?debug_time=YYYY-MM-DDTHH:MM:SS`

规则：

- 该时间按 **北京时间（Asia/Shanghai）** 解释
- 秒可省略：`YYYY-MM-DDTHH:MM` 也可
- `debug_time` 生效时，UI 会把它当作“当前时间”，用于：
  - OFFLINE ↔ SLOT 切换
  - 06:00 / 12:00 / 18:00 边界
  - 跨日滚动（23:59:xx → 00:00:xx）

### 示例

- 测 OFFLINE → SLOT0：

`http://localhost:8000/?debug_time=2024-03-21T05:59:50`

然后改成：

`http://localhost:8000/?debug_time=2024-03-21T06:00:10`

- 测 SLOT2 → OFFLINE（跨日）：

`http://localhost:8000/?debug_time=2024-03-20T23:59:50`

然后改成：

`http://localhost:8000/?debug_time=2024-03-21T00:00:10`

### 关闭 Debug Mode

移除 `debug_time` 参数并刷新页面即可。

如果 UI 还会把 debug_time 写入 sessionStorage，可手动清理：

```js
sessionStorage.removeItem("tri_debug_time");
```

---

## 缓存注意事项

浏览器与 CDN 可能缓存 `today.json`。在关键边界（尤其是 OFFLINE → SLOT0 的 06:00）建议做一次强制穿透缓存的请求，例如：

- `fetch("/data/today.json?t=" + Date.now(), { cache: "no-store" })`

如果拉到的数据仍是旧日（比如 `today.json.date` 不是“北京时间今天”），UI 应进入安全降级态并重试，直到拿到正确日期的数据为止。
