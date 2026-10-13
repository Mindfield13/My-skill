---
name: electron-fastapi-backend
description: 从0开发 Electron + Python FastAPI 桌面应用（参照功能体验、代码原创）。
---

# Electron + FastAPI 桌面应用（从0开发）

## 触发条件
- 用户要"参照某软件功能"从0开发新工具 —— 意思是参照**功能体验**，代码全部原创，不是照搬、不是给破解版换皮
- 构建 Electron 壳 + Python FastAPI 后端的桌面应用（如 M Ultra 数模工作台）
- 用户：张宇松；C盘忌装工具；国内网络用阿里云镜像；逐步推进、batch+verify

## 核心架构（已验证可跑）
```
项目/
├── package.json                # "main": "src/main/index.js"
├── src/main/index.js           # 主进程：spawn 后端、选端口、health 轮询、退出清理
├── src/preload/preload.js      # contextBridge 最小暴露
├── src/renderer/               # 无构建前端（script 标签 + 全局 window.Views 命名空间）
│   ├── index.html / css/theme.css / css/app.css / js/*
└── src/backend/                # Python FastAPI（main.py / config.py / llm.py / extract.py / latex.py）
```
- Electron 主进程 spawn `.venv/Scripts/python.exe src/backend/main.py`，env 传 `M_ULTRA_PORT`
- 端口分配：`net.createServer` 探测空闲端口（从 18099 起，`srv.once('error')` 则 +1 重试）
- 等健康：`http.get /api/health` 轮询（30s 超时，500ms 间隔）
- 渲染进程直接 `fetch http://127.0.0.1:<port>`；后端 `CORSMiddleware allow_origins=["*"]`（file:// 来源必须）
- LLM 客户端（llm.py）：anthropic(`/v1/messages`) + openai(`/v1/chat/completions`) 双协议；base_url 自动归一化补 `/v1`；`/api/model/test` 发最小请求验证连通
- preload 里 `ipcMain.handle('backend-port')` 让渲染进程拿到端口

## Windows 启动脚本（.bat / .ps1）

用户期望双击启动，不要开两个终端。两种方案：

### 方案 A：批处理启动.bat（推荐，双击即用）

```bat
@echo off
chcp 65001 >nul
title M Ultra 数模工作台

set "PROJ_DIR=E:\Project\M Ultra\M-Ultra-数模"
cd /d "%PROJ_DIR%"

echo [1/2] 启动后端服务...
start "MUltra-Backend" /min cmd /c "set PYTHONPATH= && set PYTHONHOME= && set VIRTUAL_ENV= && set PYTHONUTF8= && set PYTHONIOENCODING= && set M_ULTRA_PORT=18113 && .venv\Scripts\python.exe src\backend\main.py"

echo [2/2] 启动前端界面...
start "" "%PROJ_DIR%\node_modules\electron\dist\electron.exe" "%PROJ_DIR%"

echo 启动完成！
```

**关键注意**（全部踩过）：
- **不要用 `env` 命令**——它是 Linux 的，Windows cmd 不认识。用 `set VAR= && set VAR2= && ...` 在一行里清除多个变量。
- `start` 创建的**子进程不继承父进程的 `set` 环境变量**，所以清除环境必须写在 `cmd /c "set ... && command"` 的同一行里。
- `start "title" /min cmd /c "..."` 用 `/min` 最小化窗口，不给用户弹黑框。
- Electron 启动建议用 `electron.exe` 完整路径而非 `electron.cmd`（`.cmd` 在 `start` 中可能不解析）。
- 用 `start /d "DIR"` 或硬编码 `${PROJ_DIR}` 确保工作目录（`start` 新窗口默认是 `%windir%`）。

### 方案 B：PowerShell 脚本（更稳健但执行策略限制）

```powershell
$env:PYTHONPATH = ""
$env:PYTHONHOME = ""
$env:VIRTUAL_ENV = ""
$env:PYTHONUTF8 = ""
$env:PYTHONIOENCODING = ""
$env:M_ULTRA_PORT = "18113"

Set-Location "E:\Project\M Ultra\M-Ultra-数模"

$backend = Start-Process -WindowStyle Hidden -FilePath ".venv\Scripts\python.exe" -ArgumentList "src\backend\main.py" -PassThru
Start-Sleep 5
Start-Process -FilePath "node_modules\electron\dist\electron.exe" -ArgumentList "."
```

PS1 需要 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` 才能运行。

### 重启 Electron 的正确方法

用户说"重启"时，不要只 kill 进程再 start，要：
1. 先 `MSYS_NO_PATHCONV=1 taskkill /F /IM electron.exe`（杀所有 Electron 实例，避免旧实例占 CDP 端口）
2. 验证 `netstat -ano | grep :9223 | grep LISTENING` 确认端口空闲
3. 再 `node_modules/.bin/electron . --remote-debugging-port=9223` 重新启动
4. 验证 `curl http://127.0.0.1:9223/json` 返回 page target

**不杀干净就重启 → 看到的是旧版 UI**（CDP 连到旧实例，新实例 bind 失败静默退出）。

## Windows 坑（全部实测踩过）
1. **Hermes 会话注入 PYTHONPATH/PYTHONHOME 指向 Hermes 自带 venv** → `python -m venv` 产出的 pyvenv.cfg 为空、pip 装进错误 site-packages、后端加载错包。**必须**：
   ```
   env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV -u PYTHONUTF8 -u PYTHONIOENCODING .venv/Scripts/python.exe ...
   ```
   Electron spawn 后端时同样要在 childEnv 里 `delete PYTHONPATH/PYTHONHOME/VIRTUAL_ENV`。
2. **MSYS bash 中文路径乱码**（如 `M-Ultra-??`）：python/venv 命令用 Windows 风格绝对路径，`"C:/Users/.../python.exe" -m venv "E:/Project/M Ultra/项目/.venv"`。pyvenv.cfg 空文件 = 创建被污染，删掉重建。
3. **pip 默认源慢/卡死**：加 `-i https://mirrors.aliyun.com/pypi/simple/`（实测 15MB/s）。
4. **Windows curl 传中文 JSON body** 报 "error parsing the body"：写 JSON 文件用 `--data-binary @body.json`。
5. **git-bash 的 taskkill**：`taskkill //F //PID n` 报参数错，用 `MSYS_NO_PATHCONV=1 taskkill /F /PID n`。
6. **process kill 杀不干净**：Windows 端口仍被旧进程占用，新进程 bind 失败退出（日志只有 "no job control"）。必须验证：`netstat -ano | grep :PORT | grep LISTENING` → 拿 PID taskkill。
7. **FastAPI 路径段别用中文**（路由 404 / URL 编码问题）：任务 ID 用时间戳+随机 ASCII，中文只放 name 字段。
8. **Electron 43 移除 File.path**：渲染进程取文件路径必须走 preload 暴露的 `webUtils.getPathForFile(file)`。
9. **LaTeX 中文目录**：xelatex 前用 `ctypes.windll.kernel32.GetShortPathNameW` 转 8.3 短路径，日志写回原目录。
10. **隐藏系统菜单栏**（用户明确讨厌 File/Edit/View 那种\"老古董\"菜单栏）：
    ```js
    const { app, Menu } = require('electron');
    Menu.setApplicationMenu(null);                 // whenReady 里
    // BrowserWindow 选项: autoHideMenuBar: true
    win.setMenuBarVisibility(false); win.setAutoHideMenuBar(true);
    ```
11. **Electron 重启残留=看旧 UI 假象**：多个 electron 实例时 CDP 端口被旧实例占用（新实例 bind 失败只有日志 \"no job control\"），连 CDP 看到的是**旧版页面**（磁盘文件已是新的）。重启前必须 `MSYS_NO_PATHCONV=1 taskkill /F /IM electron.exe`，并 `netstat -ano | grep :9223 | grep LISTENING` 确认端口归谁。
12. **绝对不要 `taskkill /F /IM python.exe`**：会把 Hermes 自身后端杀掉 → 会话直接中断。只按确认 PID 杀项目自己的 python。
13. **HTML id 与 app.js 查找名必须一致**（如 welcomePanel vs homePanel 不一致 → 渲染静默抛错、面板空白）。改名后先用 CDP diag 查 `document.getElementById(...)` 是否存在。
14. **三层嵌套模板字符串易丢反引号**（SyntaxError Unexpected token '<'）：拆成独立函数返回字符串或字符串拼接，别叠三层 `${}`。
15. **CSS display:flex 覆盖 hidden 属性 → 黑条+模糊全屏 bug**：某 class 显式写 `display:flex`（如 `.modal-mask`）会覆盖 HTML `hidden` 属性 → 全屏遮罩永远可见，空 modal 渲染成中央黑色圆角长条，背景呈 backdrop-filter 模糊（用户截图报"这是什么情况"）。全局修复：CSS 顶部加 `[hidden] { display: none !important; }`。验证：`getComputedStyle(el).display === 'none'`。
16. **追踪"谁切了页面/改了状态"（幽灵交互）**：页面停在非预期视图但无报错时，临时给入口函数加 `console.warn(name, new Error().stack)`，重启后 CDP `Runtime.enable` 收集 console：stack 是 `at HTMLElement.<anonymous>` = 真实用户点击（程序没问题），是初始化调用 = 程序 bug。排查完移除日志。
17. **electron 二进制缺失**（postinstall 没跑，`npm install` 2s 就完成）：`cd node_modules/electron && ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ node install.js`。
18. **vision_analyze 读不了中文路径的图**：截图存英文路径（如 `C:/Users/.../AppData/Local/Temp/`）再分析；node 写文件路径里 `\\\\` 转义在 MSYS/Windows 下坑多，直接用正斜杠绝对路径。
19. **matplotlib 中文乱码（Glyph missing from font(s) DejaVu Sans）**：Windows 默认 rcParams 用 DejaVu Sans 画不出 CJK（标题/轴标签变警告方块）。修复：启动时 `matplotlib.font_manager.addfont` 注册 `C:/Windows/Fonts/msyh.ttc`（微软雅黑，其次 simhei.ttf/simsun.ttc/Deng.ttf），再 `rcParams["font.sans-serif"] = ["Microsoft YaHei","SimHei",...]` + `rcParams["axes.unicode_minus"] = False`。验证：`warnings.catch_warnings` 捕获渲染，`Glyph`/`missing from font` 警告数应为 0。
20. **FastAPI `app.mount("/assets", StaticFiles(directory=...))` 对不存在目录直接 RuntimeError 崩启动**（`Directory '...' does not exist`，uvicorn 起来即退）：mount 前必须 `if Path(dir).is_dir():` 守卫 —— 前端可能没有 assets/ 子目录（原生 CSS/JS 分离式前端）。
21. **uvicorn 测试后清理残留**：`process kill` 只杀 bash wrapper，**Python 子进程仍占端口**，下次 bind 报 `[Errno 10048] address already in use`。清理：`netstat -ano | grep :PORT | grep LISTEN` → 拿 PID → 验 cmdline（`wmic process where ProcessId=N get CommandLine`）确认是自己的 uvicorn → `MSYS_NO_PATHCONV=1 taskkill /F /PID N`。绝不用 `taskkill /F /IM python.exe`（杀 Hermes 自身）。

## UI 布局偏好（用户：张宇松）
- 对齐参考：MRITE_2.50 布局 —— **31px 细顶栏（可拖拽，左标题+右状态/主题分段）+ 74px 左侧窄图标导航**（58×58 圆角按钮，图标+10px 标签竖排，active 黑底/反色浮起）+ 面板式主区
- **不要**大 logo 区（左上角 logo+两行字被用户嫌弃\"太古老\"）；**不要**系统菜单栏
- Apple Design 深色 100% 优先（--panel 半透明、--accent #007AFF、圆角、负字距），浅色/跟随系统可选
- **分段控制器（协议切换/主题切换）**：必须绑定 click 事件切换 `active` 类，仅静态渲染 HTML 不足——用户点击后无视觉反馈=不可用。模式：`querySelectorAll('.seg-item').forEach(btn => { btn.addEventListener('click', () => { parent.querySelectorAll('.seg-item').forEach(b => b.classList.remove('active')); btn.classList.add('active'); }); })`。
- **面板缩放一致性**：所有面板（任务详情、写作面板等）统一用 CSS `panel-inner { max-width: 1200px; margin: 0 auto; }`，**不要内联 `style="max-width:1100px"`**，否则每个面板各自为政。
- **响应式布局**：`detail-grid { grid-template-columns: 300px 1fr; }` 在窄屏需切单栏：`@media (max-width: 1000px) { .detail-grid { grid-template-columns: 1fr !important; } .form-row { flex-direction: column; } }`。700px 以下再缩小 panel padding。
- **步骤时间线**：`.step-circle`（28px 圆，内容为 ✓/✕/①~⑤ 编号）+ `.step-row::before` 伪元素连接线（`left: 21px; top: 30px; width: 2px`）+ `stepPulse` 呼吸动画（running 状态 box-shadow 缩放）。
- **编译按钮状态机**：⏳ 编译中 → ✅ 编译成功 / ❌ 重试编译 → 3s 后恢复"编译论文"（`setTimeout` 重置）。失败时日志区显示错误详情。
- **布局必须填满屏幕，不留大片空白**（用户明确纠正过："你倒是填满啊，你留个空白什么意思"）：右侧主面板内 flex 列布局要让内容区 `flex:1` 撑满剩余空间；子元素 `max-height` 固定值会把预览区压扁并在底部留白。
- **改 UI 前先明确是哪个页面/哪个层级**（用户纠正过："你要明确是哪个层级再修改"）：动手前先用一句话说明目标页 + 主区结构，不要笼统改"所有页面"。
- **预览区被压扁的排查**（修改页/文件页实测）：右侧面板内文件列表 + 预览区被三层高度约束压扁：① JS 内联 `style="max-height:200px"` ② 复用类 `.log-box { max-height:320px }` ③ 未设 `flex:1`。修复模板：
  ```css
  .md-right { display: flex; flex-direction: column; min-height: 0; height: 100%; }
  .md-right #md-filetree { flex: 0 0 auto; max-height: 150px !important; overflow: auto; }  /* 列表压扁可滚动 */
  .md-right #md-preview { flex: 1; min-height: 0; overflow: auto; max-height: none !important; } /* 预览撑满 */
  .md-right #md-editor { flex: 1; min-height: 0; }  /* 编辑态同样撑满 */
  ```
  要点：inline 样式和复用类的 max-height 都要 `!important` 覆盖；百分比 max-height 在 flex 子项里不可靠（用固定值或 flex:1）；grid 单元格内 flex 容器记得 `height:100%`。
- **CSS 类名冲突：复用现有组件类做新控件会错位**（实测）：拿 `.toggle-btn`（圆形单选：22px + 2px border + flex 居中）做 iOS 滑块 → 轨道多了一圈边框、knob 被 flex 挤偏。新建控件用**独立类 + `::after` 伪元素**，不借现成类：
  ```css
  .cf-switch { width:44px; height:24px; border-radius:12px; position:relative; cursor:pointer;
    background: color-mix(in srgb, var(--text-3) 35%, transparent); display:inline-block; border:none; }
  .cf-switch::after { content:''; position:absolute; top:2px; left:2px; width:20px; height:20px;
    border-radius:50%; background:var(--panel); box-shadow:0 1px 3px rgba(0,0,0,.3); transition:left .2s; }
  .cf-switch.active { background: color-mix(in srgb, var(--accent) 60%, transparent); }
  .cf-switch.active::after { left:22px; }
  ```
  事件绑定只 `classList.toggle('active')`，伪元素自动跟随，不用 JS 改 left。
- **浅色主题下白色半透明轨道隐形**（"按钮不见了"）：`rgba(255,255,255,.12)` 在白底上≈透明，白圆点也看不见。轨道/边框一律用主题变量：`color-mix(in srgb, var(--text-3) X%, transparent)`（次要文字色两主题都可见）、`var(--panel)` 做圆点底色。
- **截图说"错位"先查 DOM 再改**：vision 会误判（浅色隐形/相邻元素），先 `getBoundingClientRect()` 对比控件 y 坐标；差 ≤4px 就是正常对齐，问题只是颜色对比度。别为假错位改布局。

## 视觉验证（CDP 截图，满足用户"要截图验证"偏好）
1. 启动：`node_modules/.bin/electron . --remote-debugging-port=9223`
2. 截图：`node scripts/cdp-shot.js 9223 shot.png`（依赖 Node 24 全局 WebSocket + fetch，无需额外依赖）
3. 快速确认：`curl http://127.0.0.1:9223/json` 看 page target 的 title/url 已加载
4. **验证顺序：DOM 诊断优先于截图** —— 深色 UI 截图经 vision 分析常被误判"模糊/黑色遮挡条"，以 `scripts/cdp-diag.js` 的 DOM 数据为准（body 长度、面板存在性、元素计数）
5. 截图要在 splash 淡出后（等 ~3s），否则截到启动闪屏
6. **CDP Runtime.evaluate 返回 object 拿不到值**：一行的 `Runtime.evaluate` 直接返回 object 时给的是 `objectId` 引用（description 显示 `Object`），必须加 `returnByValue: true` 参数并让表达式返回 `JSON.stringify(...)` 字符串，`msg.result.result.value` 才是数据。实测坑：未加时调试半天拿不到页面状态。
7. **`Page.captureScreenshot` 无限挂起/无响应 = 窗口不在前台**（实测，排查耗时最长）：Electron 窗口被最小化/遮挡 时 `document.visibilityState === "hidden"`，此时 `captureScreenshot`（fromSurface:true）永不返回。`Page.bringToFront` **不能恢复已最小化窗口**（visibilityState 仍是 hidden）——唯一可靠办法是杀掉重启 Electron（新窗口默认 show，visibilityState 变 visible 后立即截图）。诊断：`Runtime.evaluate` 读 `document.visibilityState` + `document.hasFocus()`；两者非 visible/false 就别截图，先重启。
8. **Node 24 原生 WebSocket 只认 `addEventListener('open'/'message')`，`ws.onopen/onmessage` 属性静默不触发** → 脚本永远等不到响应超时。CDP 工具脚本统一用 `addEventListener`；批量截图脚本里连发多条命令会竞态，改**响应驱动**（pending Map：`send(method)` 返回 Promise，收到 id 匹配的响应再 resolve，下一步等上一步完成），不要固定 sleep 连发。
9. **批量页面前先 `Page.bringToFront` 再逐页 gotoView**：隐藏窗口下即使 gotoView 正常，截图仍挂。切页后等渲染（~1.5s）再截。

## AI 工作流引擎模式（M2 读题/计划 + M3 逐题求解，实测跑通）

后端 `src/backend/workflow.py` 自研步骤引擎，模式如下：

- **步骤定义**：`STEPS = [{id, name, desc}...]`（读题→求解计划→逐题求解→论文生成→编译PDF）+ `ACTIVE = {"read_problem","solve_plan","solve"}`（未实现步骤跳过不阻塞）
- **状态持久化**：每步状态写 task.json（`steps[id].status` pending/running/done/error + `current_step` + 顶层 `status`）；日志追加 `输出/workflow.log`（progress 接口只读尾部 60 行给前端）
- **后台线程**：`threading.Thread(target=_run_loop, daemon=True)`；`stop_flag = threading.Event()`，循环内每步检查；`start()` 若 `status=="running"` 拒绝并发
- **断点续跑**：`start()` 里 `existing = {s["id"]: s for s in meta.get("steps",[])}`，已 done 的步骤保留，其余重置 pending；`_run_loop` 用 `_step_is_done()` 跳过 → 用户点"开始求解"只跑未完成步骤。注意：重置 task.json 后立即 `curl run` 可能被后台旧线程（上次 run 的残留）写回旧状态，重置不生效——必须重启后端进程（kill+spawn）彻底清空线程池。
- **失败修复循环**（AI 代码执行的核心）：`for attempt in range(1,4)`：LLM 生成完整代码 → 写 `求解/问题X/问题X_求解.py` → `subprocess.run([venv_python, script], cwd=问题目录, timeout=300)` → exit!=0 或无产出（图片/CSV 都空）→ 把 stderr 尾部回灌 LLM（`messages.append(user=报错)`）→ 重试；3 轮全败 → WorkflowError 置 error 状态。
  **Windows 关键修复**：① `subprocess.CREATE_NEW_PROCESS_GROUP`（`creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0`）防止父进程 Ctrl+C 传播到子进程 → 否则 exit=3221225794（STATUS_CONTROL_C_EXIT）且 stdout/stderr 为空。② 不用 `text=True` + `encoding='utf-8'`（Windows 上有时返回空输出），改 `capture_output=True` 后手动 `proc.stdout.decode('utf-8', errors='replace')` + `proc.stderr.decode(...)` 并在 proc 对象上挂 `stdout_text`/`stderr_text` 属性供调用方使用。③ `env = {**os.environ}` 后用 `pop` 清除 `PYTHONPATH/PYTHONHOME/VIRTUAL_ENV` 等干扰变量，再设 `PYTHONUTF8=1`。
  **修复 prompt 优化**：stdout/stderr 各保留 2000/1500 字符，标注 `--- STDOUT (末尾) ---` / `--- STDERR (末尾) ---` 分隔，末尾加 `请在读取数据后用 print(list(df.columns)) 确认列名` 提示，引导 LLM 检查列名匹配。
  **论文生成 prompt 优化**：`spec[:1500]`（原 3000）、`题目分析/求解计划[:1500]`（原 2000）、CSV 头 `[:200]`（原 500），减少 token 消耗约 40%。
- **LLMClient.max_tokens 防御（配置写坏 → HTTP 400 invalid arguments）**：config.json 里 max_tokens 曾被写成浮点科学计数法 `1e+25`，`int()` 后变成天文数字 → provider 报 `HTTP 400 {"type":"error","error":{"type":"invalid_request_error","message":"invalid arguments"}}`（只出现在**不显式传 max_tokens 的调用**，如修复循环/读题/评估——显式传 8000 的采样正常，迷惑性很强）。防御：`__init__` 里 `try: mt=int(cfg.get("max_tokens",8192)) except: mt=8192; self.max_tokens = mt if 1<=mt<=16384 else 8192`；前端设置页 collectProfiles 对 number 输入同样 clamp（`Number.isFinite(n) && n>=1 && n<=16384 ? n : 8192`）。诊断顺序：单发最小请求测 8192/12000/16000 是否被接受 → 打印 profile 原值（`repr` 会现出 1e+25）。
- **代码提取 `_extract_python` 四层容错**：LLM 输出**被截断时代码块无闭合 ```** 原正则匹配失败 → ` ```python ` 原样写进 .py → `SyntaxError: invalid syntax`（3 轮修复全败在同一处）。四层：① 完整闭合代码块 ② 去 `\r\n` 后重试 ③ 无闭合 → 取第一个 ```python 之后到末尾（打"疑似截断"日志）④ 无标记 → 去反引号前缀原样返回。why 判断"提取`m3`命不命中"要打日志，方便把截断情况回灌下一轮修复。
- **问题清单归一化去重（问题1 vs 问题一 混用 → 重复求解）**：`_find_problems` 把数字 key 统一转中文（`{"1":"一",...}`）再去重排序，否则一份求解计划里"问题1"和"问题一"被当成两个问题各跑一遍；`_plan_section` 的匹配 pattern 同时兼容中文/数字（`问题(?:三|3)[：: ]`）。
- **多方案采样（每题 2 份代码选优）**：`_step_solve` 对每题先在隔离目录 `方案1/方案2/` 各生成一份代码（temperature 0.4/0.9，max_tokens=8000）分别运行，得分 = `exit==0 ? 1000 : 0 + 图片数*10 + 结果数`，最优的产物合并回 `图片/ 结果/`、代码写 `问题X_求解.py`，两方案都无产出才进 3 轮修复循环。
- **推理模型（deepseek/sensenova）LLM 客户端坑（llm.py chat）**：
  ① **max_tokens < 512 会"响应无文本内容"**——思维链（thinking 块）占满配额，text 块为空；测试连接/短调用一律 ≥512。
  ② **偶发只输出 thinking 块无 text 块**（HTTP 200 但 `_parse_reply` 遍历 content 找不到 `type=="text"` → LLMError"响应无文本内容"）：`chat()` 里对 `"无文本内容" in str(e)` 自动重试（≤3 次，递增 `time.sleep(1.5*n)`），429 限流重试保留，循环 `range(8)` 覆盖两种重试叠加。
  ③ **Python 作用域陷阱**：函数内任一分支 `import time` 使 `time` 成为该函数**全程局部变量**——没走到那条分支就调用 `time.sleep()` 会 `UnboundLocalError`（429 分支局部 import 曾导致正常路径崩溃）。删局部 import，用顶层 import。
- **跳过已求解问题**：`_step_solve` 循环开头检查 `(prob_dir / "图片").exists() and any((prob_dir / "图片").iterdir())` → 已有图片产出的问题自动跳过，不重复求解。
- **逐题定制 prompt**：`_code_prompt` 支持按 `problem` 名追加特殊说明（如 `问题四` 追加女胎数据 sheet 名称、列结构、目标列），用 `extra = ""` + `if problem == "问题四": extra = "..."` 结构避免括号嵌套语法错误。
- **论文标题替换（用户实测抱怨"论文题目差劲"的根治）**：最早用 `meta.get("name")`（=任务名，如 "C"/"导出测试"）替换占位符 → 标题烂。正确做法：`_step_paper` 组装 prompt **前**先调 LLM 提炼标题（prompt：15~28字、体现方法+研究对象、格式"基于XX方法的XX建模与实证分析"、只输出标题；`temperature=0.5, max_tokens=512`），存 `求解/论文题目.md`（用户可改，重跑即生效），占位符替换时 `title = paper_title or meta.get("name", "数学建模竞赛论文")`。提炼 LLM 调用要 try/except 兜底回退任务名。
- **问题识别**：`re.finditer(r"问题([一二三四五六七八九十\d]+)[：: ]", 求解计划)` 提取问题清单去重，`_plan_section()` 截取"问题N"标题到下个问题标题的段落作为该题 prompt 上下文
- **Python 脚本铁律**（prompt 里强制，已实测防 stdout 乱码/图中文乱码）：\n  ```python\n  import sys, io\n  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\n  import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt\n  plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False\n  ```\n  图存 `图片/`、CSV 存 `结果/`（utf-8-sig 中文名）；数据文件用绝对路径（prompt 里给出）；执行 env 清 `PYTHONPATH/PYTHONHOME/VIRTUAL_ENV` 且 `PYTHONUTF8=1`\n- **M4 论文生成（`_step_paper`）**：① 复制模板（`templates/模板名/` → `论文/` 保留 `.tex`/`.cls`/`fonts/`）② 复制求解结果图到 `论文/图片/`（加 `问题X_` 前缀，避免 LaTeX 跨目录中文路径问题）③ 收集结果摘要（CSV 前 5 行 + 图名列表）→ 构造 prompt 含章节规范 + 所有章节文件列表 ④ 调用 LLM（max_tokens=12000），要求输出 `【=== 文件名.tex ===】` 分界标记格式 ⑤ 按行扫描解析（`re.compile(r"(?:【===|===)\\s*([^=\\n]+?\\.tex)\\s*(?:===】|===)?")`，匹配→写上个文件+开新文件，不匹配→追加到当前文件内容），跳过 `论文.tex` 骨架 ⑥ 0 章节命中回退：全文写入 `0.摘要.tex` 保底 ⑦ 保存 AI 回复原文到 `论文/_ai_reply.txt` 调试用\n- **M4 编译（`_step_compile`）**：`import latex as latex_mod`（函数内避免顶层循环引用）+ `latex_mod.compile_tex(str(paper_dir))`；成功设 `meta["has_pdf"]=True`，失败 `raise WorkflowError`。\n- **常见 TeX 阻塞点**：MiKTeX 安装损坏时 xelatex.exe 报 `STATUS_DLL_NOT_FOUND 0xC0000135`（icuuc74.dll 版本不匹配，系统有 icuuc78.dll），`miktex packages update` 显示"no updates available"也无法修复——必须重装 MiKTeX 或从官网下载最新安装包覆盖。TinyTeX 的 `xelatex.fmt` 因路径硬编码无法加载，`fmtutil` 重建也因 Perl 依赖失败，不推荐作为备选编译引擎。
- **编译"成功"却只有 3 页（用户报"论文只有这一点"的根治，实测 3→17 页）**：① LLM 在章节里写 `\includegraphics{../求解/问题X/图片/xxx.png}`（原始路径）而编译目录只有 `论文/图片/` 副本 → 必然找不到；② 旧 `-halt-on-error` 遇到缺图**中止排版**，后面章节全没进；③ 成功判定只查 PDF 存在 → 静默交付残缺稿。三件套修复：源头注入《可用图片清单》到论文 prompt + 编译前规范化 includegraphics 路径（剥离 `问题X_` 前缀/共同后缀≥8 兜底）+ **去掉 -halt-on-error**、成功判定 = `fresh and pages>=5 and not fatal`。`Missing $`/`Missing number`/`Package calc`/伴随 Output written 的 `Emergency stop` 是可恢复警告不算 fatal；`Unable to load`/`Fatal error`/`No output PDF file written` 才是 fatal。详见 `references/latex-compile-robustness.md`。\n- **产出质量三件套（读题/求解/论文实测，成本低见效快）**：
  - **数据 EDA 前置**：读题和求解前先用 pandas 脚本（非 LLM）扫 `数据/` 生成 `求解/数据概况.md`（列名/dtype/缺失/唯一值/min-mean-max/前几行样例），注入读题 prompt 和 `_code_prompt` 的《数据概况》段——LLM 不再猜列名，代码一次写对率大幅上升。EDA 失败降级跳过，不打断流程。
  - **规则库注入**：`rules-library/math-skills/_wire/<step>.md`（从外部竞赛 skill 库抽取"完成铁律"段落，截 2500 字符）注入各步骤 system prompt——外部知识库扁平化进规则库后，扩展页可浏览 + workflow 自动吃铁律。注意：交互式 skill 全文（含 FAST_MODE/脚本名约定）不能直接注入，只抽规则性段落。
  - **评估注入对抗复核要点**：AI 评估 prompt 追加 review 铁律（方向反/重复计量/外推过硬/漏变量/跨问矛盾），评审更专业。
- **API**：`POST /api/tasks/{id}/run|stop`、`GET /api/tasks/{id}/progress`、`GET /api/workflow/steps`；引擎实例注册表 `_engines` + lock\n- **前端**：任务详情面板（非 modal）←返回 + 状态徽标 + 开始/停止按钮（按 running 状态互换 hidden）+ 左栏 5 步时间线（done 绿 ● / running 蓝 ◐ pulse / error 红 ✕ / pending 灰 ○）+ 右栏日志 box（自动滚底）+ 产物文件树；`setInterval 2s` 轮询 progress，切页/卸载前 `clearInterval`；跨页跳详情用 `window.__taskDetailId` + `window.MU.gotoView`

详见 `references/workflow-engine-m2m3.md`。

## M7 扩展：AI 评估 / 多任务并行 / 多模型交火（实测跑通）

### 异步耗时任务的标准模式（AI 评估 / ai-edit 共用）
长任务（LLM 调用）不能阻塞 HTTP 请求：`POST /api/...` 里 `_jobs[task_id] = {"status":"reading",...}`（加 `_lock`）→ 起 `threading.Thread(worker, daemon=True)` → `GET /api/.../status` 轮询 `{status: reading|working|done|error, result?, error?}` → 前端 `setInterval(1s)` 轮询。
**坑：完整结果只存 task.json 摘要（如 `ai_eval: {overall, evaluated_at}`）时，前端读回来没有 scores 数组，只显示总分**。完整结构化结果单独落盘（如 `评审/eval_result.json`），`GET report` 优先读它、回退 task.json 摘要。

### AI 评估（读产物+要求 → LLM 多维评分）
- 素材：论文 tex（clip 8000）+ 题目分析 + 求解计划 + 求解产物摘要（每问 图片/结果 数量 + CSV 前几条）+ 评估要求（task.json 文本 + `评估要求/` 目录文件；PDF/DOCX 用 `extract_file(f)["text"]`——**注意 extract_file 返回 dict 不是 str**）
- LLM system prompt 强制输出**合法 JSON**（scores[{key,score,comment}] 固定 5 维度 + overall + summary + weaknesses + suggestions）；解析用正则 ```` ```json {..} ```` `` 剥代码块、`\{.*\}` 兜底、失败给 0 分兜底，防止一次坏输出打断工作流
- 报告落盘 `评审/评估报告.md`（Markdown 渲染）+ `评审/eval_result.json`（前端直读）
- 示例维度：解题逻辑/模型科学性/结果分析/图表质量/论文规范

### 多任务并行
后端本来就支持——`_engines[task_id]` 每任务独立 `WorkflowEngine` + 独立 `threading.Thread` + 独立目录，无全局互斥。真正要补的是**单任务内 task.json 并发写安全**：
```python
self._meta_lock = threading.RLock()
def _save_meta(self, meta):
    with self._meta_lock:
        tmp = self._meta_file().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._meta_file())   # 原子替换
```
RLock（可重入）避免 `_set_step` 内部嵌套 `_load_meta/_save_meta` 死锁。并发压测：双引擎 × N 轮并发写 → 0 错误。

### 多模型交火（制作者-审核者循环，用户认可的方案）
用户原话方案："一个制作，一个审核，不断提出问题，审核质量"——不是多模型独立求解再仲裁，而是**单条产出线 + 审核者挑刺循环**：
```
制作者(主模型) 生成 → 审核者(另一模型) 审 JSON{score,pass,issues[],suggestions[]}
  → pass 或 score≥threshold → 结束
  → 否则制作者按 issues 修改 → 再审核（最多 rounds 轮）
```
- config 新增 `crossfire: {enabled, reviewer, rounds, threshold}`（DEFAULTS 里才有 save_config 会保留）；`get_reviewer_profile()` 优先配置的 reviewer 名，否则自动选非主模型的第一个可用 profile —— **审核者不能是主模型自己**
- 审核 prompt：`{"score":0-100, "pass":bool, "issues":[...], "suggestions":[...]}`，强制"分数<85 时 pass=false"压住凑数好评
- 接入点：① solve 代码成功产出后 `_crossfire_solve()`（审核→改→**重跑验证**，运行失败回退原代码，产物目录写 `交火记录.md`）② paper 整篇 tex 后 `_crossfire_text()`（纯文本循环）
- 修改轮保持对话链：`[user=原始题面, assistant=现有内容, user=审稿意见+完整重输出要求]`，每轮回复都是完整内容
- 实测：DeepSeek 审简单代码打 10 分，4 条具体问题 4 条建议，链路通

详见 `references/m7-features.md`。

## 支持文件
- `references/api-smoke-test.md` —— "检查软件运行逻辑及每个功能" 的全功能检查流程：后端 API 逐个冒烟（check 收集+汇总）、前端 8 页 CDP 截图、关键链路补测、静态语法全检；urllib 中文 URL 编码坑、404 对照文件系统判定
- `references/m7-features.md` —— M7 扩展实现细节：AI 评估（素材收集/prompt/JSON 输出解析）、多任务并行（RLock+原子写）、多模型交火（制作者-审核者循环、config、设置页 UI）
- `references/latex-compile-robustness.md` —— 论文"3 页残缺"根治：缺图根因链、可用图片清单注入、编译前 includegraphics 路径规范化（含正则捕获组 group(1)/group(2) 坑）、去掉 -halt-on-error、页数判定、可恢复 vs 致命错误分类、论文分步生成（大纲→逐章→摘要殿后）
- `scripts/cdp-shot.js` —— 通用 CDP 截图脚本（连调试端口 → Page.captureScreenshot → 存 PNG）
- `scripts/cdp-diag.js` —— DOM 诊断：URL/body 长度/导航按钮数/各面板 id 存在性/点击后状态（改名前必跑）
- `scripts/cdp-test.js` —— 交互测试：点击导航/设置按钮 + 收集 console error/warning + 连截图
- `scripts/cdp-shot-hd.js` —— 高清截图（Emulation.setDeviceMetricsOverride deviceScaleFactor 2）