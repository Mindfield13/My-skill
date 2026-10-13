# M Ultra 评审与修改功能（M6，2026-08-17）

## 新 UI：评审面板 + 修改模式

左侧导航新增「评审」面板（`js/views/review.js`，app.js PANELS 加 'review'），任务详情「✎ 修改」模式（tasks.js）。

### 评审页布局（自上而下）
1. 规范参考折叠面板：MRITE_2.50 三栏（解题逻辑 / 模板要求 / 使用规范），从 `Mrite-main/Skill/CLAUDE.md` 提炼
2. 每任务卡片：
   - 评估进度条 + 得分（passed/total → 百分比，颜色 绿≥80 / 蓝≥50 / 红）
   - 检查项双列：题目分析、求解计划、每题求解（图/CSV 计数）、论文源文件、PDF 编译
   - 📋 评估要求 details：textarea + 保存要求按钮
   - ✎ 修改模式：STEP_PRODUCTS 匹配产物文件 → 🗎 编辑按钮（openEditModal 弹窗）
   - 底部 ▶ 单步重跑按钮（read_problem/solve_plan/solve/paper/compile）+ 任务详情跳转

## 后端新增 API（src/backend/main.py）

| 端点 | 作用 |
|------|------|
| `GET  /api/tasks/{id}/evaluate` | 评估：检查 题目分析/求解计划/每题图数/论文tex/PDF 存在性 |
| `POST /api/tasks/{id}/step/{step_id}` | 单步重跑：校验 step_id ∈ STEPS，engine.is_running() 防并发，run_single() |
| `GET/PUT /api/tasks/{id}/requirements` | 评估要求读写（存 task.json `eval_requirements`） |
| `PUT  /api/tasks/{id}/file` | 写文件（修改模式编辑产物）：{rel, content}，rel 需 is_relative_to 校验 |

api.js 对应：`evaluateTask / runStep / saveRequirements / getRequirements / writeTaskFile`

## WorkflowEngine 单步执行

```python
def is_running(self): return self.thread is not None and self.thread.is_alive()

def run_single(self, step_id):
    # 只重置该步骤为 pending，其余不动
    for s in meta["steps"]:
        if s["id"] == step_id: s["status"] = "pending"
    meta["status"] = "running"; meta["current_step"] = step_id
    self.thread = threading.Thread(target=self._run_single_thread, args=(step_id,), daemon=True)
    self.thread.start()

def _run_single_thread(self, step_id):
    # 校验 step 存在且 in ACTIVE → _set_step(running) → handler() → _set_step(done)
    # status = done 若所有步骤 done，否则 created
```

## 关键坑位

### 1. api.js 添加方法覆盖旧导出 → 主页崩溃
为加 evaluateTask/runStep 时把 `listTemplates` **替换**了，主页 `Views.home` 调 `API.listTemplates()` 抛 `is not a function`，整页显示红色"加载失败"。
**规则**：扩展 api.js 只追加不替换；加完 grep 一遍仍被引用的旧方法名。

### 2. 后端文件树路径分隔符（Windows `\`）
`get_task` 的 tree 用 `str(f.relative_to(d))` → Windows 反斜杠（`求解\问题一\x.py`）。前端按 `/` 匹配（STEP_PRODUCTS、STEP_FILE、fileMap）全部落空 → 编辑产物区块不渲染、修改模式无按钮。
**规则**：前端对后端路径统一 `f.path.replace(/\\/g, '/')` 后再 includes/过滤（tasks.js renderSteps 的 fileMap、review.js renderEditableFiles 都中招过）。

### 3. 写作页是主从布局，不是内联 toggle
写作页 `#wp-files`（左）→ `#wp-preview`（右）。曾改成点击文件内联展开，用户反馈"论文内容不显示"。
**规则**：写作页保持"左选文件 → 右侧面板显示"（同文件再点收回），任务详情/文件页用内联 toggle。

### 4. components.js 暴露 `UI.openModal`/`UI.closeModal`（不是 `UI.modal`）
review.js 首次写 `UI.modal(...)` 会静默失败，用 `UI.openModal(html)` + 弹窗内按钮 `UI.closeModal()`。

### 5. 分段控制器（segmented）必须绑 click
按钮静态 active 类渲染后必须手动绑 click 切换（settings.js 协议切换、review.js 都如此），否则点不动。

## 验证要点
- 主页无"加载失败"（api.js 导出完整）
- 评审页：规范参考三栏、评估 6/6、评估要求 textarea、🗎 编辑按钮（题目分析/求解计划/求解代码 .py/论文章节 .tex）、▶ 单步重跑
- 修改模式（任务详情 ✎ 修改）→ 每步骤出「🗎 编辑产物 / ▶ 重跑此步」
- 编辑弹窗：读文件 → textarea → 保存（writeTaskFile）→ 可重跑该步骤