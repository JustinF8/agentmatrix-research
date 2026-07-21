# Factor Lab 因子库前端看板

基于 Vue3 + Vite 的因子研究看板前端界面，展示 Factor Lab 本地 Flask 接口返回的因子库状态。

## 功能特性

| 模块 | 功能 |
|------|------|
| 📚 **因子库** | 因子列表浏览、搜索、筛选、排序 |
| 📊 **因子详情** | 单因子分析、IC/IR 指标、复现状态 |
| 📈 **策略回测** | 策略回测配置与结果展示 |
| 🤖 **智能体** | AI 研究智能体（因子研究、扫描、验证、推理） |
| 🔧 **服务注册** | 服务管理与任务编排 |
| 📈 **因子看板** | 因子统计分析与可视化 |

## 启动方式

### 1. 启动后端 API

```powershell
python backend/factor_lab_api.py
```

默认接口地址：`http://127.0.0.1:8012`

### 2. 启动前端开发服务器

```powershell
cd frontend/factor-lab-dashboard
npm install
npm run dev
```

访问地址：`http://127.0.0.1:5173`

### 3. 构建生产版本

```powershell
npm run build
```

## 技术栈

- **框架**: Vue 3 + Vite
- **UI**: Element Plus
- **图表**: ECharts
- **样式**: TailwindCSS

## 目录结构

```
factor-lab-dashboard/
├── index.html          # 入口 HTML
├── package.json        # 项目配置
├── vite.config.js      # Vite 配置
├── tailwind.config.js  # TailwindCSS 配置
├── src/
│   ├── main.js         # 应用入口
│   ├── App.vue         # 根组件
│   ├── components/     # 公共组件
│   ├── views/          # 页面视图
│   ├── api/            # API 接口
│   └── styles/         # 样式文件
└── public/             # 静态资源
```
