# M7：AI 评估 + 多任务并行 + 评审页增强 + 扩展页（2026-08-17）

## 1. AI 评估（evaluate.py 新模块，实测跑通）

**接口**（main.py，沿用 ai-edit 的异步作业模式）：
- `POST /api/tasks/{id}/ai-evaluate` — 校验任务存在 → `_eval_jobs[task_id]={status,detail,result,error}` + `_eval_lock` → 后台线程 → 立即返回 `{started:true}`；已有 running 返回 409
- `GET /api/tasks/{id}/ai-evaluate/status` — 轮询 status: reading→working→done|error
- `GET /api/tasks/{id}/ai-evaluate/report` — 读已完成结果

**评分维度固定 5 个**（DIMENSIONS: 逻辑/模型/结果/图表/规范，key+name+desc），LLM prompt 要求**严格 JSON 输出**：
```json
{"scores":[{"key":"逻辑","score":0-100,"comment":"具体意见"}×5],
 "overall":0-100, "summary":"总评", "weaknesses":["≤4条"], "suggestions":["≤4条"]}
```
- prompt 明确"输出必须是合法 JSON 对象（不要代码块、不要多余文字）"
- `_parse_result` 容错：regex 剥 ```json，兜底取第一个 `{...}`，score clamp 0-100，缺失维度补 0+"（未评分）"

**材料收集**：
- 论文 tex 8000 字符 + 题目分析 2500 + 求解计划 2500 + 求解产物摘要（每问题图片/结果数量 + 前 2 个结果文件 CSV 预览 600 字符）
- 评估要求 `_collect_requirement_text`：task.json `eval_requirements` 文本 + `评估要求/` 目录文件（md/txt 直读，其余走 `extract.extract_file`）

**输出**：`评审/评估报告.md`（markdown 维度表+总评+问题+建议）+ **`评审/eval_result.json`（完整结构）** + task.json `ai_eval`（仅摘要 overall+时间）

**★关键坑（截图只显示总分、无维度卡片）**：`get_eval_report` 第一版只读 task.json 的 `ai_eval` 摘要（overall+evaluated_at），前端 `hive()` 里 `r.scores||[]` 为空 → 只有总分条没有 5 张维度卡。修复：完整 result 落 `评审/eval_result.json`，`get_eval_report` 优先读它，回退 task.json。评估类接口必须存完整结构，摘要只能用于 task.json 展示。

**★坑**：`extract.extract_file()` 返回 **dict** `{path,name,type,text,rows?}` 不是 str——取文本用 `ed.get("text","")`。

**前端**（review.js `loadAiEval`）：已有报告 → `<details open>` 摘要 + "↻ 重新评估"按钮；无报告 → 大按钮。点击 → `aiEvaluate()` → 1s 轮询 status → done 后重载。展示 `hive()`：总分大字（≥80 绿 / ≥60 accent / 否则红）+ 进度条 + 5 张维度小卡（分数条+comment）+ summary 框 + 主要问题（红）+ 改进建议（accent）。卡片布局 `.review-eval`（文件检查）+ `.review-ai-eval`（AI 分）+ `.review-req`（要求）。

## 2. 多任务并行（架构已验证）

**结论：后端本就支持并行**——`_engines` dict 按 task_id 各建独立 WorkflowEngine，每引擎独立线程 + 独立任务目录 + 独立 stop_flag；前端任意任务都能点"开始求解"，无全局单任务假设。真正缺的只有**并发写坏 task.json**：
- WorkflowEngine.__init__ 加 `self._meta_lock = threading.RLock()`
- `_load_meta`/`_save_meta` 全部包 `with self._meta_lock`
- `_save_meta` 原子写：`tmp = file.with_suffix(".json.tmp")` 写入 → `tmp.replace(file)`（杜绝半写状态）
- 验证脚本：双引擎 × 每引擎 20 次并发写 → 0 错误（用临时任务目录，跑完 shutil.rmtree 清理）

## 3. 评审页增强

- **删除失效按钮**：用户点名"任务详情按钮删掉吧也不管用"——`onclick="window.__taskDetailId=...;MU.gotoView('task')"` 的跳转按钮实际无效，直接移除。铁律：**不放失效按钮**。
- **评估要求支持上传 PDF/DOCX 等文件**：
  - 后端：`POST /api/tasks/{id}/requirements/upload` 收 **base64 JSON**（`{files:[{name,content(b64)}]}`），存 `任务目录/评估要求/`（重名加 `_1` 后缀）；`GET .../requirements/files`（name/size/mime）；`DELETE .../requirements/files?name=`
  - 前端：`<input type=file multiple accept=".pdf,.doc,.docx,...">` → `f.arrayBuffer()` → `btoa(String.fromCharCode(...new Uint8Array(buf)))` → 上传 → 重载；文件 chip 带图标（pdf📕 docx📘 png🖼 默认📄）+ 大小 + ✕ 删除
  - 注意：渲染进程无法拿 File.path（Electron 43 用 webUtils），一律 arrayBuffer→base64 传输，**不要 multipart**

## 4. 扩展页规则库浏览器（M6 收尾，本次验证）

- 后端：`GET /api/rules` 递归建树（目录在前）；`GET /api/rules/read?rel=` 读文件（**路径越权防护**：`(rdir/rel).resolve()` + `str(startswith rdir)` 校验）
- 前端 ext.js：左侧 `.ext-grid` 280px 树（`.ext-dir` 展开/折叠 + `.ext-file` 叶子，默认展开第一级）+ 右侧 `.ext-prev-body` markdown 渲染；手写轻量 md 渲染函数（esc→代码块→行内代码→标题→粗体→链接→列表→br）
- CSS：`.ext-grid`/`.ext-tree`/`.ext-file.ext-active` 等，沿用 vf-grid 模式

## 5. 多模型交火：制作者-审核者循环（M7.3，已实现并实测 2026-08-17）

用户拍板的交火 = **制作者-审核者循环**（对抗式迭代），用户原话："一个制作一个审核不断的提出问题审核质量"。非"多模型独立求解再仲裁"路线（更省：单产出线，审核每轮只耗 1 次 LLM 调用）。

**配置**（config.py `DEFAULTS["crossfire"]`）：
```json
{"enabled": false, "reviewer": "", "rounds": 2, "threshold": 80}
```
- `reviewer` = 审核者 profile 名称，空 = 自动
- `get_reviewer_profile()`：优先配置 reviewer 名称；否则选**非主模型的第 1 个有 base_url+model 的 profile**；绝不能返回主模型自己

**core 方法**（workflow.py）：
- `_crossfire_cfg()` / `_reviewer_client()`（审核者≠主模型，否则返回 None）
- `_review_content(purpose, content, context_text)` → 审核者 LLM 输出严格 JSON `{"score":0-100,"pass":bool,"issues":["≤4"],"suggestions":["≤4"]}`；解析容错同 AI 评估（剥代码块/兜底 JSON）；失败解析按未通过处理；**分数<85 时 pass 强制 false**
- `_crossfire_text(purpose, system, user, content, context_text, max_chars)` → 纯文本交火循环（用于论文生成）：每轮审核→未过→制作者走对话链修改（user+assistant+revise_msg 三消息）→再审核；返回 (最终内容, 日志行)
- `_crossfire_solve(prob, prob_dir, script, analysis, plan, data_files)` → 求解代码交火增强：审核代码→修改→**写临时文件 `问题X_交火N.py` 重跑验证**（运行失败就回退、不破坏已成功的产物）→成功则覆盖正式脚本继续下一轮

**接入点**：
- `_step_paper`：LLM 首次生成后，`if cfg.enabled and self._reviewer_client()` → 对整篇论文 `_crossfire_text`（max_chars=14000）→ 日志写 `论文/交火记录.md`
- `_step_solve`：代码运行成功产出后，`if not stop_flag and enabled and reviewer` → `_crossfire_solve`（每轮修改都重跑验证，保证交火不引入坏代码）

**设置页 UI**（settings.js）：`多模型交火 🔥` 卡片 = 启用开关（自绘 toggle，44×24 滑块 `#cf-enable`）+ 审核者下拉 `#cf-reviewer`（含"（自动选择非主模型）"选项 + 未启用 profile 前置 + 主模型标注）+ 最大轮数 `#cf-rounds`（1-3）+ 通过阈值 `#cf-threshold`（0-100，默认 80）；保存时并入 config 提交。

**实测**：主模型 cc-switch 默认(sensenova) + 审核者 DeepSeek(deepseek-v4-flash)，给一段"只读 Excel 打印"的敷衍代码打 **10 分**，4 条具体问题（未响应任务/缺预处理/无模型/输出不规范）+ 4 条建议，专业度在线。

**数据一致性要点**（对任何多模型改造）：模型中间产物放独立子目录（`问题X/模型名/`），只把最终结果复制到标准位置；写文件原子化（tmp→replace）；task.json 加锁（已备）。

## 6. LLM 客户端 URL 规范化（自定义模型链接修复 2026-08-17）

**症状**：用户在设置页自定义模型贴完整端点连不上——旧 `_normalize_base` 只做"非 `/v1` 结尾就补 `/v1`"：
```python
# 旧：https://api.deepseek.com/chat/completions → https://api.deepseek.com/chat/completions/v1 ❌ 404
if not b.endswith("/v1"): b = b + "/v1"
```
`_endpoint()` 再拼 `/chat/completions` → 双重复合 → 404。

**修复后的 `_normalize_base` 三段式**：
1. **裁剪完整方法端点**：命中 `/v1/messages`、`/v1/chat/completions`、`/v1/completions`、`/chat/completions` 时，去掉方法段回退基础 URL
2. **保留版本路径**：`re.search(r"/v\d+$", b_lower)` → `/v1`、`/v2`、`/api/v1` 原样保留不补
3. **裸域名才补** `/v1`（如 `https://api.deepseek.com` → `.../v1`）

验证覆盖（行为断言）：裸域名补 /v1、已带 /v1 保留、尾斜杠裁剪、完整 openai 端点裁剪（`.../chat/completions` → base 后 `_endpoint` 恰好还原）、anthropic messages 裁剪、cc-switch `127.0.0.1:15721` 代理正常补 /v1。真实连接测试：anthropic + openai 两种协议、base 贴完整端点都 200。**教训：任何兼容多厂商的 HTTP 客户端都按"用户可能贴任意格式 URL（裸地址/带版本/完整端点/尾斜杠）"来规范化。**

## 7. 自绘 iOS 开关的 CSS 类复用坑（cf-switch 错位修复 2026-08-17）

**症状**：设置页"启用交火"开关错位/下坠，视觉像掉到下一行。

**根因两层**：
1. 复用了 `.toggle-btn` 类（模型 Profile 圆形单选按钮样式：22px 圆 + 2px 边框 + `display:flex` 居中）再叠加 inline iOS 滑块样式（44×24 轨道 + 内嵌 knob span）→ 轨道宽高被边框/居中干扰，knob 位置错乱。**class 是给别人控件用的，样式冲突靠 inline 覆盖不干净**
2. 轨道 `rgba(255,255,255,.12)` 白半透明在浅色主题白底上**隐形** → 视觉上只剩白圆点，被误判"下坠"

**正解**（`.cf-switch` 独立类 + 伪元素滑块，不依赖内嵌 span）：
```css
.cf-switch {
  width: 44px; height: 24px; border-radius: 12px; position: relative;
  cursor: pointer; background: color-mix(in srgb, var(--text-3) 35%, transparent);
  display: inline-block; border: none; padding: 0;
}
.cf-switch::after {
  content: ''; position: absolute; top: 2px; left: 2px; width: 20px; height: 20px;
  border-radius: 50%; background: var(--panel); box-shadow: 0 1px 3px rgba(0,0,0,.3);
  transition: left .2s;
}
.cf-switch.active { background: color-mix(in srgb, var(--accent) 60%, transparent); }
.cf-switch.active::after { left: 22px; }
```
JS 只 `classList.toggle('active')`（伪元素自动跟随），不要手动改 inline left/背景。**教训：自绘控件一律用独立类+伪元素；颜色走主题 CSS 变量，深/浅两主题都要可见；先用 DOM boundingRect 判断是否真错位再动 CSS（当时 top 只差 4px 实际对齐，是颜色隐形造成的视觉误判）。**

## 8. ★商汤推理模型兼容（"测试卡住"根因 2026-08-17）

**症状**：用户配置商汤官方 API（`新配置` profile：protocol=openai、base=`https://token.sensenova.cn/v1`、model=sensenova-6.8-flash-lite、真实 key 35 字符）→ 设置页点"测试当前"卡住不返回 → 后端报 `响应缺少 choices[0].message.content`。

**根因两层**：
1. **sensenova-6.8-flash-lite 是推理模型**：OpenAI 兼容响应里思维链放在 `choices[0].message.reasoning`，`content` 只在思考完成后才产出。`test_connection` 用 `max_tokens=16` → 全部 token 被思维链吃光（`finish_reason":"length"`）→ `content` 缺失 → 解析抛错。
2. 诊断命令显示：max_tokens=32 时 **55.8s** 才返回且失败；max_tokens=512 时 **3.1s** 回复"正常"。（假 key 401 秒拒、真 key 过认证后进入推理才慢，30-60s 属正常）

**修复（llm.py）**：
- `_parse_reply` openai 分支：`msg.get("content")` 为空/缺失 → 回退 `msg.get("reasoning")`；anthropic 分支同样：`content` 缺失 → `data.get("reasoning")`；全空报 `LLMError("响应缺少内容（content/reasoning 均为空）"+ _debug_snippet(data))`
- `_debug_snippet(data)`：报错时附响应键名 + finish_reason，方便定位是哪家服务的什么格式
- `test_connection` max_tokens **16 → 512**（给推理模型留足思考空间）
- 前端 settings.js 测试按钮：15s 未返回 → toast "模型响应较慢（推理模型可能需 30-60 秒），请耐心等待…"，防误判卡死

**通用教训**：接任何"推理类"模型（DeepSeek-R1、O1、商汤 flash-lite 等）时——①解析必须兼容 reasoning/content 双字段；②测试/小请求 max_tokens 要给足（512+），思维链会吃光小预算；③慢不是 bug，给用户预期提示；④真实强测连接时先抓 `resp.text` 看厂商实际响应结构再改解析（curl 假 key 只能验证连通性，看不到真 key 的响应结构）。