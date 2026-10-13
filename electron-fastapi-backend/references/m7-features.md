# M7：AI 评估 / 多任务并行 / 多模型交火 实现细节

M Ultra 数模工作台 M7 实测记录（2026-08-17）。属于 `electron-fastapi-backend` 的扩展实现。

## 1. AI 评估（evaluate.py 新模块）

### 素材收集
- 论文 `论文/论文.tex`（clip 8000）
- `求解/题目分析.md`、`求解/求解计划.md`
- 求解产物摘要 `_collect_solve_summary`：遍历 `求解/问题*` 目录，收集 图片/结果 数量 + 每个结果目录前 2 个 CSV/TXT 的头 600 字符
- 用户评估要求 `_collect_requirement_text`：
  - task.json 的 `eval_requirements` 文本
  - `评估要求/` 目录文件：`.md/.txt` 直接读；其他格式（PDF/DOCX/xlsx）走 `extract.extract_file(f)` → **取 `["text"]` 字段**（extract_file 返回 dict）

### LLM prompt（结构化 JSON 输出）
system 强制输出合法 JSON：
```json
{
  "scores": [{"key":"逻辑","score":0-100,"comment":"具体意见"},
             {"key":"模型",...},{"key":"结果",...},{"key":"图表",...},{"key":"规范",...}],
  "overall": 0-100,
  "summary": "总评 2-4 句话",
  "weaknesses": ["问题1", ...最多4],
  "suggestions": ["改进1", ...最多4]
}
```
维度固定 5 个：逻辑/模型/结果/图表/规范（`DIMENSIONS` 常量）。没给评估要求时用竞赛通用标准。

### 解析容错
```python
text = raw.strip()
m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)  # 剥代码块
if not m: m = re.search(r"\{.*\}", text, re.S)                  # 兜底
json.loads 失败 → 抛 LLMError（前端显示原始输出前 300 字符）
scores 缺维度 → 自动补 {score:0, comment:"（未评分）"}
score 夹在 0~100
```

### 落盘
- `评审/评估报告.md`（Markdown：时间/模型/综合分/维度表/总评/问题/建议）
- `评审/eval_result.json`（完整 JSON，`get_eval_report` 优先读它，回退 task.json 的 `ai_eval` 摘要）
- task.json 只写摘要 `ai_eval: {overall, evaluated_at}`（前端列表页轻量读取）

### API（main.py）
```python
_eval_jobs = {}; _eval_lock = threading.Lock()
POST /api/tasks/{id}/ai-evaluate          # 409 若该任务评估中
GET  /api/tasks/{id}/ai-evaluate/status   # {status, detail, result, error}
GET  /api/tasks/{id}/ai-evaluate/report   # {evaluated, ai_eval}
```

### 前端（review.js）
- `loadAiEval(card, tid)`：先读 report → 有结果渲染 hive()（综合分 + 5 维度卡片 + 总评/问题/建议），无结果渲染 "🤖 AI 评估本任务" 按钮
- 点击 → `API.aiEvaluate` → `setInterval(1s)` 轮询 status → done 后 `loadAiEval` 重渲染
- `hive(r)` 渲染：overall 大字 + 进度条 + 每维度卡片（分数条 + comment + 按 80/60 分档颜色）

## 2. 多任务并行

- 现状已支持：`_engines` dict + 每任务独立 engine/thread/目录
- 补充：`WorkflowEngine._meta_lock = threading.RLock()` 保护 `_load_meta/_save_meta`；`_save_meta` 原子写（.json.tmp + replace）——防同时 run/run_single/progress 写坏 task.json
- RLock 而非 Lock：`_set_step` 里 `_load_meta()` → 修改 → `_save_meta()` 会嵌套获取
- 压测脚本模式：双 WorkflowEngine × 20 轮并发写，断言 0 错误 + 实例独立（`e1 is not e2`、`stop_flag` 不同）

## 3. 多模型交火

### config（config.py）
```python
"crossfire": {"enabled": False, "reviewer": "", "rounds": 2, "threshold": 80}
def get_reviewer_profile():
    # 1. reviewer 名匹配
    # 2. 自动选非主模型（name != active.name 且 base_url && model）的第一个
    # 3. 全无 → profiles[0]
```

### 审核 JSON
```python
{"score": 0-100, "pass": true/false, "issues": ["..."], "suggestions": ["..."]}
```
解析失败 → `{score:0, pass:False, issues:["审核输出无法解析，请人工核查"]}`（不中断工作流）

### 三个方法
- `_crossfire_cfg()`：读 config
- `_reviewer_client()`：审核者 LLMClient（若审核者==主模型 → None，交火退化为不用）
- `_review_content(purpose, content, context_text)`：单次审核
- `_crossfire_text(purpose, system, user, content, context_text)`：文本交火（paper 用）
- `_crossfire_solve(prob, prob_dir, script, analysis, plan, data_files)`：代码交火（solve 用），含重跑验证

### 记录
- solve 交火：`问题X/交火记录.md`（每轮 得分/问题）
- paper 交火：`论文/交火记录.md`

### 设置页 UI（settings.js）
- 交火开关 `.cf-switch`（独立类，详见 SKILL.md UI 布局偏好）
- 审核者下拉（profiles 非主模型的那些，带 `（主模型）` 标注）
- 轮数 select 1-3、阈值 number
- 保存时 `collectProfiles()` + crossfire 一起提交

## 4. 前端三方对照
- `hive()` 评分卡片：分数条颜色 `>=80 green / >=60 accent / else red`
- 异步任务三段式按钮：启动（POST）→ 轮询（GET status 1s）→ 完成重渲染（GET report / status.result）