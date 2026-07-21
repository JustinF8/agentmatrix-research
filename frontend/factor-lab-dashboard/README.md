# Factor Lab 因子库前端看板

原生 HTML + JavaScript + CSS 的**纯静态**因子研究看板，**无需构建步骤**（No build step）。
直接由 GitHub Pages 托管，离线只读演示模式即可运行；接上后端 API 后变为实时模式。

## 功能特性

| 模块 | 功能 |
|------|------|
| 📚 **因子库** | 因子列表浏览、搜索、筛选、排序 |
| 📊 **因子详情** | 单因子分析、IC/IR 指标、复现状态 |
| 📈 **因子看板** | 因子统计分析与可视化 |
| 🤖 **智能体** | AI 研究智能体（因子研究、扫描、验证、推理） |
| 🔧 **服务注册** | 服务管理与任务编排 |

## 本地运行（无需安装依赖）

直接用浏览器打开 `index.html` 即可；或起一个静态服务器：

```powershell
cd frontend/factor-lab-dashboard
python -m http.server 5173
# 浏览器访问 http://127.0.0.1:5173
```

页面内置 **云演示模式（CLOUD_DEMO_MODE）**：当访问域名以 `github.io` 结尾，或 URL 带 `?demo`
参数时，自动忽略本地后端配置，改用打包的 `./data/demo-factor-library.json`，Agent 任务只读。

## 接入实时后端

把页面部署到任意静态托管后，加 `?api=` 参数即可切换到实时模式：

```
https://<你的Pages地址>/?api=https://<你的后端地址>
```

后端为仓库内 `backend/factor_lab_api.py`（Flask，默认 `http://127.0.0.1:8012`）。
可在 Render / Fly.io 等平台部署后端（见仓库根 `render.yaml`），并配置
`FACTOR_LAB_PUBLIC_ORIGIN` 以放行前端跨域。

## GitHub Pages 自动部署

推送 `frontend/factor-lab-dashboard/**` 或工作流文件到 `main` 分支时，
`.github/workflows/pages-factor-lab-dashboard.yml` 自动构建并发布到 GitHub Pages。
站点地址：`https://<用户名>.github.io/<仓库名>/`

## 目录结构（实际）

```
factor-lab-dashboard/
├── index.html                      # 入口 HTML（按序加载 config.js → app.js → styles.css）
├── config.js                       # API 地址配置（FACTOR_LAB_API_HOST）
├── app.js                          # 看板主逻辑（含 CLOUD_DEMO_MODE 演示回退）
├── styles.css                      # 样式
├── data/
│   └── demo-factor-library.json    # 打包的演示因子库（只读 demo 模式数据源）
└── assets/                         # 静态资源（logo 等）
```
