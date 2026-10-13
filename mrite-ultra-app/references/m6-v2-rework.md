# M6 第二轮重构全记录（2026-08-17 深夜，6 项需求）

用户 6 项需求（对应方案）：
1. 评审页删除"修改模式"组件 → 评审专注评估（无 renderEditableFiles/STEP_PRODUCTS 残留）
2. 任务页 PDF + xlsx 预览
3. 修改页重做：左 AI 对话（实时进度）+ 右产物/预览
4. 写作页 tex 改完给 PDF 实时预览
5. 导航：主页/任务/修改/写作/评审/文件/扩展/设置（"文件"恢复）
6. 文件页做成 Xmind 思维导图

## 1. 异步 AI 修改（后端 + 前端轮询）★可复用模式

**为什么改异步**：LLM 改写文件需要 20-90s，同步 HTTP 请求期间前端一直转圈，无进度反馈。用户明确要求"AI 实时反馈进程"。

**后端模式**（main.py）：
```python
_ai_jobs: dict = {}          # task_id -> {status, detail, content, error}
_ai_lock = threading.Lock()

@app.post("/api/tasks/{task_id}/ai-edit")
def task_ai_edit(...):
    # 校验 rel/instruction/二进制拦截
    with _ai_lock:
        job = _ai_jobs.get(task_id)
        if job and job.get("status") in ("working", "reading"):
            raise HTTPException(409, "该任务有 AI 修改正在进行")   # 防重入
        _ai_jobs[task_id] = {"status": "reading", "detail": "读取任务上下文…", ...}
    def worker():
        # 1) status=reading/detail="读取题目分析与求解计划…"
        # 2) 读 题目分析.md + 求解计划.md 前1500字 + 当前文件前6000字 构造 context
        # 3) status=working/detail="AI 正在理解修改要求并改写文件…"
        # 4) LLMClient(...).chat(...)  → 剥 ``` 围栏
        # 5) status=done/detail="AI 修改完成"/content=stripped
        # 异常 → status=error/detail=str(e)
    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "started": True}

@app.get("/api/tasks/{task_id}/ai-edit/status")
def ...:  # with _ai_lock: return job → {status, detail, content, error}
```
- 状态机：reading（读文件）→ working（LLM 生成）→ done/error
- 线程内更新 `_ai_jobs` 全程持锁；`detail` 是给前端显示的进度文案
- **前端必须用轮询，不能再等 POST 同步返回 content**（POST 现在只返回 started）

**前端轮询模式**（modify.js 对话 / ModifyUI 弹窗 / write.js AI 按钮三处一致）：
```js
btnAi.disabled = true; status.textContent = '正在启动 AI…';
await API.aiEdit(id, rel, instruction);          // 只启动
const poll = setInterval(async () => {
  const s = await API.aiEditStatus(id);          // {status, detail, content, error}
  if (s.status === 'reading' || s.status === 'working') {
    status.textContent = '⏳ ' + s.detail;        // 实时进度
  } else if (s.status === 'done') {
    clearInterval(poll);
    ta.value = s.content || '';                   // 结果填入 textarea
    // ✅ 提示"检查无误后点保存"
  } else if (s.status === 'error') {
    clearInterval(poll); status.textContent = '❌ ' + (s.error || s.detail);
  }
}, 800);
```
注意：`setInterval` 里的 poll 要在 done/error 分支 clearInterval，否则泄漏。

## 2. 修改页左右分栏（modify.js 重做）

```
┌ 顶栏: 标题 + 说明 + <select id="md-task"> 任务切换 ┐
├──────────────┬────────────────────────────────────┤
│ 🤖 AI 修改助手 │ 产物文件（STEP_PRODUCTS 分组按钮）   │
│ md-chat-body │ 预览/编辑：                          │
│  (消息列表)   │  - 文本 → textarea#md-editor(+保存)  │
│ md-chat-input │  - 图片 → <img>                     │
│ (意见+发送)   │  - PDF → <iframe data:pdf>          │
│              │  - xlsx → API.xlsxPreview HTML 表格  │
└──────────────┴────────────────────────────────────┘
```
- CSS：`.md-grid { grid-template-columns: 320px 1fr }`，<900px 切单栏；`.md-msg.md-ai`/`.md-user` 聊天气泡
- 全局 `_mtid`/`_mrel` 记住"当前任务/当前文件"，AI 对话发送时校验两者非空
- 页面内 select 切换任务 → `loadTree()` 重渲染产物分组

## 3. xlsx 预览（pandas → HTML 表格）

```python
@app.get("/api/tasks/{task_id}/xlsx-preview")
def ...(task_id, rel):    # 校验路径后：
    import pandas as pd
    sheets = pd.read_excel(p, sheet_name=None, nrows=50)   # 全 sheet 各读前50行
    html_parts = []
    for name, df in sheets.items():
        html_parts.append(f"<div class='xlsx-sheet'><div class='xlsx-sheetname'>工作表：{name}（{len(df)} 行 × {df.shape[1]} 列）</div>")
        html_parts.append(df.head(50).to_html(index=False, classes="xlsx-table", border=0, escape=True))
    return {"ok": True, "html": "".join(html_parts), ...}
```
前端 `.xlsx-table { border-collapse; th  sticky; white-space: nowrap }`；`.xlsx-preview { overflow:auto; max-height:420px }`。
备用：单 sheet 读取放 try/except → `{"Sheet1": ...}`。

## 4. 写作页保存 → 自动编译 → PDF 预览

`#wp-save` click → `writeTaskFile` → `autoCompileAndPreview()`：
```js
async function autoCompileAndPreview() {
  const r = await API.compileTask(id);
  if (r.ok) {
    const fr = await API.readTaskFile(id, '论文/论文.pdf');   // 后端返回 base64
    preview.innerHTML = `<iframe src="data:application/pdf;base64,${fr.content}#page=1" ...>`;
    // 附带"用系统阅读器打开"按钮 → mUltra.openPath(path)
  }
}
```
用户工作流：改 .tex → 💾 保存 → 自动重编译 → iframe 立刻显示新 PDF。

## 5. 文件页 Xmind 思维导图（view.js，手写 CSS 树）

- 结构：`.mm-branch`（任务单元）→ `.mm-node.mm-center`（彩底中心节点，`--hue` 按索引着色）+ `.mm-kids` 虚线缩进子层
- 子层：目录 `.mm-node.mm-dir`（左边框 accent）→ 文件 `.mm-node.mm-file[data-rel]`（点击 → `openMindPreview(tid, rel, name)`）
- `openMindPreview` 弹窗复用三种预览：图片内联 / PDF iframe / xlsx 表格；文本文件给"✎ 编辑"按钮 → `ModifyUI.openEditModal`
- 迭代注意：文件路径仍是 Windows 反斜杠，`data-rel` 存储时已 `replace(/\\/g,'/')`

## 6. 前端按扩展名选图标的小技巧

```js
const icon = name.endsWith('.png')||name.endsWith('.jpg') ? '🖼'
  : name.endsWith('.pdf') ? '📕'
  : name.endsWith('.csv')||name.endsWith('.xlsx') ? '📊'
  : name.endsWith('.tex') ? '📝'
  : name.endsWith('.py') ? '🐍' : '📄';
```

## 会话级坑（后续同项目会话务必注意）

1. **MSYS curl 中文 body 必炸**：`curl -d '{"instruction":"中文…"}'` → "There was an error parsing the body"。
   修复：把 JSON 写文件后用 `curl --data-binary @"$REQ_FILE"`。API 测试一律走此路径。
2. **前端路径匹配前统一 slash**：后端 `task.json tree` 的 path 是 Windows 反斜杠（`求解\问题一\...`），前端 STEP_PRODUCTS 等匹配用正斜杠 → 必须 `f.path.replace(/\\/g,'/')`。忽视会造成"修改模式编辑按钮不显示"类 bug（本会话实锤一次）。
3. **`GET file` 对 PDF 返回 base64**（旧版只返回占位文本 `[PDF 请在系统查看器中打开]`，iframe 预览必须后端改）：
   ```python
   if suffix in (".pdf",):
       b64 = base64.b64encode(p.read_bytes()).decode()
       return {"content": b64, "binary": True, "path": str(p), "mime": "application/pdf"}
   ```
4. **改后端后必须重启 Electron 整个应用**（主进程拉起后端，仅重启 uvicorn 不够）；端口被占时 `netstat -ano | findstr 18113` → `taskkill /F /PID <pid>`。
5. ad-hoc 验证脚本规范：`C:\Users\...\Temp\hermes-verify-<timestamp>.js`，运行后 `rm` 清理，输出 `===== hermes ad-hoc: n/n =====`，MU 项目无 pytest/jest 套件，报告时显式标注"非套件 green"。

## 验收要点（第二轮）

- 导航顺序：主页/任务/修改/写作/评审/文件/扩展/设置
- 修改页：左对话发送 → 轮询 reading→working→done → 内容进右侧 → 保存 → 单步重跑
- 任务页：PDF iframe、xlsx 表格
- 写作页：改 tex 保存 → 自动编译 → iframe 新 PDF
- 文件页：思维导图 + 点击预览/编辑
- 评审页：无修改组件