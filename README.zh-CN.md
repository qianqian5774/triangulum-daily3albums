# Triangulum Daily

[English](./README.md) · [正式站点](https://triangulumdaily.space/)

Triangulum Daily 是每日推荐 **九张专辑**的音乐发现站点，每次开放三张。产品围绕有限的每日访问节奏设计。

## 每日节奏

所有产品时间均为北京时间（Asia/Shanghai）。

| 北京时间 | 可见专辑 |
| --- | ---: |
| 00:00–07:59 | 离线 |
| 08:00–12:29 | 3 张 |
| 12:30–15:59 | 6 张 |
| 16:00–23:59 | 9 张 |

## Record Shop

正式首页 `#/` 从可交互的 3D 唱片店外开始。通过实体门进入店内，可浏览今日唱片和近期历史；选择唱片会在店内打开 Treatment Viewer。`#/today` 和 `#/archive` 是辅助数据页面。

## 静态生产站点

Python 生成器在部署前准备每日期刊。**Build and Deploy Pages (Daily)** 将 React/Vite 界面、静态 `data/today.json`、`data/index.json`、历史 JSON 和同源封面资源发布到 GitHub Pages。访客浏览器只读取这些文件，不生成推荐，也不调用音乐服务 API 获取应用数据。封面不可用时有本地回退。

## 本地开发

需要 Python 3.11+、Node.js `>=22 <25` 和 npm。先用 `python -m venv .venv` 创建并激活虚拟环境，再安装项目与 UI 依赖：

```bash
python -m pip install -e ".[test]"
npm --prefix ui ci
npm --prefix ui run dev
```

真实数据构建需要按 [`.env.example`](./.env.example) 配置构建期凭据，再运行 `daily3albums build --verbose --out _build/public` 和 `python scripts/self_check.py --path _build/public`。常用检查是 `python -m pytest` 与 `npm --prefix ui test`。

## 项目文档

- [运行手册](./docs/runbook.md)：验证与发布命令。
- [Foundation](./docs/foundation/README.md)：当前架构、数据与发布契约。
- [设计规范](./docs/design/README.md)：Record Shop 的视觉与交互契约。
- [性能说明](./PERFORMANCE.md)：稳定的性能做法与测量入口。
- [Agent 指引](./AGENTS.md)：仓库工作规则。
