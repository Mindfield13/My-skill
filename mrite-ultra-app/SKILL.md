---
name: mrite-ultra-app
description: Mrite/M Ultra 数模 Electron 应用的架构、规则库与打包改造。
---

# Mrite / M Ultra 数模应用（Electron）

专为数模打造的桌面应用家族（Mrite v2.x → MriteUltra → M Ultra 数模），用户长期迭代的持久项目。
引擎 = Electron + Claude Agent SDK + @jtabet/anthropic-openai-bridge（OpenAI 端点自动转换代理）+ 内置 Python 3.12 + TinyTeX(xelatex) + SQLite。**引擎内核是"数模论文 AI 自动生成"**：读题→求解计划→逐题求解→写论文→编译 PDF。

## 目录与位置

- `E:\Project\M Ultra\MRITE_2.50\` — 打包版可运行应用（Mrite.exe / M_Ultra.exe + resources/）
- `MRITE_2.50\resources\app_content\` — **asar 的完整解包源码**（2.6GB，含 unpacked 大件副本；引擎所有 JS 均明文可改）
- `MRITE_2.50\resources\app.asar` (~113MB) / `app.asar.unpacked/` (python-env 1.2G、TinyTeX 604M、原生 node_modules) / `app.asar.bak`（原始）/ `app.asar.v250.orig.bak`
- `E:\\Project\\Framework\\` — **Trigon Agent 工作站**（Electron 43.4 WebContentsView 多应用壳），MRITE 作为子应用集成在 `src/apps/mrite/`，服务层在 `src/main/services/mrite/`。dataDir = `%APPDATA%\\Trigon Agent\\mrite\\`（区别于旧版 `MriteUltra`）。  
- `E:\\Project\\M Ultra\\M-Ultra-数模\\` — **从0开发的新工程**（2026-08-16 起不再走破解引擎换皮路线；`build.js` 已删除）：`src/backend/workflow.py`（自研步骤引擎：读题→求解计划→逐题求解→论文生成→编译PDF，M5 已全部跑通）+ `src/renderer/`（原生 JS + Apple Design）+ `rules-library/`（提示词内容资产，含 `solve/求解计划模板.md`，自 Mrite-main/Skill/求解/）+ `templates/`（三套模板内容资产）。架构/坑位详见 `electron-fastapi-backend`
- `E:\Project\Mrite-main\` — 核心 Skill：`Skill/CLAUDE.md`（全自动工作流）+ `模板/`（论文模板源头）+ `算法/`（骨架）
- `MRITE_2.50\resources\_crack_plain_v2\` — 全量解密交付（decryptor.js.orig / wrapper.js.orig / 解密报告）
- `E:\Project\MRITE_2.50.zip`（4.2GB）— 目录备份 zip，内含 app.asar 为 8-14 的明文重打包版（官方原始加密 asar 已不在）
- `E:\Project\M Ultra\高教社杯\` `高教社杯-数据题\` `华数杯\` — 三套论文模板源（format.cls + SourceHanSerifCN 字体 + 论文章节规范.md）
- userData = `%APPDATA%\MriteUltra\`（bootstrap.js 里 `app.setPath('userData', ...MriteUltra)` 强制指定，勿改用其它名）

## rules-library 规则库系统（★核心）

顶层结构 + 语义：

| 目录 | 作用 |
|------|------|
| `common/主引导.md` | 系统铁律 + 全自动模式 + 项目结构，装配为工作区 CLAUDE.md |
| `common/题目/读题规则.md` `common/数据/读数据规则.md` | 分阶段 Read |
| `solve/<方案名>/{求解规范.md, 求解计划.md}` | 求解方案（阶段 2 规则） |
| `paper/<格式名>/{论文章节规范.md, *.tex, format.cls, fonts/}` | 论文格式（阶段 3 规则） |
| `external/` | 外挂规则（index.md 表格驱动，**仅最高强度 xhigh 加载**，补充约束，优先级低于项目约束） |
| `user-solve/` `user-paper/` | 用户在设置里创建的自定义方案（USER_PREFIX） |
| `templates.json` | 竞赛模板索引：模板名 → solveScheme + paperFormat |

**打包态种子逻辑**（src/services/rules-library.js ensureLibraries）：
- 首次启动把内置规则库种入 userData/rules-library；源路径优先顺序：**`app.asar.unpacked/rules-library` → `app.asar/rules-library` → MRITE_REAL_RESOURCES**
  → 只改规则内容时，把目录丢进 `app.asar.unpacked/rules-library/` 即可，无需重建 asar！
- `copyMissingSafe` 只补缺失文件、**不覆盖**用户已有内容 → 升级规则库时必须在 userData 直接覆盖，或先备份再删。
- 求解方案/论文格式解析：DB settings `solveScheme`/`paperFormat`（默认 `通用`/`高教社杯`）；装配即把 `solve/<方案>/` 复制为工作区 `求解/`、`paper/<格式>/` 复制为 `论文/`。**库缺目录会装配失败**（"库缺少 求解/论文 目录"）。

## M5 状态（2026-08-17 全部跑通）

自研引擎（`src/backend/workflow.py`）5 步全流程已跑通真实赛题（高教社杯 C 题 NIPT）：
- 读题 → 求解计划 → 逐题求解 → 论文生成 → 编译PDF
- 产出 18 页 PDF（9.5/10 分），9 张图，9 个 CSV 结果文件
- 问题四（女胎异常判定）需在 `_code_prompt` 中加特殊说明：`sheet_name='女胎检测数据'`、女胎无 Y 染色体、目标列=染色体的非整倍体
- 论文标题占位符替换：`_step_paper` 末尾将 `论文.tex` 中的 `\bfseries 论文标题\par` 替换为任务名

### Windows 子进程坑（2026-08-17 修复）

`_run_script` 中 `subprocess.run` 返回 **STATUS_CONTROL_C_EXIT (3221225794 = 0xC000013A)** 且 stdout/stderr 为空：
- 原因：父进程 Ctrl+C 信号传播到子进程，`text=True` 在 Windows 上输出丢失
- 修复：① 加 `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` 隔离信号 ② 移除 `text=True`，改为 `capture_output=True` 后手动 `.decode("utf-8", errors="replace")` ③ 用 `proc.stdout_text` / `proc.stderr_text` 属性引用
- 同样问题也出现在 `env` 构造：`pop` 掉 PYTHONHOME/PYTHONPATH/VIRTUAL_ENV/PYTHONUTF8/PYTHONIOENCODING，再设 `PYTHONUTF8="1"`

### ★`_venv_python` 路径层级 Bug（2026-08-18 修复）

`_run_script` 报 `[WinError 2] 系统找不到指定的文件。` — `subprocess.run` 找不到 Python 解释器。

根因：`_venv_python()` 旧 fallback 路径 `self.task_dir / ".." / ".." / ".venv" / ...` 只能上2层到 `data/`，但 `.venv` 在项目根（`data/` 上级的上级），需要上 **3层**：
- `task_dir` = `data/tasks/<id>/`
- 旧：`..`/`..` → `data/` → `data/.venv/...` ❌ 不存在
- 正确：`..`/`..`/`..` → 项目根 → `.venv/...` ✅

修复：改用 `config.PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"` 绝对定位，不再依赖 `task_dir` 相对层级。`config` 已在模块顶部 import。

### 跳过已求解问题

`_step_solve` 中循环每个问题前检查 `(prob_dir / "图片").exists() and any((prob_dir / "图片").iterdir())` → 跳过已有结果的问题，避免重复跑。

### 修复循环改进（2026-08-17）

`_step_solve` 中 3 轮修复循环的 `last_err` 改进：
- STDOUT/STDERR 用 `--- STDOUT (末尾) ---` / `--- STDERR (末尾) ---` 标签分隔，方便 LLM 区分
- 末尾追加 `--- 数据列名（如果有）---` + `请在读取数据后用 print(list(df.columns)) 确认列名` 提示
- 截取长度从 1500/1200 改为 2000/1500 字符

### 论文生成优化（2026-08-17）

`_step_paper` 中 LLM 调用上下文缩减（减少 token 消耗，加速生成）：
- 章节规范 `spec` 截取从 3000 → 1500 字符
- 题目分析/求解计划上下文从 2000 → 1500 字符
- CSV 结果预览从 500 → 200 字符（仅列名和前几行）

## M6 功能重构（2026-08-17 晚，两轮共 12 项需求）

**最新导航顺序（第二轮定稿）：主页/任务/修改/写作/评审/文件/扩展/设置** — "文件"页恢复（思维导图），评审专注评估不再含修改组件。核心新能力：
- **AI 辅助修改已异步化**（第二轮）：`POST /api/tasks/{id}/ai-edit` 只校验并**启动后台线程**（`_ai_jobs[task_id] = {status, detail, content, error}`）+ `threading.Lock`，立即返回 `{started:true}`；前端用 `GET /api/tasks/{id}/ai-edit/status` **轮询（800ms）** detail（reading→working→done），done 后把 `content` 填入 textarea，用户确认后 `PUT file` 保存 → 单步重跑。已有 running 任务再 POST 返回 409。**前端所有 AI 按钮（modify 对话、统一弹窗、写作页）都必须走"启动+轮询"模式，不能再等同步返回值**
- **修改页重做（左右分栏）** `js/views/modify.js`：左 `.md-chat` AI 对话（消息列表 + 输入意见 + 发送 → 轮询实时反馈进度），右 `.md-grid` 产物文件分组 + 预览/编辑区。任务切换用 `<select id="md-task">`
  - **v4：预览区严禁再内嵌 AI 输入框**——第一版 `PreviewUI.render(..., {aiInstr: editable})` 在右侧预览顶部显示"给 AI 的要求"输入框被用户点名批评（"预览里面怎么还藏着AI修改"）。AI 修改入口**只留左侧对话**（modify 页）和统一弹窗，`PreviewUI.render` 一律**不再传 aiInstr**。规则：**编辑器/预览区只负责内容，所有 AI 操作入口收敛到对话面板**
- **v3：产物必须全量按目录列出**（`task.tree` 直接 map：`题目/ 数据/ 求解/ 论文/`，含 PDF 📕 / xlsx 📊 / 图片 🖼 / CSV / py / tex / md）——用户明确"修改模式是对所有产物的修改"，**不能只列 STEP_PRODUCTS 过滤的 md/py/tex**（第一版只显示两组被点名批评）。图标映射：`/\.(png|jpe?g|gif)$/i → 🖼`、`pdf → 📕`、`/\.(xlsx|xls|csv)$/i → 📊`、`tex → 📝`、`py → 🐍`、默认 📄
  - **v3→v4（第四轮定稿）：输入框固定在左侧底部 + 优雅玻璃感**：`.md-chat-input { margin-top:auto }`；textarea 使用 `background: rgba(255,255,255,.05)` + `border: 1px solid var(--hairline)` + `border-radius: 12px` + padding 10px 12px，hover 才显 40% accent，focus 才有 3px 16% accent 光晕。**用户第 3 轮嫌 v1 默认丑 → 加了 accent 背景+1.5px 边框+4px 光晕（v3）→ 第 4 轮仍嫌\"太丑\"，v4 定稿为安静玻璃感**：常态低调、hover/focus 才亮 accent。教训：输入框默认态不要堆 accent 色块/重边框，apility 用 hairline+透明底，交互态渐进亮起
- **统一编辑弹窗** `window.ModifyUI.openEditModal(tid, rel)`（modify.js 全局；各页复用，内含 AI 轮询 + 手动编辑 + 保存）
- **写作页保存后自动编译 + PDF 实时预览**：`#wp-save` 点击 → `writeTaskFile` → `autoCompileAndPreview()`（compileTask → `PreviewUI.render(...,'论文/论文.pdf')` 显示最新版本）
- **文件页 Xmind 思维导图** `js/views/view.js`：手写 CSS 树（任务=`.mm-center` 中心节点 → 目录=`.mm-dir` → 文件=`.mm-file` 叶子，`.mm-kids` 虚线连接）**v3 改为左导图右大预览面板**（`.vf-grid` 320px+1fr，点击文件 → 右侧 `PreviewUI.render` 大区域预览，**不再弹窗**——用户两次明确拒绝小弹窗）
  - **v4：折叠 + 柔和色**——用户嫌全排列太占地方（"给加收回弹出的那个小箭头"）：任务节点箭头 `tf-arrow ▾/▸`（点击折叠整个任务子树）、目录节点 `.dir-arrow ▸/▾`，**目录默认收起**（`.dir-kids { display:none }`，点击展开文件）。任务中心节点颜色**用柔和色板避开纯红**：`HUES=[215,160,270,195,330,230]`（hue=0 纯红被用户嫌"像报错"，i*50%360 第一项正是纯红）。色相语义：蓝/绿/紫/青/粉，绝不 0-30°
- **共享预览组件** `js/preview.js`（第三轮新增）：`window.PreviewUI.render(el, tid, rel, {editable, aiInstr, onSaved})` 一个入口统一 PDF/xlsx/图片/文本预览；文本支持内联编辑 + AI 轮询 + 保存。文件页/修改页/任务页/写作页全部复用
- **PDF 预览（v3 定稿）：自绘分页阅读器，禁用 iframe data:base64**——Chromium 原生 PDF viewer 工具栏显示乱码文件名/重复标题/难关闭，用户强烈不满。后端 `GET /api/tasks/{id}/pdf-info`（pymupdf 总页数）+ `GET /api/tasks/{id}/pdf-page?rel=&page=`（pymupdf `get_pixmap(Matrix(1.6,1.6))` 渲染单页 PNG base64），前端 PreviewUI.renderPdfReader 分页 `<img>` 翻页（‹ › + 页码），彻底自绘无浏览器工具栏
- **任务页/写作页 PDF 预览**：同走 `PreviewUI.render`（自绘阅读器）；xlsx 走 `GET /api/tasks/{id}/xlsx-preview`（pandas `read_excel(sheet_name=None, nrows=50)` → `df.head().to_html()` 返回 HTML 表格，前端 `.xlsx-table` 样式，`.xlsx-preview` 容器滚动）
- **评审页删除修改模式组件**：`renderEditableFiles`/`STEP_PRODUCTS` 已移除，评审只保留评估得分 + 检查项 + 评估要求 + 单步重跑
- **模型 Profile 管理**：`config.py` `DEFAULT_PROFILES`（多项配置，各含 enabled 开关）+ `get_active_profile()`（返回第一个 enabled）+ 旧版 `model` 字段自动迁移为 profiles；`llm()`/`model_test` 都改为取 profile

细节见 `references/ai-modify-profiles.md`、`references/review-modify.md`（评审/评估 API、单步重跑、Windows 路径 slash bug）、`references/m6-v2-rework.md`（第二轮重构全记录：异步 AI 轮询、xlsx 预览、思维导图、写作自动编译、MSYS curl 传参、bat 修复）与 `references/pdf-preview-reader.md`（v3：自绘 PDF 分页阅读器、PreviewUI 共享组件、修改页产物全量、pymupdf）。

## M7（2026-08-17 晚）：AI 评估 + 多任务并行 + 评审页增强

- **AI 评估**：新 `src/backend/evaluate.py`，LLM 按 5 固定维度（逻辑/模型/结果/图表/规范）对论文 tex+求解产物+评估要求（含上传文件提取文本）严格 JSON 打分；完整结果存 `评审/eval_result.json`（**只存 task.json 摘要会致前端无维度卡**）；评估接口走"启动+轮询"异步模式（同 ai-edit）。实测对 M2 测试任务打出 48 分，评论专业
- **多任务并行**：后端本就支持（每任务独立引擎+线程+目录），补充 `_meta_lock`(RLock) + task.json 原子写（tmp→replace）防并发写坏；并发压力测试 0 错误
- **评估要求上传**：`POST .../requirements/upload` 收 base64 JSON（渲染进程拿不到 File.path，用 arrayBuffer→btoa），存 `任务目录/评估要求/`，支持 PDF/DOCX/图片；带列表+删除
- **评审页**：删失效"任务详情"按钮（用户点名）；卡片 = 文件检查(`.review-eval`) + AI 评分 hive(`.review-ai-eval`) + 要求(`.review-req`)
- **扩展页**：规则库浏览器上线（`GET /api/rules` 递归树 + `GET /api/rules/read` 带路径越权防护；左侧 `.ext-grid` 目录树 + 右侧轻量 markdown 渲染）
- **M7.3 多模型交火（已实现+实测 2026-08-17）**：制作者-审核者循环（用户原话"一个制作一个审核不断的提出问题审核质量"）——主模型生成 → 审核者（另一 profile，`get_reviewer_profile()` 自动选非主模型，不能是主模型自己）挑问题/打分(JSON {score,pass,issues,suggestions}) → 主模型按意见修改 → 再审核…。config 新增 `crossfire` 节（enabled/reviewer/rounds/threshold）；接入 `_step_solve`（`_crossfire_solve`：改代码→写临时文件重跑验证，失败回退不破坏成功产物）与 `_step_paper`（`_crossfire_text` 整篇交火，记录写 `交火记录.md`）。设置页新增"多模型交火🔥"卡片（iOS 滑块 + 审核者下拉 + 轮数 + 阈值）
- **★llm.py `_normalize_base` URL 规范化坑（2026-08-17 修复）**：旧实现盲目给非 `/v1` 结尾补 `/v1` → 用户贴完整端点（`https://api.deepseek.com/chat/completions` 或 `.../v1/messages`）被拼成 `.../chat/completions/v1` → 404。修复三步：① 先裁剪完整方法端点（`/v1/messages`、`/v1/chat/completions`、`/chat/completions`）回基础 URL ② 已带版本路径（`/v1`、`/v2`、`/api/v1`）原样保留 ③ 仅裸域名补 `/v1`。规则：**LLM 客户端必须兼容用户贴入的任意 URL 格式**
- **★前端类复用坑（cf-switch 错位）**：iOS 滑块样式**不能复用 `.toggle-btn`**——那是给模型 Profile 的圆形单选（22px 圆+2px 边框+flex 居中），与轨道+内嵌 knob 的 inline 样式冲突→视觉错位。独立 `.cf-switch` 类用 `::after` 伪元素做滑块（`left` 2px↔22px 动画）；颜色用主题变量（轨道 `color-mix(in srgb, var(--text-3) 35%, transparent)`、knob `var(--panel)`+阴影）——**白轨道 `rgba(255,255,255,.12)` 在浅色主题下隐形**，浅色/深色均可见
- **★商汤推理模型兼容（"测试卡住"根因）**：sensenova-6.8-flash-lite（及一切推理模型）OpenAI 兼容响应把思维链放 `message.reasoning` 而非 `content`，小 max_tokens（16/32）会被思维链吃光 → content 空 → 解析报错像"卡住"。修复：`_parse_reply` 兼容 reasoning 兜底 + `test_connection` max_tokens 16→512（实测 55s 失败→3.1s 成功）+ 设置页测试按钮 15s 慢速提示。官方端点 `token.sensenova.cn/v1`（ms 商汤 API）真实 key 可直连

### ★前端即时保存模式（2026-08-17 修复"交火开了又自关"）

用户报：设置页开启交火 → 去主页 → 返回设置 → 开关又变回关闭。根因：`#cf-enable` 的 click 只切 `.active` class（DOM 内存态），**必须点"保存全部配置"才写盘**；没保存就离开，SPA 重渲染从 config.json 读回 false。修复：交火字段（开关/审核者/轮数/阈值）任一变更都调 `saveCrossfire()` 自动 `PUT /api/config`——开关点击后 `setTimeout(saveCrossfire, 50)`（等 class 先切换），下拉/数字用 `change` 事件（**不用 `input`**，打字会狂发请求）。规则：**任何"一改就想生效"的 UI 控件，变更事件必须立即写后端，不能依赖独立保存按钮**；切页重渲染会从后端重读，未落盘的 DOM 态必然丢失。

### cc-switch provider 结构（M Ultra 换模型参考）

cc-switch 数据在 `~/.cc-switch/cc-switch.db`（SQLite）：`providers` 表（id/app_type/name/settings_config/**is_current**）、`provider_endpoints`、`proxy_config`（claude 代理 127.0.0.1:15721）。**同名 provider 按 app_type 分开**（如 SenseNova × claude/codex/gemini/claude-desktop/hermes 各一条）；`app_type='claude' 且 is_current=1` 的 provider 才是 M Ultra "cc-switch 默认" profile（base=http://127.0.0.1:15721）实际转发的后端。切 cc-switch provider 后 **M Ultra 的 model 名也要同步改**（代理对不认识的非 claude-* 模型名多透传，可能报错）。推荐做法：M Ultra 建多个 profile（相同 base + 各自 model 名），应用内点启用开关切换，少依赖 cc-switch 手动切。

细节见 `references/m7-ai-eval-multitask.md`。

### M7.5 产出质量提升闭环（2026-08-17 用户选 1~6 全做）

**★论文标题差劲根因 + 修复**：`_step_paper` 旧逻辑 `title = meta.get("name")` 把**任务名**（如 "C"、"导出测试"）直接当论文标题 → 用户问"为什么论文题目都特别差劲"。修复：先生成/读取 `求解/论文题目.md`（LLM 按《题目分析》提炼 15~28 字「基于XX方法的XX建模」标题，可人工编辑后重跑），存在则用它替换 `论文.tex` 的 `论文标题` 占位符，任务名只兜底。**产出物凡是能由内容推导的（标题/摘要），绝不用任务元数据（name）硬塞**。

**★推理模型"无文本"偶发 + 重试**：deepseek-v4-flash（推理模型）偶发响应只有 `content:[{type:"thinking",...}]` 无 text 块 → `_parse_reply` 抛"响应无文本内容"。修复：`LLMClient.chat` 捕获 `LLMError("无文本内容")` 自动重试（最多 3 次，1.5s 退避），429 限流保留 3 次，for 循环扩到 range(8)。**短调用（标题提炼等）max_tokens 必须 ≥512**（同 sensenova 规则，思维链吃 token）。

**★配置数值腐坏 → HTTP 400 "invalid arguments"（2026-08-17 线上失败）**：`_step_solve` 修复循环报 `HTTP 400: {"error":{"type":"invalid_request_error","message":"invalid arguments"}}`。根因：config.json 三个 profile 的 `max_tokens` 全被写成 **`1e+25`（float 科学计数法）**（来源不明，可能历史保存路径写入），`LLMClient.__init__` 的 `int(1e25)` 变成 10^25 → 服务端拒绝。诊断：直接 `print(profile.get('max_tokens'))` 看是否为 float/超大数。三层修复：① `LLMClient.__init__` 防御 clamp：`mt = int(...)` 后 `mt if 1 <= mt <= 16384 else 8192`（try/except 兜底非数字）——**客户端必须对配置数值字段做范围校验，任何发往服务的请求参数都可能被脏配置污染** ② 修复 config.json 数据（脚本遍历 profiles 改回 8192）③ 设置页 `collectProfiles` 兜底：`Number.isFinite(n) && n >= 1 && n <= 16384 ? n : 8192`（不要再 `parseInt || 8192` 一把梭）。另注意 `self.timeout = int(cfg.get("timeout", 600))` 同样可能被腐坏。

**★Python 局部 import 陷阱（心里有坑才抓得到）**：函数内任何 `import time` 使整个函数作用域 `time` 变局部变量 → 未走该分支的 `time.sleep()` 抛 `UnboundLocalError: cannot access local variable 'time'`。修复：删局部 `import time`，用模块顶层导入。教训：**函数内不要局部 import 顶层已导入的模块**；行为验证（连续真实调用）能暴露这类偶发错。

**★CDP 截 Electron 窗口 hidden 陷阱（截图挂起的真凶）**：`document.visibilityState === "hidden"`（用户把窗口最小化/切走）时 `Page.captureScreenshot` **挂起永不返回**（fromSurface:true/false 都无效）；`Page.bringToFront` **对已最小化的 Electron 主窗口无效**（可见性仍是 hidden）。解决办法：**taskkill 重启 Electron**（新窗口默认显示，`visibilityState=visible` 后截图立即正常）。诊断顺序：先 evaluate `document.visibilityState` → hidden 就重启再截。工具：`tools/cdp-one.js`（响应驱动：bringToFront→gotoView→等1.5s→captureScreenshot，**必须用 `ws.addEventListener` 不能 `ws.onopen`**——Node 原生 WebSocket 不认 onopen 属性）；批量截图见 `tools/cdp-all-pages.js`。

**产出质量提升四件套**（workflow.py）：
- **EDA 前置**：新 `src/backend/eda.py` 用 pandas 读 数据/ 前 5000 行 → `求解/数据概况.md`（每列 dtype/缺失/唯一值/min-mean-max/样例）→ 读题与代码生成 prompt 都注入《数据概况》（"列名以这里为准，不要臆测"）。实测减少猜列名报错循环。
- **论文分步生成**：一次 12000 tokens 一锅炖易出占位符 → 改为 ①LLM 生成《论文大纲.md》②逐章独立调用（每章只输出该章 LaTeX，max_tokens 6000）③**摘要 0.摘要.tex 殿后**（能收束全文）。交火整篇审核改为"只评不改"（存档 交火记录.md，不破坏分章）。
- **多方案采样**：每题生成 2 份代码（temperature 0.4/0.9），各在 `问题X/方案N/` 隔离目录运行，按 `(ok?1000:0)+图片*10+结果*1` 选优合并到标准 图片/结果/；都失败才进 3 轮修复循环。
- **小样本硬约束**：代码 prompt 加"样本量 <30 禁止时间外推/复杂 ML；列名读取后 `df.columns.str.strip()`"。

**评估闭环（轻量）**：评审页 AI 评估卡片下加"根据评估建议重跑"按钮组——`suggestSteps()` 对 weaknesses/suggestions 做关键词匹配（占位符/未生成→paper；求解/数据/模型→solve；编译/PDF→compile…），点击直接 `API.runStep`。实测 M2 评估自动推荐 [论文生成, 逐题求解, 编译PDF]。

**★urllib 不自动编码中文 URL**：Python `urllib.request` 直接拼中文 query **抛 UnicodeEncodeError/400**，必须 `quote(path, safe=":/?=&%")`。curl 拼中文 URL 也会 400 "Invalid HTTP request"（git-bash 编码问题），API 冒烟脚本一律用 Python + quote。

细节见 `references/m7-quality-upgrades.md`。

#### ★math-skills 竞赛技能库导入（2026-08-17）

用户把整套 Mrite 竞赛 skill（`E:\Project\M Ultra\数学建模竞赛\`，11 个 `comp-*`：prob-analysis 赛题分析 / modeling 建模 / code 编程 / review 逻辑复核 / paper-zh|en 论文 / compile-zh|en 编译 / stats-topic 选题 / 各 docx 变体）要求"做成软件可用的 skill"。落地方式（三件套，勿改架构）：
- **整体入库**：明文 `SKILL.md` + references + 模板（跳过 `.enc` 加密、`*.ttf/ttc/otf` 字体）复制到 `rules-library/math-skills/<skill-name>/`（5.3MB / 69 文件）→ 扩展页规则库树自动显示（`/api/rules` 递归已覆盖）
- **_wire 抽取**：`tools/extract_math_skills.py` 按 `## ⛔铁律/规模警示/硬门禁/合理性预验证` 章节抽取各 SKILL.md → `math-skills/_wire/<step>.md`（read_problem / solve_plan / solve / paper / review / compile / topic）——**不要整体注入交互式 SKILL.md**（含 FAST_MODE 检测等 Claude Code 专属指令，占 token 且跑不动）；注入一律 `[:2200~2500]` 截断
- **步骤接线**：`_step_read_problem` 读 `_wire/read_problem.md`、`_step_solve_plan` 读 solve_plan、`_code_prompt` 读 solve、`_step_paper` 读 paper、`evaluate._build_system_prompt` 读 review（对抗复核检查要点：方向反/重复计量/外推过硬/漏变量/跨问矛盾）

#### ★求解代码提取容错 + 问题归一化（2026-08-17 线上失败修复）

用户线上跑了 3 轮全失败：`问题4_求解.py` 第一行是 ` ```python ` → `SyntaxError: invalid syntax`。根因：deepseek 输出**被 max_tokens 截断、代码块无闭合 ```` ``` ````**，旧 `_extract_python` 正则要求闭合 → 匹配失败返回原文（含 ``` 头）→ 写入 .py 即语法错。修复（workflow.py）：
- **`_extract_python` 四层容错**：① 完整闭合代码块 ` ```(?:python|py)?\s*\r?\n(.*?)``` ` ② 去 `\r\n` 再匹配 ③ **未闭合代码块**：取第一个 ```python 之后到末尾（截断兜底，同时 `self._log` 告警\"代码块未闭合/疑似截断\"）④ 无标记则 `.lstrip("`")`
- **多方案采样 max_tokens 4000→8000**（中文代码 4000 必截断）
- **`_find_problems` 归一化去重**：求解计划里\"问题1/问题一\"混写曾被识别成 8 个问题（重复求解）；数字 key 统一转中文（`1→一`），CN_NUM 排序，`found[:8]`
- **`_plan_section` 兼容数字写法**：正则 `问题(?:{中文}|{数字})[：: ]` 双 match
- 验证用 T1-T5 针对性脚本（复现失败文件提取干净 / CRLF / 带前缀代码块 / 去重清单 / 数字章节抽取）

### M7.4 新建任务增强：上传文件 + 输出目录导出（2026-08-17 用户硬性要求）

用户原话「你不让我上传文件，你也不让我配置输出路径，你懂做题吗」——**做题第一步必须能传赛题文件+配置产物输出位置，新建任务流程不能只有名称/模板/方案**。规则：任务创建即支持文件选择（创建后立刻 attach），且每个任务可选输出目录。

- **新建任务弹窗**（`tasks.js openNewTaskModal`）：名称 → 📎 选择文件（系统对话框多选，显示文件名列表）→ 模板 → 方案 → 输出目录输入框 + 📂 浏览…
- **任务详情页**新增两按钮：
  - `📎 上传文件` → `API.attachFiles`（创建后随时补传题目/数据）
  - `📤 导出` → `POST /api/tasks/{id}/export`：把 `论文/论文.pdf|tex` + `求解/` 下全部 png/jpg/csv/xlsx（相对路径下划线化平铺）复制到 `task.json.output_dir`，成功后 `mUltra.openPath(dir)` 打开文件夹
- **★模态弹窗溢出坑（用户批评\"弹窗和屎一样\"）**：`UI.openModal` 的内容**不要再套 `<div style="width:min(560px,92vw)">` 内层容器**——`.modal` 自身已有 `width:min(560px, calc(100vw-60px)) + padding:24px`，内层再限宽会使内容（input/按钮）右贴边、\"创建\"按钮被截断、出现水平滚动条。修改页多版弹窗曾复用此坑。弹窗内 flex 并列输入框+按钮时：输入框加 `min-width:0`、按钮加 `flex-shrink:0`。改完弹窗验证三件套（CDP `scrollWidth>clientWidth` 判断无横向溢出 + 截图确认按钮完整 + 无误贴边）
- **★Electron 43 文件/目录选择坑**：`File.path` 已被移除，且 **contextBridge 不能传 File 对象**（`webUtils.getPathForFile` 只适合 preload 内同步调用）。正确方案：主进程 `dialog.showOpenDialog` → 新 IPC `dialog:pick-files` / `dialog:pick-dir` → preload `pickFiles()/pickDirectory()` → 前端 `UI.pickFiles()` 优先走 `mUltra.pickFiles()`（浏览器调试模式 fallback：`<input type=file>` + `webUtils.getPathForFile`）
- **后端**：`TaskCreateReq.output_dir` 存 task.json；`task_export` 用模块顶部 `import time`（**create_task 里的局部 import 不覆盖其它端点**）；导出端点收到 500 用 `process poll/log` 查 FastAPI traceback
- **★task_delete 导入坑**：`_engines`/`_engine_lock` 定义在 **main.py** 模块级，`task_delete` 曾写 `from workflow import _engines` → ImportError 500（软删除/导出测试必踩）。同文件内直接用模块级变量，不要跨模块 import 本文件的变量

细节见 `references/new-task-upload-export.md`。

### 一键启动脚本更新（2026-08-17 两版）

`启动.bat` — 双击启动后端 + Electron。**用户实测第一版（`start "" "node_modules\.bin\electron.cmd" .`）启动后看不到界面**，第二版改用 `electron.exe` 直接调用 + `/d` 指定工作目录后正常：

```bat
@echo off
chcp 65001 >nul
set "PROJ_DIR=E:\Project\M Ultra\M-Ultra-数模"
cd /d "%PROJ_DIR%"
start "MUltra-Backend" /min cmd /c "set PYTHONPATH= && set PYTHONHOME= && set VIRTUAL_ENV= && set PYTHONUTF8= && set PYTHONIOENCODING= && set M_ULTRA_PORT=18113 && .venv\Scripts\python.exe src\backend\main.py"
timeout /t 5 /nobreak >nul
start "" /d "%PROJ_DIR%" "node_modules\electron\dist\electron.exe" "%PROJ_DIR%"
```

关键：
- Windows cmd 中清除环境变量用 `start` + `cmd /c "set A= && set B= && command"`（**不能用 Linux 的 `env`**）
- 启动前端用 `electron\dist\electron.exe`（**不要用 electron.cmd**，实测新窗口不继承工作目录 → 找不到 package.json → 无窗口）；`/d` 显式指定项目目录
- 排障顺序：`netstat -ano | findstr 18113` 找到占用 PID → `taskkill /F /PID <pid>`（**绝不用 `taskkill /F /IM python.exe`**，会误杀 Hermes 自身后端导致会话中断）

### 前端 UI 打磨（2026-08-17）

**★用户交互铁律（多次点名）**：**改 UI 前必须先明确要改哪个页面/哪个层级**——用户原话「你修改个蛋啊，你要明确是那个层级再修改」。「整体调节全部UI界面」这类宽泛改动会被拒绝（看不到进展），正确做法：先列出页面层级（主页/任务/修改/写作/评审/文件/扩展/设置）与具体区域，确认后再动手。**布局必须利用满可用空间**——用户原话「你要利用好这些区域，你倒是填满啊，你没看预览PDF和其他文件超级窄吗，你留个空白什么意思」：右侧预览/内容区要让 flex:1 撑满面板，禁止留大片空白；改动后截图 + vision 验证。

详见 `references/ui-polish.md`，关键模式：
- **分段控制器**：必须绑定 click 事件切换 `active` 类，仅静态渲染不够
- **响应式布局**：`detail-grid` 在 <1000px 时切单栏，`form-row` 切 column
- **面板缩放一致性**：所有面板的 `panel-inner` 统一用 CSS 的 `max-width: 1200px`，不用内联 style
- **步骤时间线**：`.step-circle` + `.step-row::before` 伪元素连接线 + `stepPulse` 呼吸动画
- **编译按钮**：状态机流转（⏳ 编译中 → ✅ 成功 / ❌ 失败 → 3s 恢复）

## Trigon Agent MRITE 集成（2026-08-20 状态）

MRITE 作为 Trigon Agent 的子应用（`src/apps/mrite/`）运行，不再独立启动。关键集成点：

### 数据目录
- `%APPDATA%\\Trigon Agent\\mrite\\` — workspace/ + rules-library/ + sqlite DB
- DB 在 `%APPDATA%\\Trigon Agent\\data\\mrite.db`
- 旧版 `%APPDATA%\\MriteUltra\\` 不再使用

### 服务层
- `src/main/services/mrite/index.js` — 懒初始化 db/workspace/rules-library/task，注册 IPC
- 规则库 seed 路径：dev 下 `MRITE_BUILTIN_RULES` 环境变量或 `E:/Project/MRITE_2.50/resources/app_content/rules-library`（硬编码，需迁移到 `assets/rules-library/`）
- 预热：`setTimeout` 1500ms 后后台加载 SDK / python / latex 环境

### 导出功能修复（2026-08-20）
`getCustomOutputPath` 原返回 `''` 空字符串 → `syncOutput` 跳过导出。修复后从 DB 读取 `outputPath` 设置并解密：
- AES-256-GCM 密文格式: `ivHex:authTagHex:ctHex`（`crypto.createCipheriv('aes-256-gcm', key, iv)`）
- 密钥 = SHA256(machineCode + '|mrite-db-v2')
- IV 是 12 字节 = 24 hex 字符（不是 16 字节 = 32 hex！）
- 机器码 = SHA256(hostname|cpuModel|platform|totalMem)[:16].upper()
- ⚠️ 必须在 Node 侧算机器码，Python `platform.processor()` 返回的 CPU 字符串不同 → AES-GCM InvalidTag

### 防造假机制（2026-08-22 新增）

**背景**：AI 在求解中可能造假——生成空图、空CSV、论文引用不存在的图/数值、使用占位符。只要代码能跑不报错，runner 就标记 complete，不会验证产物质量。

**三层防御**：

1. **Prompt 规则增强**（`rules-library/solve/Mrite_*/求解规范.md` 第九章「⛔ 防造假守则」）：
   - 代码必须真实运行并验证输出（打印路径、行数、文件大小）
   - 每个问题求解后必须运行 `python 求解/验证脚本.py .`
   - 论文引用必须对账真实文件（`\includegraphics` 路径存在、CSV 有数据行）
   - 禁止省略号/占位符、禁止引用不存在的图/表编号
   - 论文中的 `tabular` 数据必须来自真实 CSV 输出

2. **验证脚本**（`rules-library/solve/Mrite_*/验证脚本.py`，同步到 `tools/verify_outputs.py`）：
   - 检查 `问题X/图片/`：图片文件非空（>200 bytes）、PIL 可打开、尺寸合理（≥50×50）
   - 检查 `问题X/结果/*.csv`：有数据行（仅表头=失败）
   - 检查 `论文.tex`：无占位符（省略号/TODO/待填）、`\includegraphics` 引用指向真实文件
   - 检查 `论文.pdf` 存在且体积合理
   - 验证不通过 → exit code 1，AI 必须修复后再继续

3. **论文规范防造假**（`rules-library/paper/*/论文章节规范.md` 第七章「⛔ 论文防造假守则」）：
   - 写论文前读取验证脚本输出确认产物真实
   - 写论文后再次运行验证脚本确认
   - 逐条核对 `\includegraphics` 路径、数值与 CSV 匹配

**关键文件**：
- `rules-library/solve/Mrite_中等/求解规范.md` — 防造假守则源（同步到快速/高级）
- `rules-library/solve/Mrite_中等/验证脚本.py` — 验证脚本（同步到快速/高级）
- `rules-library/paper/*/论文章节规范.md` — 论文防造假守则（高教社杯/数据题/华数杯）
- `rules-library/tools/verify_outputs.py` — 验证脚本主文件

### 防造假机制（2026-08-22 新增）

**背景**：AI 在求解中可能造假——生成空图、空CSV、论文引用不存在的图/数值、使用占位符。只要代码能跑不报错，runner 就标记 complete，不会验证产物质量。

**三层防御**：

1. **Prompt 规则增强**（`rules-library/solve/Mrite_*/求解规范.md` 第九章「⛔ 防造假守则」）：
   - 代码必须真实运行并验证输出（打印路径、行数、文件大小）
   - 每个问题求解后必须运行 `python 求解/验证脚本.py .`
   - 论文引用必须对账真实文件（`\includegraphics` 路径存在、CSV 有数据行）
   - 禁止省略号/占位符、禁止引用不存在的图/表编号
   - 论文中的 `tabular` 数据必须来自真实 CSV 输出

2. **验证脚本**（`rules-library/tools/verify_outputs.py`，同步到 `solve/Mrite_*/验证脚本.py`）：
   - 检查 `问题X/图片/`：图片非空（>200 bytes）、PIL 可打开、尺寸≥50×50
   - 检查 `问题X/结果/*.csv`：有数据行（仅表头=失败）
   - 检查 `论文.tex`：无占位符、`\includegraphics` 引用指向真实文件
   - 验证不通过 → exit code 1，AI 必须修复后再继续

3. **论文规范防造假**（`rules-library/paper/*/论文章节规范.md` 第七章）：
   - 写论文前读取验证脚本输出确认产物真实
   - 写论文后再次运行验证脚本确认
   - 逐条核对 `\includegraphics` 路径、数值与 CSV 匹配

4. **Runner 后置自动验证**（`runner.js` result 分支）：
   - 任务完成后自动运行 `求解/验证脚本.py`
   - 验证通过 → 正常标记完成并导出
   - 验证失败 → 标记 error（不标记 completed），前端显示失败原因，提示「继续」修复
   - 旧任务（无验证脚本）自动跳过，不报错

### 模板更新（2026-08-20）
- 高教社杯/高教社杯-数据题：`论文.tex` 和 `论文章节规范.md` 中移除 `\\tableofcontents`
- 新增页数规则：总页数不超过30页，控制在25页以内
- 规则同步到 `solve/Mrite_中等/求解规范.md`（各章篇幅控制建议）
- userData 规则库（`%APPDATA%\\Trigon Agent\\mrite\\rules-library/`）需单独覆盖，`copyMissingSafe` 不更新已有文件

### UI 设计原则（用户明确）
- Trigon 的现有设计系统（tokens.css + glass-app.css + 组件类）就是标准
- MRITE 的 UI 应该使用 Trigon 的 CSS 变量和组件类，而不是自己的独立样式
- 所有 `bg-white`、`text-zinc-*`、`border-zinc-*`、`shadow-sm` 替换为 `var(--glass)`、`var(--txt)`、`var(--border)`、`var(--shadow-sm)`
- 自定义按钮 → `btn` / `btn-primary` / `btn-ghost` 类
- 自定义输入框 → `input` 类
- 自定义卡片 → `glass-card` 类
- 自定义分段选择器 → `seg` / `seg-item` 类
- 自定义徽标 → `badge` 类
- 设置面板（模型提供商/主题/API Key）应合并到 Trigon 全局设置，MRITE 只保留规则库/模板/环境路径等独有配置
- 授权/激活/公告轮播等无用代码删除

## CUMCM 第三组件（2026-08-21 从0搭建，核心照搬 Modex）

Framework 内第三个组件 `src/apps/cumcm/`（🏆 竞赛工作台）——**核心架构/底层资产/解题逻辑来自 Modex，UI 用 Trigon 设计语言，运行时与 Modex/Mrite 完全隔离**。用户明确定位：不干扰、可分离（关键时拎走）、只借鉴核心不引用运行时文件。

要点（完整模式见 `electron-shell-framework-dev` skill 的 "Integrating a third-party component with asset 照搬" 章节 + `references/modex-asset-copy-separable-component.md`）：
- **资产物理照搬**：`cp -r modex/skills → backend/skills`（92 目录/181MB，SKILL.md 明文+`.enc` 双份共存，照搬即可用无需解密）+ `modex/tools → backend/tools`（14MB）+ `modex/templates → backend/templates` + katex 到 `frontend/vendor/katex`。**陷阱**：`cp -r` 到已存在目录产生 `skills/skills_cache` 嵌套，先 `rm -rf skills` 再复制。
- **隔离**：独立端口 18089（Modex 18088）、数据目录 `Framework 同级 cumcm_data/`（config.py 用 `CUMCM_EMBEDDED=1` 切换嵌入/独立路径）、`standalone.js` 脱离壳直接跑。
- **SkillRegistry 双格式**：Modex 的 88 个 skill 是 SKILL.md frontmatter 格式（MdSkill），引擎内建（final-package）放 `engine/builtin_*.py` 显式 `from engine.xxx import Xx` 注册（裸 import 顶层 sys.path 找不到）。
- **模板 skill 引用对齐真实 id**：自研模板（templates/cumcm_a.py 等）的 skill_name 必须写 Modex 真实 id（comp-prob-analysis/comp-modeling/comp-code/comp-paper-zh/comp-review/comp-compile-zh/paper-figure/paper-figure-drawio/quality-check/auto-paper-improvement-loop），不要用自造占位名；验证脚本 `reg.get(s.skill_name)` 全非 None。
- **UI**：前端自托管壁纸（`framework/background.png → frontend/assets/`），卡片 `var(--glass)`+`blur(34px) saturate(210%)`；左栏拆 `.panel-left-scroll`（可滚）+ `.panel-left-footer`（固定底部 CTA 按钮）；结果区加 `--glass-weak` 底保对比度。

## 任务流水线（src/services/task/）

- `prompt.js`：buildPrompt 铁律（工作区边界/禁 cd ..、无数据→模拟数据标注、中文、找不到即没有）+ preBlocks 注入（外挂规则 xhigh + solve-intensity）；`buildResumeContext` 断点续跑；`getResultErrorMessage`/`normalizeError` 错误翻译表（401/402/429/超时/网络 → 用户可读提示）
- `runner.js`：Claude Agent query 执行；maxTurns 2000、stuckTimeout 1h（config.js）
- `pre-read.js`：异步预读题目/数据（spawn python 提取 PDF/DOCX/xlsx → 题目内容.txt / 数据摘要.txt）
- `watcher.js`：监视工作区文件 → UI 进度
- `executable.js`：python/latex 可执行探测
- UI 进度依赖 AI 对话中输出带 ✅/🔄/⏳ 的编号计划列表（求解规范.md 必须要求 AI 定期重发完整列表）

## 环境与有效性 PATH

`buildEffectivePath`（task/index.js）：注入 python-env + TinyTeX bin 到 PATH 前部，并**过滤**系统 PATH 里的外部 tex/python（防止误用系统版）。Python: `assets/python-env/win-x64/python.exe`；LaTeX: `assets/TinyTeX/bin/windows/xelatex.exe`（app_content 里另有 src/env/python.js + latex.js 探测逻辑）。

## asar 打包要点（本应用特有）

- 打包必须 unpack：`assets/python-env`、`assets/TinyTeX`、`node_modules/@anthropic-ai`、`@img`、`@napi-rs`、`better-sqlite3`、`sharp`（原生 .node 无法从 asar 内加载）。漏了 → 体积 113MB→2.7GB 且原生模块报错。
- **CLI `npx asar pack --unpack-dir "a,b,c"` 逗号明文列表静默无效**（2026-08-16 实测产出 2.69GB）。必须用 Node API `asar.createPackageWithOptions(src, out, {unpackDir: ['**/python-env/**', ...]})` 的 glob 数组（详见 electron-asar-modification skill）。打包后**立即校验体积**≈原 asar。
- **版本号绑定解密密钥**：`preload-bootstrap.js` 的 deriveKey 用 `sha256(appVersion + ':' + KEY_SALT + ':partA')` XOR 注入的 keyPartB/C 解压 preload 密文 → **改动 package.json version 会破坏解密**（当前破解版是明文 JS，encrypted 分支未走，但版本仍被 deriveKey 读取）；升级版本号前必须确认密文分支未启用。
- main.js 先 `require('bytenode')` 支持 .jsc 字节码（破解版全明文 .js）。

## 品牌化地图（Mrite → M Ultra）

只改可见字符串，**内部标识符 `window.Mrite` / `Mrite._xxx` 函数名/事件名一律不动**（数百处引用，改了必炸）：
- `renderer/index.html`：splashBrand+splashTag（L22）、标题栏（L28）、首页 home-brand（L70）、设置 logo alt+app-name（L671/673）、使用条款 terms-lead（L1112）、版本号显示 v2.5.0（可留）
- `renderer/panels/dashboard.js`：作者的话 desc + 竞赛日程卡文字
- `renderer/panels/settings.js`：补丁文件对话框 title/filters
- `src/core/bootstrap.js`：启动错误框 showErrorBox('Mrite 启动失败')
- `package.json`：name/description/author
- 应用根 `首次运行看这里.txt`（asar 外）

## settings 修复铁律（多会话踩坑沉淀）

- **`fetch-server-api-config` IPC handler 必须只读**：若它在返回前写 DB，渲染进程启动时用空值覆盖用户配置 → 症状"设置保存后消失"。保存只走 `db-save-settings`。
- 接收值的 handler 加 `v !== ''` 守卫跳过空串。
- 排查顺序：先查 DB 实际数据 → 再改 handler → 追踪完整 IPC 链（fetch-server-api-config / user-me-update / db-save-settings）。
- crypto.js decrypt 需兼容旧 AES-256-GCM 密文（历史版本换过密钥结构）。

## 数模全自动方案设计（Mrite-main 核心 Skill 映射）

`rules-library/solve/数模全自动/` 是权威方案，源自 `Mrite-main/Skill/CLAUDE.md`：
- 全自动模式铁律：禁止提问/禁止中断/一次跑完/编译后自动排版优化/找不到即没有
- 目录结构：题目/ 数据/ 求解/{求解计划.md, 预处理数据.csv, 问题X/{py, 图片/, 结果/}} 论文/{论文.tex, format.cls, fonts/, 章节tex}
- 输出铁律：结果表一律 CSV（utf-8-sig, index=False, 中文名）；matplotlib 仅（禁 seaborn）；ML 仅 PyTorch；先算后画（每题 4-6 图）；图上不 set_title（标题归 \caption）
- Windows 中文路径防坑：禁手写中文绝对路径，一律 `BASE_DIR=os.path.dirname(os.path.abspath(__file__))` 推导；禁 `python -c` 内联中文
- 脚本头两行 UTF-8 包装必须；plt 中文字体 rcParams + axes.unicode_minus=False
- 求解计划六章：总体方向/各题思路/输出标准/操作步骤/文件清单/异常预案（排版禁 Markdown 表格，用列表）
- templates.json 三模板（高教社杯/高教社杯-数据题/华数杯）→ 都映射 solveScheme=数模全自动
- **高教社杯最新要求（2026-08-20）**：论文不要目录，总页数不超过30页控制在25页以内。`论文.tex` 和 `论文章节规范.md` 中已移除 `\\tableofcontents`，`求解规范.md` 中已添加篇幅控制建议（摘要1页、引言1-2页、模型假设+符号说明1页、各问题3-5页合计≤15页、检验评价改进2-3页、参考文献+附录1-2页）。
- 修改规则库后需同步到 userData（`%APPDATA%\\Trigon Agent\\mrite\\rules-library/`），直接覆盖文件，不要依赖 `copyMissingSafe`。

## 验证清单（改动后必做）

- [ ] `node --check` 改过的 JS（中文路径下可能误报 MODULE_NOT_FOUND——lint 显示 pre-existing 即 OK）
- [ ] `python -m py_compile` 改过的 Python
- [ ] 全流程验证：创建任务 → 上传附件 → 提取 → run → 轮询 progress → 检查步骤状态 → 检查 PDF 产出
- [ ] 跳过已求解问题：已有结果的任务重新 run 时跳过已成功的步骤和问题
- [ ] 论文标题：`论文.tex` 中 `\\bfseries ...\\par` 行显示任务名而非"论文标题"
- [ ] 子进程隔离：`subprocess.run` 含 `CREATE_NEW_PROCESS_GROUP`，无 3221225794 崩溃
- [ ] 设置页协议切换：Anthropic/OpenAI 兼容按钮点击后高亮切换
- [ ] 设置页 Profile：多配置卡片、启用开关互斥、添加/删除、保存后 config.json 的 `profiles` 正确
- [ ] 配置数值合法性：config.json 所有 profile 的 `max_tokens` 是 1~16384 的 int（曾出现 `1e+25` float → LLM 全链路 HTTP 400）；`LLMClient` 构造后 `max_tokens` 在合理范围
- [ ] AI 修改（异步）：modify 页左侧对话发意见 → 轮询 status 显示 reading→working→done 进度 → 内容填入右侧 → 💾 保存 → 单步重跑；已有任务运行中再发返回 409
- [ ] 写作页：点 .tex → 右侧 textarea 可编辑；保存 → 自动编译 → 自绘阅读器显示最新 PDF
- [ ] 任务页：点 PDF → 自绘分页阅读器（无 Chromium 工具栏/乱码）；点 xlsx → HTML 表格预览（前 50 行）
- [ ] 评审页：无"修改模式"组件，仅评估得分/检查项/评估要求/单步重跑
- [ ] 文件页：左思维导图（`.mm-center` 任务 → `.mm-dir` 目录 → `.mm-file` 文件）+ 右大预览面板（PreviewUI：PDF 阅读器 / xlsx 表格 / 图片 / 文本编辑+AI），**点文件不进小弹窗**
- [ ] 修改页：产物按目录全量列出（题目/数据/求解/论文，含 PDF 📕 xlsx 📊 图片 🖼）；点文件右栏 PreviewUI 预览；PDF 不出 Chromium viewer
- [ ] 修改页 AI 输入框：位于左栏底部（`.md-chat-input margin-top:auto`）+ accent 主题色边框/聚焦光晕
- [ ] 导航顺序：主页/任务/修改/写作/评审/文件/扩展/设置
- [ ] 页面缩放一致性：缩小窗口到 1000px 以下 → detail-grid / md-grid 自动变单栏；缩小到 700px → panel padding 缩小
- [ ] 新建任务弹窗：有 📎 选择文件 + 输出目录输入框/浏览；选文件后创建任务立即上传（题目/数据 分类正确）；**无横向溢出**（`scrollWidth <= clientWidth`、按钮文字完整、无贴边/无水平滚动条）
- [ ] 任务详情页：📎 上传文件 可补传；📤 导出 复制 论文.pdf/tex + 求解图片/CSV 到 output_dir 并打开文件夹；无 output_dir 时导出报 400 友好提示
- [ ] 删除任务（含刚导出的测试任务）不再 500（task_delete 不再 from workflow import）
- [ ] 前后端路径分隔符一致：后端返回 Windows 反斜杠路径，前端统一 `path.replace(/\\/g,'/')` 再匹配（知识、代码、MD/tex 分组筛选按此）
- [ ] 启动应用：首页/启动屏品牌正确、模板轮播出现 3 模板、无 "Mrite" 可见残留
- [ ] 三套模板用内置 TinyTeX `xelatex -interaction=nonstopmode 论文.tex` ×2 → grep -c 'Error' 0
- [ ] userData rules-library 与权威源一致（备份后覆盖，勿依赖 copyMissingSafe）

## 相关
- `electron-asar-modification` — asar 提取/打包机制与坑（本项目的打包细节主档）
- `references/asar-rebuild-status.md` — 2026-08-16 构建状态与下一步（asar 重建未完成）
- `references/trigon-export-output-fix.md` — 2026-08-20 Trigon MRITE 导出输出目录修复（getCustomOutputPath 从 DB 读取 + AES-GCM 解密）
- `references/gaojiaoshe-template-update.md` — 2026-08-20 高教社杯模板更新（去除目录、页数限制规则）