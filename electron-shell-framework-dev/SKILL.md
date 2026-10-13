---
name: electron-shell-framework-dev
description: Build Electron host shells embedding WebContentsView apps.
---

# Electron Host/Shell Framework Development (Windows)

Build a personal Electron "agent framework"/app-shell that hosts multiple Electron-architecture apps as plug-ins, with shared theme, model-provider config, and automated smoke verification. Distilled from the Trigon Agent build (E:\Project\Framework, Electron 43.4.0, Win11/MSYS, npm registry npmmirror).

## Proven architecture pattern

- **Shell window**: frameless (`frame:false`), custom slim titlebar (31px) + icon sidebar (74px); `Menu.setApplicationMenu(null)`; `titleBarStyle` overlay optional.
- **App container**: one `WebContentsView` per app (`contextIsolation:true, nodeIntegration:false, sandbox:false, backgroundThrottling:false`), shared preload exposing `window.trigon` bridge. Switch = `contentView.removeChildView(old); addChildView(new); layout()`.
- **App registry**: `src/apps/<id>/manifest.json` `{id,name,icon,entry,main?,order?,wallpaper?}`; optional `main.js` registers app-scoped main-process APIs (`api(method, fn)`); renderer calls them via `window.trigon.invoke(method, ...flatArgs)`.
- **IPC**: single channel `trigon:invoke` `{app, method, args}` routed to a global api map or app-scoped handlers.
- **Theme**: `nativeTheme.themeSource = light|dark|system`; broadcast `trigon:theme {mode, effective}` to every wc; preload sets `data-theme` per page; CSS variables per theme; wallpaper injected per view via `insertCSS` (absolute `pathToFileURL`).
- **Settings**: JSON in `userData/…-settings.json`, thin `settingsStore` module (get/set/per-app data).
- **Providers module**: OPENAI-compatible (`…/chat/completions`) + Anthropic native (`…/messages`) endpoints; presets for DeepSeek/Qwen/GLM/Kimi/MiMo/SenseNova/OpenAI/Claude/Grok + custom; SSE streaming via async generator; `AbortSignal.timeout()` on fetch.

## Critical Electron pitfalls (each bit hard in a real build)

1. **contextBridge naming collision** — `contextBridge.exposeInMainWorld('trigon', …)` creates a NON-configurable global. Any page top-level `const trigon = window.trigon;` throws `SyntaxError: Identifier 'trigon' has already been declared` (ECMAScript HasRestrictedGlobalProperty). Page scripts MUST alias differently: `const host = window.trigon;`. #1 breakage for ported apps; document it in porting guides.

2. **WebContentsView attach & offscreen capture (Windows/Electron 43)**:
   - Attach view to `contentView` BEFORE `loadFile` (after-load attach breaks offscreen capture).
   - On-screen view `wc.capturePage()` returns EMPTY (views aren't in the window compositor capture).
   - Offscreen (`webPreferences.offscreen:true`) view does NOT enter the paint pipeline right after attach — `capturePage` empty until you force re-attach: `removeChildView(v); addChildView(v); layout(); sleep(~600-800ms)`. Then it returns real frames. Root-caused by 12 control probes (A11 was the fix).
   - Full matrix: `references/electron-capture-and-verify-windows.md`.

3. **desktopCapturer caveats (Electron 43.4.0)** — `webContents.getMediaSourceId()` binding throws "Insufficient number of arguments"; match sources by `s.name === win.getTitle()` instead. Window thumbnails for windows containing WebContentsView children come back near-black — don't use for shell+view composites.

4. **CDP `webContents.debugger` `Page.captureScreenshot` on WebContentsView HUNG** (~98s, "target closed while handling command") — avoid; use the offscreen+re-attach path.

5. **withTimeout(promiseOrFn, ms, tag)** — `Promise.race([p, killer])` treats a passed FUNCTION as an immediately-fulfilled value: the body NEVER runs and the caller gets a truthy result → classic fake-PASS in smoke harnesses. Guard: `if (typeof p === 'function') p = p();` (same bug class: passing a fn to Promise.race instead of invoking it).

6. **waitFor polling** — if the polled fn never settles (`executeJavaScript` on a hung wc), a plain `await fn()` inside the loop hangs forever and the timeout is never reached. Use per-iteration `Promise.race([fn(), sleep(800)])` so the deadline is real.

7. **Windows GUI swallows stdout** — main-process `console.log` doesn't reach bash redirection reliably. Evidence must go to FILES (`fs.appendFileSync` progress.log / results.json), with write-back verification (`existsSync` + `statSync().size > 0`). `ELECTRON_ENABLE_LOGGING=1` surfaces renderer console to stderr. Wrapper exit codes unreliable → judge pass/fail from artifacts on disk.

8. **Harness exit** — use `process.exit(code)` for smoke scripts (app.exit once left orphan processes). Always kill leftover trees first: `MSYS_NO_PATHCONV=1 taskkill /F /T /IM electron.exe` — SINGLE-slash flags; `//F //IM` silently fails under MSYS.

9. **Electron binary on npmmirror** — `npm i -D electron` can finish WITHOUT `dist/electron.exe`; fix: `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ node node_modules/electron/install.js`.

10. **Layout-bug class** — layout helpers that default args to 0 then clamp (`Math.max(w, 320)`) silently produce 320×240 views. Resolve real window size (`BrowserWindow.getAllWindows()[0].getContentBounds()`) when args omitted, and setBounds BEFORE loadFile.

## Smoke-verification workflow (evidence-first, no fake passes)

Harness via `--smoke` flag inside the app's own main process:
- File-backed `log()` (console.log + appendFileSync progress.log), `check()` → `results.json {failed,total,results[]}`.
- Inline mock OpenAI-compatible HTTP server (127.0.0.1) serving canned `chat/completions` + `/models` → proves the provider chain end-to-end: main-direct call, renderer→preload→IPC bridge (`executeJavaScript` on shell), SSE streaming deltas.
- Global watchdog (`setTimeout` ~100s → `process.exit(1)`) so a hang can't wedge CI.
- Screenshots: shell via `capturePage` (real); views via offscreen+re-attach trick; every shot write-verified on disk; reject empty images.
- If the vision API is flaky: verify screenshots with PIL luminance stats (mean / dark<80 / bright>180 share — proves light vs dark actually rendered, catches all-black captures), then downscale to ≤1500px JPEG for vision analysis.
- Never report a check as passing without an artifact on disk.

## Templates & references
- `templates/app-manifest.json` — skeleton manifest for porting an app into the shell.
- `references/electron-capture-and-verify-windows.md` — capture capability matrix, the offscreen re-attach root-cause story, control-probe methodology, pixel verification.
- `references/modex-asset-copy-separable-component.md` — 照搬 Modex 资产进新组件 (cumcm) 的完整模式：SKILL.md 双格式注册表、模板 skill 引用对齐真实 id、可分离组件（CUMCM_EMBEDDED 环境变量 + standalone.js 独立入口 + 独立端口/venv）、matplotlib 中文字体注册、FastAPI StaticFiles 目录守卫。

## Integrating a third-party component with asset 照搬 (Modex → cumcm pattern)

用户模式(Trigon Framework 内新增组件)：**核心架构/资产/解题逻辑照搬 Modex，UI 用 Trigon Apple 风格，组件可分离、与既有组件互不干扰**。不是引用 Modex 文件，而是**物理复制**进组件目录。

### 照搬清单（实测 Modex 资产）
```
cp -r modex/skills    → 组件/backend/skills    (92 目录, ~180MB)
cp -r modex/templates → 组件/backend/templates (文档模板 .md)
cp -r modex/tools     → 组件/backend/tools     (pyc 工具链, ~14MB)
cp -r modex/katex-assets → 组件/frontend/vendor/katex
```
- Modex skills 每个目录 = `SKILL.md`（**明文** YAML frontmatter: name/description/argument-hint/allowed-tools）+ `templates/` + `references/` + 同名 `.enc` 加密副本。**明文与 .enc 双份共存** → 照搬直接可用，无需解密。`.enc` 只有 `skill_crypto.cp311-win_amd64.pyd`（Python 3.11 专属）能解，勿尝试。
- 陷阱：`cp -r` 到已存在目录会产生 `skills/skills_cache` 嵌套；先 `rm -rf skills` 再复制。

### SKILL.md 双格式注册表
引擎的 SkillRegistry 必须能加载两类技能：Modex `SKILL.md`（`MdSkill`，解析 frontmatter 得 id/description）+ 自研 Python `Skill` 子类（引擎内建逻辑）。内建 Python skill 放 `engine/builtin_*.py`，**显式注册**：
```python
# SkillRegistry._load_all() 里
from engine.builtin_final_package import FinalPackageSkill
self._skills[FinalPackageSkill.id] = FinalPackageSkill()
```
`import builtin_final_package` 裸导入会在 backend 顶层 sys.path 找不到，必须 `from engine.xxx import XxxSkill`。

### 模板 skill 引用必须对齐真实 id（关键）
模板步骤里 skill_name 写 Modex **真实技能 id**（`comp-prob-analysis`/`comp-modeling`/`comp-code`/`comp-paper-zh`/`comp-paper-zh-docx`/`comp-review`/`comp-compile-zh`/`paper-figure`/`paper-figure-drawio`/`quality-check`/`auto-paper-improvement-loop`），不要用自造占位名（`analyze-problem`/`ode-solver`/`paper-writer` 是我初版踩的坑）。`/api/skills` 可列出真实 id 全集用于对齐，另需内建 `final-package` 一类引擎技能补齐收尾。

### 可分离组件设计
- `main.js`(主进程 handler)：spawn 独立 venv/runtime python 跑 `-m uvicorn main:app --port <独立端口>`，健康轮询；`_findPython()` **优先组件 venv → Framework runtime python → 最后才 `where python`**。
- **⚠ 主进程 spawn python 三铁律（加载屏卡死的根治）**：
  1. **绝不用 `where python` 打头** — 在 Hermes 桌面环境里会抓到 Hermes venv 的 python 3.12（没有 uvicorn/依赖不全），后端起不来，WebContentsView 卡死在「正在启动…」加载页无限健康轮询。优先 `Framework/runtime/python/python.exe`（py3.11，已验证可跑 uvicorn+fastapi+numpy/matplotlib）。
  2. **spawn env 必须删除 `PYTHONPATH`/`PYTHONHOME`/`VIRTUAL_ENV`** — Hermes 会话把这几个变量指向 hermes venv，不清会污染子进程导致 uvicorn import 崩溃。
  3. 把 `runtime/node`、git/bin 加进 `env.PATH`，设 `PYTHONDONTWRITEBYTECODE=1` + UTF8 标志。
  启动前 `console.log('[CUMCM] Using python:', pythonExe)` 打印实际 python 路径，排查时看这一行就知道选对了没有。
- **加载屏卡死诊断顺序**：① 壳里后端起没起（netstat 端口/stdio 日志）→ ② main.js 打印的 python 路径对不对（是否 runtime）→ ③ spawn env 有无 PYTHONPATH 污染。截图「正在启动…」+ 菊花永久转 = 后端根本没起来，前端在 60 次循环重试 health。
- `backend/config.py`：`CUMCM_EMBEDDED` 环境变量切换数据目录 —— 嵌入时 `Framework/../cumcm_data`，独立时组件同级；所有路径 `Path(__file__).parent.parent` 派生，不引用 Framework 其他目录。
- `standalone.js`：不经壳直接 `electron standalone.js` 启动（spawn 后端 + BrowserWindow loadURL），验证可分离性。
- 独立端口（cumcm=18089 vs modex=18088）、独立 venv、独立数据目录 → 互不干扰。

### UI 改造为 Trigon Apple 玻璃风（http 托管页面）
- **背景壁纸自托管**：页面由后端 http://127.0.0.1:PORT 托管时加载不了 `file://` 的 shell 壁纸（manifest `wallpaper:false`）→ 把 `Framework/background.png` 物理复制进 `frontend/assets/`，`body { background-image: url("../assets/background.png"); background-size: cover }`。
- **设计令牌内联**：http 页面不能依赖 shell 的 tokens.css/glass-app.css（insertCSS 的 file:// CSS 变量在 http 页不保证生效）→ 把 `--glass/--border/--radius/--accent` 等令牌 + `.card`/`.seg`/`.btn` 全套**内联进自己的 app.css**，浅色/深色双主题。
- **固定底部操作条**（内容截断时）：左栏结构 = 滚动区 `panel-left-scroll`（flex:1 overflow-y:auto，内含全部 section）+ 固定 footer `.panel-left-footer`（flex:0 0 auto，操作按钮钉在底部，随内容滚动条一起滚动但始终可见）。
- **浏览器缓存**：uvicorn 托管 HTML 改完可能加载旧 DOM（`.panel-left-scroll` 为 null），导航加 `?t=<随机>` 强制刷新；console 里 `!!document.querySelector(...)` 确认新结构已生效再截图。
- 视觉验证用 browser_vision 问「壁纸透出/玻璃拟态/对比度/截断」，深色浅色都截一遍；layout 用 browser_console 查 `getBoundingClientRect()` 断言按钮 `bottom <= innerHeight`。

### 通用 FastAPI/图表坑
- **matplotlib 中文乱码**（Win）：注册系统字体 + rcParams：
```python
import matplotlib.font_manager as fm
for f in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
    if os.path.exists(f): fm.fontManager.addfont(f)
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei","SimHei","sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False
```
验证：`warnings.catch_warnings(record=True)` 断言无 Glyph 警告。
- **StaticFiles 挂载目录不存在 → RuntimeError 启动崩**：`app.mount("/assets", StaticFiles(directory=...))` 前先 `if assets_dir.is_dir()` 守卫（前端用分离的 css/js 时没有 assets/）。
- bash curl 传中文 JSON body 报 "error parsing the body"：改用 Python `urllib.request` 发请求，不要在 bash 单引号里写中文。