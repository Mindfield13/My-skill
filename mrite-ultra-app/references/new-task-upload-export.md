# 新建任务：上传文件 + 输出目录导出（M7.4）

2026-08-17 用户硬性要求：「你不让我上传文件，你也不让我配置输出路径，你懂做题吗」。
规则：**做题第一步必须能传赛题文件 + 配置产物输出位置**；新建任务流程不能只有名称/模板/方案。

## 前端改动

### 1. Electron 43 文件/目录选择（★核心坑）

- `File.path` 在 Electron 43 已移除
- **contextBridge 不能直接把 DOM File 对象传给主进程**（不可结构化克隆），所以 `getFilePath(file)` 只适合 preload 内同步回调
- 正确方案：**主进程 `dialog.showOpenDialog` + IPC**

`src/main/index.js`：
```js
ipcMain.handle('dialog:pick-files', async () => {
  const { dialog } = require('electron');
  const win = BrowserWindow.getFocusedWindow() || mainWindow;
  const r = await dialog.showOpenDialog(win, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: '赛题与数据', extensions: ['pdf','doc','docx','xlsx','xls','csv','txt','png','jpg','jpeg'] },
      { name: '全部文件', extensions: ['*'] },
    ],
  });
  return r.canceled ? [] : r.filePaths;
});
ipcMain.handle('dialog:pick-dir', async () => {
  const { dialog } = require('electron');
  const win = BrowserWindow.getFocusedWindow() || mainWindow;
  const r = await dialog.showOpenDialog(win, { properties: ['openDirectory', 'createDirectory'] });
  return r.canceled ? '' : (r.filePaths[0] || '');
});
```

`src/preload/preload.js`：
```js
pickFiles: () => ipcRenderer.invoke('dialog:pick-files'),
pickDirectory: () => ipcRenderer.invoke('dialog:pick-dir'),
```

`src/renderer/js/components.js` `UI.pickFiles()`：优先 `window.mUltra.pickFiles()`；浏览器调试模式 fallback 用 `<input type=file>` + `mUltra.getFilePath(f)`（webUtils）。

### 2. 新建任务弹窗（tasks.js openNewTaskModal）

字段顺序：任务名称 → 📎 选择文件（显示已选文件名，创建后立即 `API.attachFiles(task.id, pickedFiles)`）→ 竞赛模板 → 求解方案 → 输出目录（`nt-outdir` 输入框 + `nt-pickdir` 浏览按钮，留空=保存软件内部）。

创建 payload：`API.createTask({ name, template, solve_plan, output_dir })`；若选了文件，创建成功后马上 attach（失败只 toast 不中断创建）。

### 3. 任务详情页按钮（renderTaskDetail）

- `📎 上传文件`（`td-attach`）：`UI.pickFiles(true)` → `API.attachFiles(id, paths)` → 重载 renderTaskDetail 刷新文件树
- `📤 导出`（`td-export`）：`API.exportTask(id)` → toast `已导出 N 个文件 → dir` → `window.mUltra.openPath(r.dir)` 自动打开文件夹

## 后端改动

### 4. output_dir 存储

`TaskCreateReq` 加 `output_dir: str = ""`；create_task 里 `meta["output_dir"] = (req.output_dir or "").strip()`。

### 5. 导出端点（POST /api/tasks/{id}/export）

```python
copy_if_exists(paper / "论文.pdf", "论文.pdf")
copy_if_exists(paper / "论文.tex", "论文.tex")
for p in (solve).rglob("*"):
    if p.is_file() and p.suffix.lower() in (".png",".jpg",".jpeg",".csv",".xlsx"):
        safe = rel.replace("\\","_").replace("/","_").replace(" ","_")
        shutil.copy2(p, target / safe)
```

- 需 `import time`（模块顶部）；create_task 里的局部 `import time` 不覆盖 export → NameError 500
- 无 output_dir → 400；无产物 → 400

## 坑（实测踩过）

| 症状 | 根因 | 修复 |
|------|------|------|
| 导出 500 Internal Server Error | `task_delete` 写 `from workflow import _engines, _engine_lock`，但两变量定义在 main.py | 同文件直接用模块级变量 |
| 导出 500 NameError: name 'time' is not defined | main.py 顶部无 `import time`（只在 create_task 局部 import） | 模块顶部 `import time` |
| 新建任务没文件选择 | 弹窗只有名称/模板/方案 | 见本文档第 2 节 |
| 上传选不了文件（File.path 报错） | Electron 43 移除 File.path + contextBridge 不能传 File | 主进程 dialog IPC |

## 排障

导出/删除 500 时看 Electron 进程日志：`process(action='log')` 尾部有 FastAPI traceback（`task_export` / `task_delete` 行号）。注意 taskkill 旧 Electron 后，之前进程的退出日志可能还在弹 IMPORTANT 通知——那是旧代码的 traceback，以新进程实测为准。