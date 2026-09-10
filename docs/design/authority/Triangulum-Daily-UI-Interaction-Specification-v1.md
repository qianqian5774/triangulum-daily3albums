# Triangulum Daily UI & Interaction Specification — Formal v1

状态：**当前交互与状态 authority**
生效日期：2026-08-30

## 1. 文档职责

本文只定义产品状态、输入、时间、迁移、返回、持久化和无障碍行为。视觉材质、构图、颜色、人物外观和画面验收由 [`ui-visual-interaction-system.md`](./ui-visual-interaction-system.md) 决定；产品意图由 [`ui-redesign-concept-v1.md`](./ui-redesign-concept-v1.md) 解释。

## 2. 产品表面与完整链路

标准链路为：

`Record Shop 店外 Entry Diorama → 选择有限相机视角 → 激活实体大门 → 店内 Offline/Ready → Daily OPEN → Shuffle → Continue → 水平唱片浏览 → Treatment Viewer → 返回原浏览位置 → HUD 最近日期 → 返回店外`

补充边界：

- Record Shop 承载店外与店内的连续体验。
- Archive Page 仍是站点保留的静态历史表面，不被解释成另一间房；店内 HUD 的最近日期切换是同一店内的快速历史浏览。
- Treatment Viewer 是覆盖层，不是独立详情路由。
- 进入店内与唱片解锁是两个独立条件。用户可在 08:00 BJT 前进入店内，但装置保持 Offline。

## 3. 产品时间

所有日界线、解锁和每日状态以 BJT（UTC+8）为准。

| BJT 时段 | Today 可用库存 | 装置基础状态 |
| --- | ---: | --- |
| 00:00–07:59 | 0 | Offline |
| 08:00–12:29 | 3 | Online |
| 12:30–15:59 | 6 | Online |
| 16:00–23:59 | 9 | Online |

12:30 和 16:00 只向同一水平库存追加新唱片，不重新播放 Shuffle，不要求再次 OPEN，也不提前显示未解锁唱片。

环境昼夜可以由同一 BJT 时钟驱动，但它不改变库存数量。店外环境与店内门窗所见的外部时间必须一致。

## 4. 店外状态与输入

### 4.1 初始状态

- 初始到达对象是持久存在的 Entry Diorama，不再播放“普通街道 → 建筑分开 → 店铺出现”的旧序列。
- 默认相机必须属于批准视角集合，并完整显示合法构图。
- HUD、装置控制、唱片浏览和店内日期控件在店外不可操作。

### 4.2 Preset views and bounded inspection

- AXON、FRONT、RIGHT、REAR、LEFT、ROOF 六个 preset view 是可重复检查的构图锚点；选择 preset 会恢复该预设相机。
- 指针拖动或触控可在实现的 yaw、pitch 与 zoom 边界内检查同一 Entry Diorama；它不是第一人称、无边界轨道或可离开 Diorama 世界的漫游。
- 点击或触控大门以外区域不能触发进入；选择入口 preset 后再激活实体门。
- reduced motion 下视角切换直接或短淡入完成；受限检查和缩放仍不能改变建筑、基座或进入目标。
## 5. 进入与返回

激活大门后进入店内。过渡完成前，店内控件不可提前获得焦点；完成后，焦点移到店内主要状态／操作入口。

返回店外时：

- 清除临时 hover、打开的日期菜单和未完成的指针拖动；
- 保留由 BJT clock 决定的当前库存数量；
- 恢复最近选择的 preset view；受限自由观察不作为跨越这次店内往返的持久状态；
- 不重新播放旧入口显现序列。

## 6. 店内基础状态

店内固定包含环境、店员、中央装置和 HUD。状态机不得通过切换到另一个房间、黑色抽象空间或普通 dashboard 取代店内。

### 6.1 HUD

HUD 在店内持续可见，最少显示：

- 当前产品日期；
- 当前 BJT 时间或时段；
- 装置状态（Offline／Ready／On）；
- 当前库存数量或下一次解锁信息；
- 当前是否处于历史日期。

HUD 日期控件只在可用历史数据存在时启用。菜单打开是临时状态，不写入持久化。

### 6.2 Offline

00:00–07:59 期间：

- 用户可以进入店内；
- 装置显示 Offline 和下一上线时间；
- OPEN、Shuffle、Continue 和 Today 浏览不可执行；
- HUD 和环境保持可读；
- 不展示未来唱片的锁定替身。

08:00 到达时，装置原地转为 Ready，不退出店内、不重置相机或重载整个体验。

## 7. Daily Device session flow

当前已上线的店内以组件会话状态呈现 Daily Device：当 BJT 已有库存时，进入店内后装置处于 Ready；触发后显示短暂 Shuffle；完成后由 Continue 进入可浏览的唱片序列。Offline 期间装置保持 Offline，08:00 到达后可进入 Ready。

这套状态不会创建账户、服务器状态或访客写入。当前实现也不把 Daily OPEN 完成或 Skip 资格作为跨刷新／跨重新进入店内的持久承诺；重新挂载店内时应以当时的公开 issue 和 BJT 状态为准。若未来加入持久化，必须连同状态迁移、无障碍和测试一起更新本规范。

Shuffle 不等同于 3／6／9 条实际库存。12:30 与 16:00 只向同一有限库存追加新唱片，不提前展示未来唱片。
## 8. 水平唱片浏览

- 库存是一个有序、有限、水平延伸的唱片序列，数量为当前 Today 的 3、6 或 9，或历史日期的完整 9。
- 支持指针／触控水平拖动、明确方向控件和键盘 Left／Right。
- 到达边界时停止，不循环到另一端；HUD 可提示下一解锁时间。
- hover、pointer focus 和 keyboard focus 是临时状态，不写入持久化。
- 12:30／16:00 的新增唱片附加到同一序列，尽量保留当前浏览位置。

打开唱片时记录当前水平位置和唱片标识，随后进入 Treatment Viewer。

## 9. Treatment Viewer

Treatment Viewer 显示当前唱片的封面、标题、艺人、可用的可靠元数据、推荐上下文和有效外部探索路径。

行为要求：

- 打开后焦点进入 Viewer，背景交互暂停；
- Escape、明确关闭按钮和可访问返回动作均可关闭；
- 关闭后恢复打开前的水平位置；
- 恢复为无 hover、无选中的中立浏览状态；
- 当前日期和库存保持不变；
- 不创建独立详情路由或要求账户、后端、播放服务、评论或访客写入。

## 10. 最近日期与 Archive Page

### 10.1 店内最近日期

HUD 可提供当前日期和最近可用日期的有限列表。选择历史日期时：

- 仍留在同一店内；
- 只替换装置库存和 HUD 活跃日期；
- 历史完整日期直接显示 9 张唱片；
- 不播放 Shuffle，不重置当日 OPEN 状态；
- 浏览和 Treatment Viewer 行为与 Today 相同。

选择当前日期后，立即恢复真实 BJT 对应的 0／3／6／9 库存。

### 10.2 Archive Page

Archive Page 保留为静态历史入口，可覆盖比 HUD 更广的日期范围。进入 Archive Page 不被表现成另一间店或另一套唱片交互隐喻；从 Archive Page 打开专辑仍使用 Treatment Viewer 术语和静态站点数据边界。

## 11. Persistence boundary

持久的产品事实是已发布静态 issue、archive index 与 archive JSON。BJT 时钟决定当前 issue 的可见 0／3／6／9 库存。

店内的 device 状态、打开的 Treatment Viewer、日期菜单、hover/focus、拖动与自由观察都属于当前客户端会话。它们不构成访客身份、跨设备状态或浏览器端写入契约。存储不可用、刷新页面或返回并重新进入店内时，体验必须能从当前公开数据和 BJT 时间安全恢复。
## 12. Current state transitions

| From | Cause | To |
| --- | --- | --- |
| 店外 preset view | 选择另一 preset | 对应构图锚点 |
| 店外 | 受限拖动／缩放 | 同一 Diorama 的受限检查状态 |
| 店外 | 激活实体大门 | 店内 Offline 或 Ready |
| 店内 | 返回店外 | 最近选择的 preset view |
| Offline | 到达 08:00 BJT | Ready |
| Ready | OPEN | Shuffle |
| Shuffle | 完成 | Complete |
| Complete | Continue | Today 水平浏览 |
| Today 浏览 | 12:30／16:00 到达 | 同一有限库存的 6／9 条可用唱片 |
| 浏览 | 激活唱片 | Treatment Viewer |
| Treatment Viewer | 关闭／返回 | 原浏览位置附近的中立浏览状态 |
| 浏览 | 选择历史日期 | 同一店内的历史库存 |
| 历史浏览 | 选择 Today | 当前真实 BJT 库存 |
## 13. Current non-negotiable behavior

- 初始店外是持久 Entry Diorama，不再恢复旧街道显现序列。
- 六个 preset view 提供可重复构图；自由检查与缩放必须留在实现的边界内，不得改变模型结构或离开 Diorama 世界。
- 只有实体门执行进入；进入不等于解锁唱片。
- HUD 在店外隐藏、店内持续存在。
- Today 库存严格遵守 BJT 0／3／6／9；不提前展示未来唱片的锁定替身。
- Daily Device 的 OPEN／Shuffle／Continue 是当前店内会话流程，不声称跨刷新或跨设备持久化。
- 新时段扩展同一有限库存，不创建三套界面。
- Treatment Viewer 是覆盖层，关闭后回到同一浏览上下文。
- 历史日期使用同一店内装置；Archive Page 不是另一间房。
- 所有关键操作都有键盘、触控和可见 focus 等价路径。
- 已部署浏览器不调用外部音乐／元数据 API，不引入账户、访客写入或后端。
