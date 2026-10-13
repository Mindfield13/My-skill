# 可分离组件架构

在 Trigon Framework 中新建组件时遵循"**可分离但不孤立**"原则。

## 架构原则

- **可分离**: 整个组件目录拎出来就能独立跑（`standalone.js` + 独立 venv + 独立端口 + 独立数据目录）
- **不孤立**: 嵌入 Framework 时复用壳的 preload/shell/主题系统，但**不引用其他组件的代码或数据**
- **借鉴概念，不复制文件**: 读 Modex/Mrite 学设计模式（管道引擎、skill 注册表、模板解析），但重新实现

## 目录结构

```
src/apps/<id>/
├── manifest.json              # 嵌入 Framework 的元数据
├── index.html                 # 加载屏（启动后端 → 导航到后端 URL）
├── main.js                    # 主进程 handler（spawn/stop Python 进程）
├── standalone.js              # 独立运行入口（electron standalone.js）
├── backend/                   # Python 核心（自包含 venv）
│   ├── main.py                # FastAPI 入口
│   ├── config.py              # 可分离路径设计（IS_EMBEDDED 检测）
│   ├── requirements.txt       # 仅自己需要的依赖
│   ├── engine/                # 核心引擎
│   ├── templates/             # 模板（动态 resolve() 生成步骤）
│   ├── skills/                # 技能注册表
│   ├── figures/               # 图表模板库
│   └── services/              # LLM 客户端等
├── frontend/                  # 前端（原生 JS，不打包）
│   ├── index.html
│   ├── css/app.css            # 自包含设计令牌（不依赖 tokens.css）
│   ├── js/app.js
│   └── vendor/                # 独立 vendor
└── scripts/                   # 部署脚本
```

## 可分离路径设计（config.py）

```python
IS_EMBEDDED = os.environ.get("CUMCM_EMBEDDED") == "1"
ROOT = Path(__file__).resolve().parent.parent

if IS_EMBEDDED:
    DATA_DIR = ROOT.parent.parent.parent / "cumcm_data"  # Framework/../cumcm_data/
else:
    DATA_DIR = ROOT.parent / "cumcm_data"                # 独立运行时同级
```

关键：**所有路径只依赖自身，不引用 Framework 其他目录**。嵌入时数据放 Framework 同级，独立时放组件同级。

## 独立运行入口（standalone.js）

```javascript
// 用法：electron standalone.js
// 不依赖 Trigon 壳，直接以独立 Electron 窗口运行
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

const ROOT = __dirname;
const BACKEND_DIR = path.join(ROOT, 'backend');
const PORT = 18089;

// 启动 Python 后端 → 等待健康 → 打开 BrowserWindow → loadURL
```

## 不干扰原则

| 维度 | 做法 |
|------|------|
| Python 环境 | 自己的 venv（`backend/.venv/`），不共享 Modex 的 `runtime/python/` |
| 端口 | 自己的端口（如 18089），不与 Modex 的 18088 冲突 |
| 数据目录 | 自己的数据目录，不与 Modex 的 `MHAgent/` 或 Mrite 的 `mrite/` 冲突 |
| 依赖 | 自己的 `requirements.txt`，只装需要的包 |
| 前端 | 原生 JS，不引用其他组件的打包产物 |

## 核心引擎模式

### 管道执行引擎
- 步骤序列 = 串行执行的 Step 列表
- 每步有 skill_name, params, model, quality, checkpoint 标志
- 检查点系统：每步完成暂停，等待用户确认（continue/modify/rollback/stop）
- 支持异步执行（asyncio.create_task）

### 模板解析模式
- 模板基类 `CompetitionTemplate` 有 `resolve(analysis, params) → list[Step]`
- 按赛题分析结果动态生成步骤，不是固定列表
- 不同题型（物理/优化/数据驱动）自动选择不同建模 skill 组合

### 技能注册表模式
- 文件系统自动发现：扫描 `skills/` 目录下的所有 `.py` 文件
- 按 `Skill` 子类自动注册，id 作为唯一标识
- 热插拔：加新 skill 文件即可，无需重启注册逻辑

### 模型编排器模式
- 每步可指定不同模型（写作用强模型，审稿用不同模型防自审）
- 推理强度分级：low/medium/high/xhigh 映射到不同质量分数
- 自动降级：无匹配模型时退回到最高质量模型

### 图表模板库模式
- FigureTemplate 基类：render(data, style, output_dir) → FigureOutput
- 15+ 内建图表类型：line, multi_line, bar, grouped_bar, scatter, heatmap, boxplot, radar, pareto_front, convergence, histogram, contour, confusion_matrix, roc
- 智能选择：auto_render 按 data_type 自动匹配最佳图表模板
- 国奖配色板：nature, ieee, apple, cumcm 四套调色板