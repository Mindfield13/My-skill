# M Ultra 工作流引擎实现细节（M2/M3，2026-08-16 实测）

项目：`E:\Project\M Ultra\M-Ultra-数模`，后端 `src/backend/workflow.py` + `main.py`。

## 任务目录结构与 task.json 状态机

```
data/tasks/<ASCII_id>/
├── task.json           # {name, template, status, current_step, steps:[{id,name,desc,status,updated,error?}]}
├── 题目/  数据/         # 附件（.txt/.csv→数据；.pdf/.docx→题目）
├── 求解/
│   ├── 题目分析.md     # 读题产物（LLM 结构化分析）
│   ├── 求解计划.md     # 求解计划产物（六章）
│   ├── 问题一/ 问题二/… # 每问：
│   │   ├── 问题一_求解.py   # LLM 生成 + 修复循环落盘
│   │   ├── 图片/*.png       # 图（中文名，4-6 张）
│   │   └── 结果/*.csv       # 结果表（中文名）
├── 论文/  输出/
│   └── 输出/workflow.log    # 追加日志，progress 读尾 60 行
```

状态流转：created → running（步骤级更新）→ done | error（WorkflowError）。`stop_flag` 导致 error("已手动停止")。

## 断点续跑实测

- M2 任务（读题+求解计划 done）重新 run → 日志：
  `── 步骤已完成，跳过：读题` / `── 步骤已完成，跳过：求解计划` → 直接进逐题求解
- 实现要点：`start()` 先快照 existing 状态，done 保留；`_run_loop` 每步检查 `_step_is_done()`。

## 失败修复循环实测（真实案例）

测试任务 `20260816_221442_es8b`（5 行销售额 CSV）：
- 问题一第 1 轮：代码生成(7532字符) → exit=1（`Empty DataFrame`，CSV 读取失败）→ stderr 回灌 → 第 2 轮修复成功（8569字符）
- 问题二第 1 轮失败 → 第 2 轮成功
- 全程 2 分 09 秒完成两问，各产出图+CSV（问题一 1 图 3 CSV；问题二 3 图 3 CSV）
- vision 检查图：中文标题正常（Microsoft YaHei rcParams 生效）、2x2 子图、R²/RMSE 指标齐全，质量 9.5/10

教训：**修复循环是必须的** —— 首轮生成代码几乎必然有小 bug（列名/编码/路径），3 轮足够。

## API 形状（供前端对接）

```
POST /api/tasks/{id}/run      → {started: bool}（running 时 false）
POST /api/tasks/{id}/stop     → {stopping: true}
GET  /api/tasks/{id}/progress → task.json + {log: [末尾60行]}
GET  /api/workflow/steps      → {steps:[{id,name,desc}], active:[...]}
```

## LLM prompt 关键设计

- 读题：system=读题规则+读数据规则（rules-library/common/题目|数据/*.md）+ 明确输出格式（五段结构化）；user=题目/数据提取文本（每文件截断 4000 字符）
- 求解计划：system=计划模板（rules-library/solve/求解计划模板.md，源自 Mrite-main Skill）+ 六章输出格式
- 逐题求解：system=代码铁律（见 SKILL.md 主文）；user=题目分析 2500 字符 + 该题计划段落 2200 字符 + 数据绝对路径列表
- 提示词素材来源：`rules-library/`（common/题目/读题规则.md、common/数据/读数据规则.md、common/主引导.md、solve/求解计划模板.md）—— 文档类内容资产可自由复用（非代码）

## 状态相关的小坑

- `_find_problems` 曾用 `key not in [x[0] for x in found]`（对字符串取首字符的脆弱写法），已简化为 `key not in found`
- 前端 `renderFiles(task.tree)` 定义后忘记调用 → 产物文件区空白；初始渲染必须显式调用
- 面板 id 命名：index.html 与 app.js 的 PANELS 数组必须一字不差（曾 welcomePanel vs homePanel 静默失败）