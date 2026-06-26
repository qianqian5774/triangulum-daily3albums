# UI Terminology

本文是 Triangulum Daily 3 Albums 描述 UI 问题、派发 UI 任务和审查 UI PR 时的标准词表。不要用“顶部区域”“专辑页面”“按钮没反应”“手机页面乱了”这类模糊说法，应该落到具体页面、组件、状态、数据文件和复现路径。

## Page-Level Terms

- Today Page：默认路由 `/`。展示当前日期、BJT 解锁状态、Today Timeline、Album Grid、Share Card 入口、Ambient 入口、Offline State 和 Treatment Viewer overlay。
- Archive Page：路由 `/archive`。读取 `data/index.json`，再读取最近日期对应的 archive JSON，展示 Date List 和按日期/slot 分组的 archived Album Cards。
- Treatment Viewer：从 Today Page 的 Album Card 打开的覆盖式详情浏览器。它不是独立 route。它包含上一张/下一张、键盘切换、swipe、metadata、overview 和外链。
- Share Card Dialog：配置、预览和下载分享卡 PNG 的弹窗。
- Project Info Dialog：从 HUD 打开的项目说明弹窗。
- Ambient Overlay：从 Today Page 进入的沉浸/待机覆盖层。
- BSOD：静态 JSON 加载或解析失败时的错误面板。不要把正常的 Offline State 叫 BSOD。

## HUD And Status Terms

- HUD：固定在顶部的全局状态面板，代码在 `ui/src/components/Hud.tsx`。包含 BJT Clock、Status Badge、导航、Language Toggle、Font Scale Controls、debug badge、状态消息和 Marquee。
- BJT Clock：HUD 中的北京时间显示。它由真实 Asia/Shanghai 时间或 `debug_time` 驱动。
- Status Badge：HUD 状态徽标。当前状态值包括 `OK`、`DEGRADED`、`ERROR`、`OFFLINE` 和 `ARCHIVE`。
- Marquee：HUD 的滚动信息条，通常来自已解锁或已归档的专辑标题和艺人。
- Language Toggle：EN / 中文分段控件，状态写入 localStorage。
- Font Scale Controls：A- / A+ / reset 字号控件，写入 `tri_ui_font_scale` 并设置 `--ui-font-scale`。
- Project Info Button：HUD 中打开 Project Info Dialog 的按钮。

## Today Page Terms

- Today Timeline：Today Page 上的三个解锁窗口入口。未解锁的未来 slot 会 disabled。
- Slot：一天中的一个 BJT 解锁窗口。当前是 06:00-11:59、12:00-17:59、18:00-23:59。
- Album Grid：展示当前可见 slot Album Cards 的网格区域。
- Album Card：`SlotCard` 渲染的专辑卡片，显示封面、Slot Badge、标题、艺人、年份、tag、MusicBrainz rating/tags 和外链。在 Today Page 中可打开 Treatment Viewer。
- Slot Badge：Album Card 上的 Headliner / Lineage / Deep Cut 标签。代码值是 `DeepCut`，UI 文案显示为 `Deep Cut`。
- Share Card Button：打开 Share Card Dialog 的 Today Page 控件。没有任何 slot 解锁时不可用。
- Ambient Button：进入 Ambient Overlay 的控件。
- Offline State：BJT 00:00-05:59 的正常等待状态。Today Page 显示离线等待界面，并可能展示锁定的归档预览。
- Offline Locked Panel：Offline State 中不可导航的归档预览区。点击后给 locked feedback，不应该静默跳转到 Archive Page。
- Signal Lost / Restored：`today.json` 加载失败或日期不匹配时的 Today Page 运行状态。

## Archive Page Terms

- Archive Mode：Offline State 内浏览 Archive Page 时的 HUD 状态。代码状态为 `ARCHIVE`，展示文案为 archive mode。
- Date List：Archive Page 左侧日期列表。
- Recent Static Archive：构建时恢复并写入的最近静态归档数据。它不是数据库，也不能在访客访问时扩展。
- archive JSON：某个日期/run 的归档数据，路径优先为 `data/archive/{date}/{run_id}.json`，并有 `data/archive/{date}.json` fallback。
- Archived Album Card：Archive Page 中的历史专辑卡片。数据模型与当前 pick 相同，但语境是历史浏览。

## Share Card Terms

- Share Card Canvas：1080 x 1440 的 DOM 画布，用于预览和导出 PNG。
- Share Card Version：`0600`、`1200`、`1800` 三种版本。它们分别包含 max slot id 0、1、2，所以包含 3、6、9 张已解锁专辑。
- Share Card Theme：弹窗内可选的 `day` 或 `night` 视觉主题。
- Share Card Language：导出语言。弹窗打开后可独立于 HUD 全局语言切换。
- Download PNG：等待图片加载后用 `html2canvas` 渲染并下载 PNG 的命令。
- No Cover Placeholder：封面缺失或加载失败时的分享卡占位。

## Debug And Time Terms

- debug_time：模拟 BJT 的 URL 参数，例如 `#/?debug_time=2026-06-26T05:59:00`。它驱动 HUD clock、slot 状态、Offline State 和 visual theme。
- `tri_debug_time`：debug time 使用的 sessionStorage key。
- Debug Flag：`debug=1` 或 `debug=true`。HashRouter URL 也支持，例如 `#/?debug=1`。
- Time Lab：debug 模式下显示的时间实验室面板。包含 OFFLINE / 05:59、06:00、12:00、18:00、20:00 transition、clear debug time 和 Ambient 入口。
- Debug Time Active：HUD 或 Time Lab 中提示当前由模拟时间驱动的状态。

## Responsive Terms

- Mobile Layout：小屏布局。常见问题包括 HUD 堆叠、timeline 行为、Album Grid 单列、dialog 尺寸、safe area 和 touch target。
- Desktop Layout：大屏布局。常见问题包括 HUD 多列和 Today Page 的 timeline + Album Grid 并排布局。
- Breakpoint：CSS 或 Tailwind 切换布局的断点。
- Touch Target：按钮、timeline、Album Card、viewer controls、share controls 和 HUD controls 的可点击/触摸区域。
- Horizontal Overflow：页面级内容宽度超过 viewport。局部 timeline 横向滚动可以是合法行为，全页横向溢出是缺陷。
- Safe Area：移动端刘海、圆角和系统手势区域。HUD、overlay 和 exit hint 应避开它。
- Reduced Motion：系统 `prefers-reduced-motion` 下的低动效行为。

## Data, Routing, And Public Path Terms

- today.json：`data/today.json`，Today Page 的数据产物。包含 `date`、`run_id`、`theme_of_day`、当前 slot 的 top-level `picks` 和完整 `slots`。
- index.json：`data/index.json`，Archive Page 的归档索引。包含 `archive_retention_days` 和最近归档条目。
- archive JSON：从 `data/archive/...` 加载的静态归档 issue payload。
- HashRouter：`ui/src/main.tsx` 中的前端路由器。公开路由是 `#/` 和 `#/archive`。
- GitHub Pages base path：Vite `base` 和 `import.meta.env.BASE_URL` 影响的 Pages 子路径资源前缀。
- Public Path：`resolvePublicPath()` 拼接静态 data/assets 路径的规则。它会去掉开头斜杠并加上 Vite `BASE_URL`。
- Cache Buster：附加在静态 data 或 cover URL 上的查询参数，用于绕开旧缓存。
- Published Archive Seed：构建前从已发布站点取回并作为 seed 的归档 JSON。

## Vague Phrase Replacements

| 模糊说法 | 更准确说法 |
|---|---|
| 顶部区域 | HUD |
| 左上角时间 | BJT Clock |
| 状态那个东西 | Status Badge |
| 首页 / 主屏 | Today Page |
| 历史页面 | Archive Page、Date List 或 archive JSON |
| 专辑页面 | Album Card、Treatment Viewer、Archive Page 或 Share Card Canvas |
| 按钮没反应 | 指明具体控件，例如 Share Card Button、Language Toggle、Time Lab Button、Viewer Control、Project Info Button |
| 手机页面乱了 | Mobile Layout、Breakpoint、Horizontal Overflow、Touch Target 或 Safe Area |
| 分享图不对 | Share Card Dialog、Share Card Canvas、Share Card Version、Share Card Theme 或 Share Card Language |
| URL 不对 | HashRouter、GitHub Pages base path 或 Public Path |

## Request Templates

1. “在 Today Page 的 HUD 里，BJT Clock 在 `{viewport/debug_time}` 下显示 `{actual}`，预期是 `{expected}`。”
2. “打开 `#/?debug=1`，在 Time Lab 点击 `{control}` 后，`{specific region}` 应该 `{expected}`，但实际 `{actual}`。”
3. “在 Offline State 下，Offline Locked Panel 应该 `{expected}`，但现在 `{actual}`。”
4. “在 Archive Page 中，Date List 选中 `{date}` 后，右侧 Album Grid 没有匹配 archive JSON。”
5. “Share Card Dialog 中，Share Card Version `{0600/1200/1800}` 泄露或隐藏了 `{specific slot}`。”
6. “Mobile Layout 在 `{width}px` 下，`{specific component}` 导致 Horizontal Overflow 或 Touch Target 不足。”

## Source basis

Verified from source:
- 路由与 HashRouter：`ui/src/main.tsx`、`ui/src/App.tsx`、`ui/src/routes/Today.tsx`、`ui/src/routes/Archive.tsx`。
- HUD、dialogs、overlays、cards、share-card、settings、data、paths 和 BJT 逻辑位于 `ui/src/components/` 和 `ui/src/lib/`。
- `today.json`、`index.json` 和 archive JSON 解析位于 `ui/src/lib/types.ts` 与 `ui/src/lib/data.ts`。
- Share Card version 行为位于 `ui/src/lib/share-card.ts`。

Inferred from current behavior:
- 本词表把 UI 问题定位到稳定组件、路由、数据产物和运行状态，适合后续任务复用。
- `Deep Cut` 是代码值 `DeepCut` 的用户可见文案。

Not implemented / Not confirmed:
- Treatment Viewer 当前不是独立 route。
- 当前 UI 未实现后端详情页、登录、评论、播放器或用户状态系统。
