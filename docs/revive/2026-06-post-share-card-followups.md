# 2026-06 Post Share Card Follow-ups

## Deferred

1. 移动端实机验证分享卡下载暂时搁置。
2. 搁置原因：当前优先处理 Offline / Archive / Debug / CI 小修。
3. 后续恢复时需要验证：移动端 Share Card 入口、弹窗、下载 PNG、不同浏览器下载行为。
4. 本次不再重复确认 GitHub Pages 每日发布链路，因为用户已手动验证发布成功且功能正确。

该事项状态为 deferred / 暂缓，不是失败，也不是阻塞。

## Static Archive Boundary

GitHub Pages 不能在用户访问时动态写入或储存新数据。

GitHub Pages 可以托管每日构建产出的静态历史 JSON。因此“最近三天历史查看”不需要买服务器、不需要数据库、不需要后端。

实现边界是：daily build 在构建时恢复已发布的静态 archive/index seed，生成当天数据后再输出最近三个唯一 archive 日期。前端 Archive 页面只读取 `data/index.json` 与 `data/archive/...json`，并按最近三个有 archive 数据的日期展示；如果实际可用数据少于三天，就展示实际可用数量并给出空状态或单日 fallback。

Today 页面仍按当前 BJT 解锁状态裁剪，不泄露今日未来时段。Archive 读取的是已经归档的过去静态 JSON，不受今日 unlock 限制。
