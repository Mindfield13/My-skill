# PDF 自绘阅读器 + PreviewUI 共享预览（M Ultra v3，2026-08-17）

## 背景：用户拒绝了什么

1. **iframe data:base64 PDF 预览被否**：`<iframe src="data:application/pdf;base64,...">` 在 Electron 里唤起 Chromium 原生 PDF viewer，顶部工具栏显示乱码文件名（base64 哈希样）、文件名重复、且 modal 难以关闭（viewer 覆盖层吞点击）。用户原话："你这个预览要做好了""显示不全""打不开退不出来"。
2. **小弹窗预览被否**：文件页思维导图点文件弹 `UI.openModal` 小窗（高度/宽度受限，PDF/xlsx 显示不全）。用户要求"不要你整个小对话框"。

**结论（写入习惯）**：本应用所有文件预览一律放**页面内大区域**（左右分栏的右栏，或面板内嵌），**禁止为预览开小 modal**；PDF 一律**自绘分页阅读器**，禁止 Chromium 原生 viewer。

## 后端 API（src/backend/main.py）

```python
@app.get("/api/tasks/{task_id}/pdf-info")   # ?rel=论文/论文.pdf → {"ok":true,"pages":N}
@app.get("/api/tasks/{task_id}/pdf-page")   # ?rel=...&page=1 → {"ok":true,"page":1,"total":N,"image":"<png base64>"}
```

实现要点：
- `import pymupdf as fitz`（**新版包名 pymupdf**；`import fitz` 会打 deprecated warning——v3 曾先按旧名写，收到 "The `fitz` API is deprecated" 警告后统一改）
- 渲染：`pg = doc[page-1]; pix = pg.get_pixmap(matrix=fitz.Matrix(1.6,1.6)); base64.b64encode(pix.tobytes("png")).decode()`
- 安装：`.venv/Scripts/python.exe -m pip install pymupdf -i https://mirrors.aliyun.com/pypi/simple/`

## 前端共享组件 src/renderer/js/preview.js

`window.PreviewUI.render(el, tid, rel, opts)` 一个入口分派：

- `opts.editable`（文本可编辑 + 保存按钮）
- `opts.aiInstr`（显示 AI 输入行 + 🤖 按钮，走 aiEdit 启动 + aiEditStatus 800ms 轮询）
- `opts.onSaved(rel)`（保存后回调）
- 分支：`r.binary && mime==='application/pdf'` → renderPdfReader；`mime.startsWith('image/')` → 大图；`rel.endsWith .xlsx/.xls` → renderXlsx（API.xlsxPreview → html 表格）；`!r.binary` → renderText。

PDF 阅读器 DOM 结构（无 Chromium 工具栏）：

```
.pv-pdf > .pv-pdf-toolbar（文件名 + ‹ 页码 ›）+ .pv-pdf-body（overflow:auto，深色#1a1a1f，内 <img width:100%>）
```

翻页：`‹/›` 按钮调 `API.pdfPage(tid, rel, page)` 换 `img src="data:image/png;base64,.."`。

CSS：`.pv-loading` / `.pv-center` / `.pv-ai` / `.vf-grid`（左 320px 导图 + 右 1fr 预览）等见 `css/app.css` "共享预览组件"段。

## 修改页产物全量（用户要求）

第一版修改页产物树只按 `MODIFY_STEP_PRODUCTS`（md/py/tex）过滤 → 用户看到只有两组，"没看到全部产物 PDF 和 xlsx"。v3 改为 `task.tree` 原样 map 按**目录**分组（题目/ 数据/ 求解/ 论文/），每个按钮带类型 emoji 图标。已有 PDF（如 `题目/C题.pdf`、`数据/附件.xlsx`）会显示并可点开预览（PDF 阅读器 / 表格）。

## 其他 v3 顺手修复

- **MSYS curl 中文 body**：`curl -d '{"instruction":"中文"}'` 在 git-bash 会 "error parsing the body"；改 `printf '...' > "${TEMP}/ai_edit_req.json"` + `curl --data-binary @"$REQ"`。注意 `/tmp` 在 MSYS 会被映射走样，用 `C:/Users/<user>/AppData/Local/Temp/` 显式路径。
- **路径分隔符**：后端 `task.tree[].files[].path` 是反斜杠（`求解\问题一\问题一_求解.py`）；前端做文件名/类型匹配前必须 `f.path.replace(/\\/g,'/')`（v3 在 review/tasks/modify/view 四处置换了同样 bug，已入验证清单）。
- 修改页保存后不回跳编辑态：`PreviewUI.render` 文本分支自带 textarea+保存，`onSaved` 里仅提示"已保存，可重跑"。