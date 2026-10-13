# M Ultra AI 辅助修改 + 模型 Profile（M6，2026-08-17 晚）

用户 6 项需求收敛到：修改模式必须集成 AI（非单纯手动）、独立成页、写作页可直改、PDF 应用内预览、导航重排、模型多配置。

## 导航重排 + 修改独立页

- 最终顺序：`主页(home) / 任务(task) / 修改(modify) / 写作(write) / 评审(review) / 扩展(ext) / 设置(settings)`
- 原「文件」页（view）整个移除：index.html 删按钮 + `viewPanel` + `views/view.js` 引用；app.js PANELS/PAGES 同步。改动导航/面板时三处必须一起改：index.html 按钮 + index.html panel div + app.js PANELS/PAGES。
- `js/views/modify.js`：任务卡片按 STEP_PRODUCTS（题目分析 .md / 求解计划 .md / 求解代码 .py / 论文章节 .tex）分组渲染 🗎 编辑按钮 + 底部 ▶ 单步重跑（read_problem/solve_plan/solve/paper/compile）。

## AI 辅助修改 API（核心）

```
POST /api/tasks/{id}/ai-edit
body: { rel, instruction, extra_context? }
→ { ok, content: 新文件内容 }   # 不落盘！前端确认后 PUT file 保存
```

实现要点（src/backend/main.py task_ai_edit）：
- 校验 rel 在任务目录内（is_relative_to）、文件存在、非二进制（.png/.jpg/.pdf/.xlsx/.otf 拒绝）
- 上下文 = 任务 题目分析.md[:1500] + 求解计划.md[:1500] + 当前文件内容[:6000] + 用户修改要求
- system prompt：只改相关部分、输出完整新文件内容不省略、按文件类型守规范（tex→可编译/图宽0.8/禁newpage；py→可运行/编码字体配置；md→保持结构）
- 返回前剥离 ``` 围栏（若 LLM 裹了代码块）
- LLM 失败 → 502；异常走 HTTPException 而非裸抛

前端统一弹窗 `window.ModifyUI.openEditModal(tid, rel)`（modify.js 定义，tasks.js/review.js 复用）：
- 顶部 `🤖 AI 修改` 按钮 + 修改要求 textarea（#ai-instr）
- 主体 `#ai-content` textarea（可手动编辑）
- `💾 保存` → `API.writeTaskFile(tid, rel, ta.value)`
- AI 返回后状态提示「✅ 已生成新内容（检查后点保存）」，**不自动保存**（用户确认制）

api.js：`aiEdit(id, rel, instruction, extraContext)`、`writeTaskFile(id, rel, content)`。

## 写作页 tex 直改 + PDF 预览

- 右栏布局：`#wp-preview`（只读预览）+ `#wp-editor`（textarea，隐藏）+ `#wp-save`/`#wp-ai` 按钮 + `#wp-ai-instr` + `#wp-ai-status`
- 点 .tex/.md → switchToEditor（显示 textarea，可编辑）；点图片 → switchToPreview(img)；点 PDF → iframe data URL
- 保持主从布局（左文件列表 → 右编辑），**不是**内联 toggle——用户明确反馈写作页要点开即显示内容
- PDF 应用内预览：后端 `GET /api/tasks/{id}/file` 对 .pdf 输出 `{content: base64, mime: "application/pdf"}`；前端
  `<iframe src="data:application/pdf;base64,${b64}#page=1" style="height:520px">` + 兜底「用系统阅读器打开」按钮（mUltra.openPath）

## 模型 Profile 管理

config.py：
```python
DEFAULT_PROFILES = [{name, enabled, protocol, base_url, api_key, model, temperature, max_tokens}, ...]
DEFAULTS = {"profiles": DEFAULT_PROFILES, "latex": ..., "app": ...}
def get_active_profile():  # 返回第一个 enabled，否则 profiles[0]
def save_config(cfg):      # 兼容迁移：入参含旧 "model" 字段 → 转成单个 profile
```
- 消费方：workflow.py `_llm()` 和 main.py `model_test` 都改为 `config.get_active_profile()`
- settings.js：`renderProfile(p, i)` 卡片（启用圆钮互斥：点某卡 enabled → 其他全 false）、添加/删除（至少保留 1 个）、温度滑块联动、协议分段切换

## 后端新 API 汇总（M6）

| 端点 | 作用 |
|------|------|
| `POST /api/tasks/{id}/ai-edit` | AI 改写文件（LLM，返回不落盘） |
| `PUT  /api/tasks/{id}/file` | 写文本文件（修改保存） |
| `PUT/GET /api/tasks/{id}/requirements` | 评估要求存取（task.json eval_requirements） |
| `POST /api/tasks/{id}/step/{step_id}` | 单步重跑（run_single） |
| `GET  /api/tasks/{id}/evaluate` | 评估得分（文件存在性检查） |

## 坑位

- **MSYS curl 中文 body 编码错误**（`{"detail":"There was an error parsing the body"}`）：curl -d 内联中文在 git-bash 会坏；用 `--data-binary @文件`（JSON 文件，Windows 路径如 `C:/Users/.../Temp/x.json`）测后端 API
- **api.js 只追加不替换**：为加新方法"替换"掉 `listTemplates` 会整页红色"加载失败"（主页调它）
- **路径统一正斜杠后匹配**：后端 tree 文件路径带 `\`，前端 STEP_PRODUCTS/fileMap 一律 `f.path.replace(/\\/g, '/')` 后再 includes
- **分段控制器/Profile 卡片**：全部是 JS 重新渲染事件绑定（collectProfiles → renderProfilesList 后重绑），不是一次性绑定