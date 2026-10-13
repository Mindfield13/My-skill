# M7.5 产出质量提升闭环 — 实现细节（2026-08-17）

## 2026-08-18 关键更新

### skill 加载改为完整原稿（用户铁律：不截断）

用户原话「不要提取精华，我要全部原汁原味」。已废弃 `_wire/` 摘要注入（只加载 ~1KB），改为每步骤直接加载对应完整 SKILL.md：
- `_step_read_problem` → `../math-skills/comp-prob-analysis/SKILL.md`（73KB）
- `_step_solve_plan` → `../math-skills/comp-prob-analysis/SKILL.md`
- `_code_prompt` → `../math-skills/comp-modeling/SKILL.md`（41KB）+ `comp-code/SKILL.md`（60KB）
- `_step_paper` → `../math-skills/comp-paper-zh/SKILL.md`（112KB）+ 论文章节规范.md
- `_step_compile` → `../math-skills/comp-compile-zh/SKILL.md`（44KB）
- `evaluate._build_system_prompt` → `../math-skills/comp-review/SKILL.md`（6KB）
- `_wire/` 目录已删除

context 估算：求解 ~71K tokens / 论文 ~73K tokens，需 ≥128K ctx 模型。**context 不足直接报错，不静默回退到摘要。**

### 前端修复：openModal 双参数 bug + 关不掉

`openModal` 原签名 `function openModal(html)` 只接一个参数，但任务体检弹窗传两个 `('🩺 任务体检报告', '...正文...')` → 正文被丢、只显示标题字符串，且弹窗无关闭机制。

修复（`src/renderer/js/components.js`）：
- 签名 `openModal(title, html)`；单参数时 `html=title; title=''` 向后兼容
- 标题右侧加 × 关闭按钮（`addEventListener` 绑定 `closeModal`，**不用 `onclick`**——IIFE 作用域内 `onclick="UI.closeModal()"` 会因作用域问题失败）
- 点击遮罩关闭（`e.target === mask` 才关，modal 内容区点击不关）
- ESC 键全局关闭（一次性绑定，`_bound` 防重复）
- 15/15 ad-hoc 验证通过（vm 模拟 DOM mock 验证所有行为）

### 前端修复：Electron 自启后端端口混乱

每次 Electron 启动自启一个新后端（随机端口 18099+），与手动启动冲突导致 10048。修复（`src/main/index.js` `startBackend()`）：启动时先 `fetch /api/health` 检查 18100/18099，已有健康后端就复用，不自启。8/8 验证通过。Electron 输出 `[backend] 复用现有后端 @ 18100`。

### 论文模板修复：国模要求无 TOC

删除 `templates/高教社杯/论文.tex` 和 `rules-library/paper/高教社杯/论文章节规范.md` 中的 `\tableofcontents` 块（华数杯保留）。

---

用户选 1~6 全做（论文分步/EDA/规则注入/交火/评估闭环/多方案/小样本约束）。
交火已在 M7.3 实现（配置 `crossfire: {enabled, reviewer, rounds, threshold}`），本阶段无需重做。

## 1. 论文标题提炼（fix "论文题目特别差劲"）

根因：`_step_paper` 第 6 步 `title = meta.get("name")` → 任务名（"C"、"导出测试"）直接写进 `论文.tex`。

修复（workflow.py `_step_paper` 4.5 步）：
```python
title_bak = self.task_dir / "求解" / "论文题目.md"
if title_bak.exists():  # 人工/上次提炼的结果优先
    paper_title = 读第一行
else:
    reply = self._llm().chat(
        "你是数学建模竞赛选手，负责给竞赛论文起一个专业标题。要求：15~28字；体现【方法】+【研究对象】；格式参考「基于XX方法的XX建模与实证分析」；只输出标题本身。",
        [{"role":"user","content": f"《题目分析》如下，请提炼论文标题：\n\n{analysis}"}],
        temperature=0.5, max_tokens=512)  # ★max_tokens≥512，推理模型思维链吃 token
    paper_title = reply.strip().strip('"').strip("「」").splitlines()[0][:60]
    title_bak.write_text(paper_title)  # 保存供人工修改
# 第 6 步：title = paper_title or meta.get("name", "数学建模竞赛论文")
```
产出物凡是能由内容推导的（标题/摘要），绝不用任务元数据硬塞。实测 6/6 真实标题：
「基于多目标优化的NIPT检测时点选择与胎儿异常判定模型」等。

## 2. LLM chat 无文本自动重试（llm.py）

deepseek-v4-flash 偶发响应只有 thinking 块没有 text（约 1/3 概率）→ `_parse_reply` 抛
`LLMError("响应无文本内容")`。修复在 `chat()`：

```python
body = self._build_body(system, messages, temperature, max_tokens)
last_err = None
empty_tries = 0
for attempt in range(8):          # ★原 range(4) 不够（429×3 + 无文本×3 + 正常1）
    ... 429 重试（不变）...
    try:
        return self._parse_reply(data)
    except LLMError as e:
        if "无文本内容" in str(e) and empty_tries < 3:
            empty_tries += 1
            time.sleep(1.5 * empty_tries)
            last_err = f"响应无文本，重试（第 {empty_tries}/3 次）"
            continue
        raise
raise LLMError(f"连续失败：{last_err or '未知错误'}")
```

### ★Python 局部 import 陷阱（本阶段真抓到的 bug）

原 429 分支里有 `import time`（局部）→ Python 把整个函数作用域的 `time` 当局部变量 →
正常路径（没走到 429）的 `time.sleep(1.5*empty_tries)` 抛
`UnboundLocalError: cannot access local variable 'time'`。
修复：删函数内 `import time`（模块顶部已有）。行为验证法：连续 3 次真实调用标题提炼，
第 1 次暴露此 bug，修复后 5/5 绿。

## 3. CDP 截 Electron 窗口 hidden 陷阱（截图挂起）

症状：cdp 截图脚本超时，`Page.captureScreenshot` 发了无响应。
诊断：
```
evaluate document.visibilityState → "hidden"，document.hasFocus() → false
```
说明 Electron 主窗口被最小化/隐藏 → Chromium 对 hidden 页面不执行 fromSurface 截图（挂起）。
`Page.bringToFront` 实测**无法**恢复已最小化的 Electron 主窗口（visibilityState 仍 hidden）。

解法：taskkill electron → 重启（新窗口 show → visible）→ 立即截图。
工具脚本（本会话沉淀，位于项目 tools/）：
- `cdp-one.js <view> <out.png>`：响应驱动（pending Map await 每步响应，不用固定 sleep 拼接）；
  顺序 bringToFront → gotoView → 等 1.5s → captureScreenshot。
  **必须用 `ws.addEventListener('open'/'message')`，Node 原生 WebSocket 不认 `ws.onopen` 属性**（属性赋值版本静默不执行 → 超时）。
- `cdp-all-pages.js`：8 页批量截图到 Temp/mu_pages/。
- `smoke_test.py`：后端 API 全量冒烟（20 端点，含 health/config/tasks/file/xlsx/pdf/rules/templates/单步校验）。
  中文 URL 必须 `quote(path, safe=":/?=&%")`（urllib 不自动编码；curl 拼中文也 400）。

## 4. 产出质量提升四件套（workflow.py）

### EDA 前置（src/backend/eda.py，新模块）
```python
generate_eda(task_id)  # pandas 读 数据/*.xlsx|csv 前 5000 行 → 求解/数据概况.md
get_eda_content(task_id, max_chars=4000)  # prompt 注入
```
输出每列：dtype / 缺失数 / 唯一值 / 样例 / min-mean-max（数值列）+ 文件级工作表清单。
接入点：`_step_read_problem`（读题就生成，题目分析基于真实字段）、`_step_solve` 开头、
`_code_prompt` user 段注入（"《数据概况（EDA 自动生成，列名/类型/缺失/统计以这里为准，不要臆测）》"）。

### 论文分步生成（_step_paper 重构）
- 旧：一个 user 拼全部章节 + max_tokens=12000 + 【=== 文件名 ===】分界解析 → 易占位符/空泛。
- 新：① outline_system 生成《大纲.md》（概述+各章要点+图表文件名+数值结果）② 对 chapters 逐章
  `_llm().chat(system_逐章, [user: base_context + 大纲 + 本节任务], max_tokens=6000)` ③ 摘要 0.摘要.tex
  排最后（chapter_order = 非摘要章 + 摘要章），提示"900字内，禁止引用未出现的图/表"。
- 清理残留代码块：`cleaned.startswith("```")` → 剥首行和尾部 ```。
- 交火整篇改为"只评不改"：拼接各章 → reviewer 逐轮打分（rounds 默认 2）→ 达标记录"审核通过"；
  意见只写 `论文/交火记录.md`，不覆盖分章文件（避免 crossfire_text 整篇改写破坏分章）。
- 失败容错：单章 `except LLMError` → log 跳过继续。

### 多方案采样（_step_solve 循环内）
```
for variant in range(2):
    vdir = prob_dir / f"方案{variant+1}"          # ★目录隔离防相互覆盖
    ... _code_prompt → chat(temperature=0.4+0.5*v) → _run_script(cwd=vdir) ...
    score = (1000 if ok else 0) + len(imgs)*10 + len(results)
if best_score >= 1001:  # 至少 1 方案成功且有产出
    copy 胜者 图片/* 结果/* 到标准位置 + 代码 → 问题X_求解.py → 清理 方案* 目录 → continue
else: 清理方案目录 → 进原 3 轮修复循环
```
注意：采样 run 用的也是 `_code_prompt`（含 EDA/规则/硬约束），LLM 调用 ×2 + 运行 ×2，代价翻倍。

### 小样本硬约束（_code_prompt user 段追加）
```
【硬约束】
- 列名一律以《数据概况》为准；读取后先 df.columns = df.columns.str.strip() 清理空格
- 样本量 <30 时禁止做时间外推/复杂机器学习（用描述统计/简单回归/合理假设）
- 时序外推只在有明显周期且样本 >=30 时允许，且必须说明依据
```

## 5. 评估闭环（review.js 轻量版）

`suggestSteps(r)` 关键词匹配 weaknesses+suggestions：
- 占位符|未生成|缺失|正文|章节|摘要|无法评估 → paper
- 求解|建模|模型|数据|列名|结果|外推|代码 → solve
- 编译|LaTeX|tex|PDF|报错 → compile
- 题目|题意|读题 → read_problem；计划|规划 → solve_plan
渲染 "🔁 根据评估建议重跑：" 按钮组（`.ai-rerun` data-step），wrap 事件委托绑定点击 → `API.runStep`。
DOM 实测 M2 评估（48 分）自动推荐 [论文生成, 逐题求解, 编译PDF]。
注意：`loadAiEval` 里把评估触发抽成 `async function runEvaluate()` 复用（原 addEventListener 内联闭包改
函数引用后，收尾 `});` 要改 `}`，勿删外层函数闭合括号——本会话踩过 2 次 SyntaxError）。

## 验证记录

- eda.py 真实任务：`共 1 个数据文件，2 个工作表`，3983 chars 概况。
- 标题提炼 6/6 成功（修复 local import 后 5/5 绿）。
- review.js DOM：`rerunBtns: 3, labels: ["▶ 论文生成","▶ 逐题求解","▶ 编译PDF"]`。
- 语法：py_compile 全绿 + node --check 全绿；行为验证 12/12（eda 生成、code_prompt 注入、
  分步/采样代码在位、suggestSteps 绑定）。