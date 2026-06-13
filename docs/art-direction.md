# Triangulum Daily 3 Albums Art Direction

本文用于统一后续网站整体美术升级和每日分享卡片图的视觉方向。它不是实现方案，不要求本轮改代码、生成图片或引入依赖。

当前阶段只聚焦两件事：

1. 整体美术升级。
2. 每日分享卡片图。

暂不处理域名、服务器、留言、播放器、专辑长介绍、后端，也不处理 Archive 功能问题。Archive 在本文里只保留未来视觉原则。

## 1. 核心方向

推荐方向：**Acid Rave Signal Archive（酸性 Rave 唱片信号档案）**。

中文可描述为：**地下酸性唱片信号系统**。

它也可以接近这些语义：

- Underground Album Signal System（地下唱片信号系统）
- Y2K Glitch Album Terminal（Y2K 故障唱片终端）
- 地下酸性唱片信号档案

这不是普通音乐推荐站，也不是流媒体产品。Triangulum 的核心不是“猜你喜欢”，而是反推荐算法的每日听觉仪式：

- 它不是根据你越听什么就继续推什么。
- 它不是 playlist feed（歌单信息流）。
- 它不是排行榜、热门榜或推荐流。
- 它强调 album as a unit（以专辑为单位）。
- 它每天按固定时段释放专辑，让用户重新以“专辑”为单位听音乐。

项目名仍然是 **Triangulum Daily 3 Albums**，这是历史名称和品牌名；但当前页面发布结构应统一理解为：

```text
daily 9 albums
3 unlock windows
3 albums each
06:00 / 12:00 / 18:00
BJT
```

中文表述：

```text
每天九张专辑
三个时段
每个时段三张
06:00 / 12:00 / 18:00
北京时间
```

后续文案、分享卡和视觉结构不要再写成“每天三张专辑”。如果需要解释项目名，可以说 Daily 3 Albums 是历史项目名，但当前公开发布结构是 daily 9 albums / 3 unlock windows / 3 albums each。

## 2. 当前已有视觉语言

当前黑底、酸绿色、扫描线、HUD、Ambient、Album Card 这些方向是对的，不需要推翻。需要修正的是解释方式：不再主要解释为“慢速观测站”，而是解释为地下信号系统、Rave 入口、唱片档案终端和 Y2K 故障界面。

现有前端已经形成的基础：

- `void-black #050505`：黑色系统底。
- `panel-900 #0C0C0C`、`panel-800 #121212`、`panel-700 #1A1A1A`：深色面板和边框层级。
- `acid-green #CCFF00`：主识别色，像信号灯、入口灯、Rave flyer 上的酸性印刷色。
- `alert-red #FF3300`：错误、离线、信号中断。
- `clinical-white #F0F0F0`：文字、线框、档案标签。
- HUD（顶部状态面板）：可解释为 club door control（地下入口控制台）、signal console（信号控制台）、bootleg archive terminal（地下档案终端）。
- Marquee（滚动信息条）：不是公告栏，而是信号带、低速数据流、唱片标题广播。
- Album Card（专辑卡片）：不是普通产品卡片，更像 flyer（传单）、档案标签、唱片箱里的编号卡。
- Ambient Overlay（沉浸覆盖层）：像无人操作时的低频屏保、Rave 前的黑场、信号待机。
- Glitch / glow（故障 / 发光）：用于状态反馈和酸性界面质感，但不能压过专辑信息。
- Noise / scanline / grid（噪声 / 扫描线 / 网格）：作为低清数字材质，而不是装饰壁纸。

一句话原则：

**系统像地下信号终端，专辑封面才是每天变化的主视觉。**

## 3. 视觉关键词

核心关键词：

- underground rave（地下 Rave）
- Y2K
- acid graphics（酸性设计）
- glitch（故障）
- black + acid green（黑底 + 酸绿）
- low-res digital texture（低清数字纹理）
- scanner light（扫描光）
- signal noise（信号噪声）
- album archive（唱片档案）
- anti-feed（反信息流）
- anti-algorithm（反推荐算法）
- daily ritual（每日仪式）
- time-window release（时段释放）

中文关键词：

- 地下 Rave
- Y2K
- 酸性设计
- 故障视觉
- 黑底荧光
- 低清数字纹理
- 扫描光
- 信号噪声
- 唱片档案
- 反信息流
- 反推荐算法
- 每日仪式
- 时段释放

这些关键词不能只堆在视觉上。每个关键词都应服务信息结构：九张专辑、三个时段、专辑封面、日期、BJT、档案。

## 4. 明确不要走的方向

### 不要做成流媒体产品

避免：

- Spotify / Apple Music 风格。
- 普通音乐 App 首页。
- 推荐流、playlist feed、排行榜、热门榜。
- “发现更多”“立即播放”“为你推荐”这类平台感 CTA。
- 大面积圆角封面墙和商业化卡片堆。

原因：Triangulum 是反推荐算法项目，不是无限内容消费产品。

### 不要做成复古黑胶唱片店

避免：

- 大面积米色、牛皮纸、复古唱片店拟物。
- 黑胶唱片、唱针、旧海报作为主视觉。
- 手帐化、咖啡馆化、温暖怀旧路线。

原因：当前骨架是黑色数字终端，不是实体唱片店。

### 不要做成泛赛博朋克或 AI 壁纸

避免：

- 紫蓝霓虹城市、雨夜、霓虹汉字。
- 大面积高饱和渐变。
- 泛黑客终端表演感。
- 无关的宇宙、抽象、人像、AI 壁纸大图。

原因：这会稀释 acid green（酸绿色）识别，也会抢走专辑封面的注意力。

### 不要做成医疗、药物或恐怖实验室

项目最初中文名曾经叫“黑胶囊”，有一点“给你解药”的感觉。现在可以保留一点冷感、仪式感和黑色系统感，但不要继续把胶囊、解药、医疗、处方、treatment、dose 作为核心视觉方向。

避免：

- 胶囊、解药、病历、针管、处方单。
- 医疗恐怖、药物隐喻、实验室恐怖。
- 血液、手术室、惊吓式视觉。
- 把现有代码里的 treatment / dose 语言视觉化成医疗系统。

原因：当前方向应是地下 Rave / Y2K / 酸性设计 / 唱片档案，不是医疗叙事。

### 不要做成廉价夜店或商业音乐节海报

避免：

- 过度商业音乐节海报。
- EDM 派对宣传海报。
- 廉价霓虹夜店风。
- 过度潮流贴纸拼贴。
- 把 Y2K 做成可爱风或泡泡糖风。
- 把酸性设计做成纯装饰，导致专辑信息看不清。

原因：Triangulum 可以有地下 Rave 能量，但它仍是每日专辑档案系统，不是派对售票海报。

## 5. 颜色系统

### 保留核心色

| Token（色彩名） | Hex | 用途 |
|---|---|---|
| `void-black` | `#050505` | 页面底色、分享卡主背景、地下黑场 |
| `panel-900` | `#0C0C0C` | HUD、弹窗、深色面板 |
| `panel-800` | `#121212` | Album Card（专辑卡片）面板、封面 fallback（回退）底 |
| `panel-700` | `#1A1A1A` | 边框、分隔、弱层级面 |
| `clinical-white` | `#F0F0F0` | 主要文字、白色线框、档案标签 |
| `acid-green` | `#CCFF00` | 主识别、当前状态、BJT、焦点、信号灯 |
| `alert-red` | `#FF3300` | 错误、离线、信号丢失、短暂警报 |

绿色仍是主识别。它应该像地下入口的荧光灯、信号终端的运行灯、bootleg flyer（地下传单）上的酸性油墨，不是整页大面积铺色。

### 可扩展辅助色

这些是未来可选扩展，不要求本轮进代码：

| 建议 Token（色彩名） | 建议值 | 用途 |
|---|---|---|
| `acid-yellow` | `#EFFF4A` | 时段标记、分享卡细线、短暂高亮 |
| `toxic-lime` | `#B6FF00` | 酸绿的近邻变化，只用于微小层级 |
| `dirty-cyan` | `#42E8D8` | 扫描偏色、Y2K 界面噪声、小面积错位边 |
| `signal-amber` | `#FFD166` | 等待、降级、即将解锁 |
| `hot-magenta` | `#FF2BD6` | 极小面积故障偏移或分享卡角标 |
| `archive-gray` | `#7A7F78` | Archive（归档）弱化信息、旧记录、日期索引 |

使用规则：

- acid green（酸绿色）仍是主识别。
- hot magenta（热品红）、dirty cyan（脏青色）、acid yellow（酸黄）只能小面积使用。
- 不要变成彩虹霓虹。
- 专辑封面本身已经有很多颜色，系统色不能抢封面。
- 分享卡可以比网站更大胆，但仍要保证封面、标题、艺人名清楚。

建议比例：

```text
70% void black / panel black
18% clinical white / off white
7% album covers
4% acid green
1% alert red / amber / cyan / magenta accents
```

## 6. 字体方向

继续使用 sans + mono 的组合。

| 字体角色 | 用途 | 原则 |
|---|---|---|
| Sans（无衬线） | 专辑名、正文、项目说明、主要阅读文本 | 清楚、硬朗、可读，不要为了风格牺牲中文 |
| Mono（等宽字体） | 时间、编号、slot、BJT、archive id、run id、状态 | 用于 Y2K 终端感、档案感、信号系统感 |
| Display Font（展示字体） | 未来大标题或分享卡片标题 | 可以更 Y2K / acidic，但必须克制 |

原则：

- Mono 用于数据，不用于所有文本。
- Sans 用于专辑名和正文，保证中文可读。
- 可以探索更 Y2K / acidic 的 display font（展示字体），但只用于大标题、品牌字或分享卡标题。
- 不要把所有文字都做成故障字体。
- 网站正文要保持可读；分享卡可以更大胆。
- 中文不要强行模拟英文大写标签的密度，应优先保证行高、字重和换行。
- 字距适合 HUD label、slot label、BJT、archive id；不适合长段正文。

## 7. 背景纹理原则

背景应更偏酸性设计和低清数字材质，而不是干净科技背景。

可使用：

- scanline（扫描线）
- low-res noise（低清噪声）
- compression artifact（压缩痕迹）
- displaced grid（错位网格）
- slight chromatic offset（轻微色偏）
- signal band（信号带）
- telecode / ticker strip（电报码 / 信息带）
- dark rave flyer texture（Rave flyer 式暗纹）
- Y2K interface frame（Y2K 式界面框）

强度规则：

- 网站常态纹理要轻，像屏幕材质，不像装饰主体。
- Ambient 模式可以更强，像低频屏保、黑场、信号待机。
- 分享卡可以最强，因为它是静态输出物。
- 纹理不能遮挡专辑封面和文字。
- 不要让酸性纹理变成“看不清信息”的借口。

推荐结构：

网站常态：

```text
void-black base
low opacity noise
thin scanline
subtle grid
short signal sweep only during state transition
```

Ambient：

```text
black standby field
stronger scanline
slow signal band
displaced grid
ghost time / STANDBY
```

分享卡：

```text
void-black base
visible acid texture
time-window dividers
three signal lanes
small chromatic offsets
clear cover-safe zones
```

## 8. 页面与组件视觉原则

### HUD（顶部状态面板）

HUD 应像 club door control（地下入口控制台）、signal console（信号控制台）和 bootleg archive terminal（地下档案终端）的混合体。

原则：

- BJT Clock（北京时间时钟）是第一信息层级。
- 06:00 / 12:00 / 18:00 可以被视觉化为三段 gate（入口）或 signal windows（信号窗口）。
- Status Badge（状态徽标）要清楚，但不要过度发光。
- Marquee（滚动信息条）像地下电台信号带，不是公告栏。
- Language / Font 控件是工具区，视觉重量应低于时间和状态。
- 移动端优先保证不遮挡正文。

不要：

- 做成普通导航栏。
- 加大 logo 图或社交按钮堆。
- 做成医疗仪表或处方系统。

### Today Timeline（三时段线）

Today Timeline 是当前九张专辑结构的核心：三个时段，每个时段三张。

原则：

- 06:00 / 12:00 / 18:00 应像三道入口、三段信号窗、三张档案抽屉。
- locked（未解锁）状态可以有黑场、问号、低对比封面预影，但不要像错误。
- 当前时段应清楚，但不需要大面积高亮。
- 移动端横向滚动可以像滑过三段 signal rail（信号轨道）。

### Album Card（专辑卡片）

Album Card 不应像普通产品卡片。它更接近：

- Rave flyer（地下传单）的一块信息区。
- 唱片档案标签。
- 唱片箱里的编号卡。
- bootleg archive card（地下档案卡）。

原则：

- 封面是主视觉，必须真实、清晰、无遮挡。
- 卡片系统只负责秩序：slot、标题、艺人、年份、tag、外链。
- Slot Badge（Headliner / Lineage / Deep Cut）应像档案标签，不要变成潮流贴纸。
- hover（悬停）倾斜和 glow（发光）可以保留，但要克制。
- 缺封面时应使用故障信号占位图，不是普通灰块。

不要：

- 做成圆角很大的流媒体推荐卡。
- 给每张卡片加不同贴纸。
- 让装饰遮住封面或标题。

### Ambient / Standby（沉浸 / 待机模式）

Ambient 是方向正确的视觉资产。它应像无人操作时的低频屏保、Rave 前的黑场、信号待机。

原则：

- STANDBY、时间、TRIANGULUM DAILY 3 ALBUMS 是核心元素。
- 可以比常态页面更强地使用扫描线、错位网格、信号带、低清纹理。
- 动作要慢，不要像游戏加载页。
- 退出按钮必须清楚，尤其移动端 safe area（安全区）。

可升级方向：

- 三时段的微弱轨道线。
- 当天九张封面的极弱色偏反射。
- 分享卡可以借用 Ambient 的黑场和信号带语言。

### Project Info Dialog（项目说明弹窗）

Project Info 应像系统说明卡或地下档案终端的铭牌，不是营销弹窗。

原则：

- 解释反推荐算法、album as a unit、daily 9 albums、3 unlock windows。
- 视觉比 HUD 更安静，适合阅读。
- 可以用编号、细线、时间刻度组织信息。
- Repository Link（仓库链接）是辅助入口，不是主 CTA。

不要：

- 做成商业 BP。
- 做成产品落地页。
- 继续强化医疗 / treatment / dose 叙事。

### Archive（归档页）未来视觉原则

Archive 当前功能问题本阶段不处理。未来视觉上，它应承担 album archive（唱片档案）角色，而不是 Today 的旧版复制。

原则：

- Date List（日期列表）像 log rail（日志轨道）或档案索引。
- 每日记录可以像 archive receipt（归档收据）。
- 旧内容更安静，减少 glow。
- 大量日期时仍要可扫读。
- 归档是“唱片信号沉积”，不是失败状态，也不是图片瀑布流。

本阶段只保留这些原则，不把 Archive 功能修复列为当前实施重点。

## 9. 分享卡片方向

分享卡不是独立海报设计任务。分享卡是整体美术系统的输出物。必须先统一网站视觉语言，再把同一套视觉语言应用到分享卡。

第一版不要复杂。目标是每日生成一张可下载图片，不专门适配小红书、公众号、Instagram 或任何平台。

核心要求：

- 每日一张图，可下载。
- 不专门适配任何平台。
- 可以优先做竖版或正方形。
- 风格和网站统一。
- 按三个时段组织，而不是随便九宫格堆专辑。
- 信息短，封面清楚。

### 推荐第一版结构

```text
顶部：
TRIANGULUM DAILY 3 ALBUMS
日期 / BJT / DAILY 9 ALBUMS

主体：
三个时段分区：
06:00 — 三张专辑
12:00 — 三张专辑
18:00 — 三张专辑

每个时段：
三张封面 + 专辑名 + 艺人
信息尽量短

底部：
ANTI-FEED / ALBUMS ONLY / STATIC SIGNAL
或中文等价短句
```

### 两个可选模板方向

#### A. Vertical Signal Sheet（竖版信号单）

优先推荐第一版做这个。

结构：

```text
顶部品牌区
日期 / BJT / DAILY 9 ALBUMS
06:00 时段：三张封面 + 简短文字
12:00 时段：三张封面 + 简短文字
18:00 时段：三张封面 + 简短文字
底部短句：ANTI-FEED / ALBUMS ONLY / STATIC SIGNAL
```

特点：

- 三个时段从上到下排列，最符合 time-window release（时段释放）。
- 适合强调每日仪式。
- 文字和封面更容易保持清楚。
- 可以使用纵向扫描线、三段 signal lane（信号轨道）。

#### B. Square Signal Grid（方形信号网格）

作为后续可选，不建议第一版同时做。

结构：

```text
三行代表 06:00 / 12:00 / 18:00
每行三张封面
左侧或上方标记时段
底部放品牌和短句
```

特点：

- 更紧凑。
- 适合通用保存和缩略图。
- 风险是九张封面和文字会挤，需要严格控制信息量。

### 分享卡视觉规则

- 封面必须真实、清晰、无遮挡。
- 不放长介绍、不放推荐理由长段。
- 不做“今日必听”“宝藏专辑”“懂音乐的人都在听”这类推荐号语气。
- 不把九张封面简单堆成普通九宫格。
- 三个时段分区必须明显。
- acid green（酸绿色）用于品牌和时段结构，不要铺满整张图。
- magenta / cyan / yellow 只能作为小面积故障偏移或细线。
- 压缩噪声、扫描线、错位网格可以更明显，但不能影响专辑名和艺人名。

推荐短句：

- `ANTI-FEED`
- `ALBUMS ONLY`
- `STATIC SIGNAL`
- `DAILY 9 ALBUMS`
- `3 WINDOWS / 3 ALBUMS EACH`
- `BJT 06:00 / 12:00 / 18:00`
- 中文：`反信息流`
- 中文：`只按专辑听`
- 中文：`每日九张 / 三个时段`

## 10. 美术资源清单

这些资源不一定马上生成。本文只定义方向和优先级。

### P0：下一阶段优先制作

1. Texture Pack（纹理包）
   - 酸性噪声、扫描线、错位网格、低清数字纹理。
   - 网站常态、Ambient、分享卡都能复用。
   - 必须有强度分级：light / standby / share card。

2. Slot Window System（三时段视觉标记系统）
   - 06:00 / 12:00 / 18:00 三个时段的视觉标记。
   - 可表现为三段 gate、三条信号轨、三点三角、三格档案窗。
   - 同时服务 HUD、Today Timeline、分享卡。

3. Share Card Template（每日分享卡模板）
   - 第一版优先 Vertical Signal Sheet（竖版信号单）。
   - 按三个时段组织九张专辑。
   - 明确封面位置、标题区、日期区、BJT、底部短句。

4. Brand Mark（品牌标记）
   - Triangulum 的简化标记。
   - 可由三点、三角、三时段窗口、信号轨构成。
   - 用于 HUD、favicon、分享卡角标。

5. No Cover Placeholder（无封面占位图）
   - 无封面时的故障信号占位图。
   - 方向是 signal lost / no cover signal，不是普通灰块。
   - 需要适配 Album Card 和分享卡。

### P1：网站视觉升级时制作

6. HUD Micro System（HUD 微型系统）
   - 三时段刻度、状态分区线、弱化后的工具控件层级。

7. Ambient Standby Background（待机背景素材）
   - 更统一的黑场、扫描线、低频信号带。

8. Archive Visual Kit（归档视觉组件）
   - 日期索引、archive receipt、run id、旧记录水印。
   - 当前只做视觉原则，不处理功能问题。

9. Cover Treatment Rules（封面处理规则）
   - 封面阴影、边框、低强度反光、封面色提取边界。

10. Share Card Export Safe Area（分享卡输出安全区）
   - 只服务“可下载图片”的稳定排版，不做平台专门适配。

### P2：稳定后再考虑

11. Motion Spec（动效规范）
   - hover、viewer open、slot transition、ambient drift 的节奏。

12. Favicon / App Icon Set（站点图标组）
   - 基于 Brand Mark 生成多尺寸图标。

13. OG Image Variant（链接预览图）
   - 可复用 Square Signal Grid，但不是当前重点。

14. Mini Diagram Assets（小型流程图）
   - 用于 Project Info：music data -> daily selection -> static site。

15. Poster Variant（海报变体）
   - 只有分享卡系统稳定后再做。

## 11. 后续实施顺序

### Phase 1：修订 art direction

目标：确定地下 Rave / Y2K / 酸性故障方向。

输出：

- 本文档作为方向基准。
- 明确 daily 9 albums / 3 unlock windows / 3 albums each。
- 弱化观测站、医疗、处方、胶囊、解药方向。

验收标准：

- 不再把项目描述成普通音乐推荐站。
- 不再把视觉核心放在医疗或慢速观测站。
- 能清楚指导后续视觉资产制作。

### Phase 2：做美术资源草案

目标：先做可复用资源，不急着改完整页面。

输出：

- Texture Pack（纹理包）。
- Slot Window System（三时段视觉标记系统）。
- Share Card Template（每日分享卡模板）。
- Brand Mark（品牌标记）。
- No Cover Placeholder（无封面占位图）。

验收标准：

- 黑底酸绿识别稳定。
- 三时段结构清楚。
- 分享卡不是独立海报，而是网站视觉系统的延伸。

### Phase 3：网站整体视觉升级

目标：把统一视觉语言应用到现有 UI。

重点：

- 背景纹理。
- HUD。
- Ambient。
- Album Card。
- Project Info 的说明卡气质。

暂不做：

- Archive 功能修复。
- 域名、服务器、留言、播放器、专辑长介绍、后端。

验收标准：

- 网站和分享卡看起来属于同一套系统。
- 专辑封面仍是主视觉。
- 故障、酸性、Rave 感不影响可读性。

### Phase 4：实现每日分享卡下载功能

目标：先做一个简单但风格统一的版本。

第一版：

- 一张可下载图片。
- 优先 Vertical Signal Sheet（竖版信号单）。
- 三个时段从上到下排列。
- 每个时段三张专辑。
- 无平台专门适配。

验收标准：

- 不依赖人工微调也能生成。
- 长标题、无封面、低清封面仍可读。
- 风格和网站统一。

## 最终判断

Triangulum 现阶段最适合的 art direction 是 **Acid Rave Signal Archive（酸性 Rave 唱片信号档案）**。

它应该像一个地下酸性唱片信号系统：黑底、酸绿、Y2K 故障、低清数字纹理、三段时窗、反信息流、反推荐算法。它每天按北京时间 06:00 / 12:00 / 18:00 释放九张专辑，让用户重新以 album as a unit（专辑为单位）听音乐。

网站负责建立系统、时段和档案秩序；每日分享卡负责把同一套视觉语言输出成一张可下载图片。专辑封面是每天变化的主视觉，系统美术只负责提供清晰、克制但有地下能量的黑色信号框架。
