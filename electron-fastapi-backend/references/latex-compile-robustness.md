# LaTeX 编译健壮性 + 论文分步生成（2026-08 实测：3 页 → 17 页完整论文）

## 经典故障：论文 PDF 只有 3 页（用户报"论文只有这一点"）

**症状**：`论文.tex` 骨架完整、章节文件全在（0.摘要~10.附录）、`论文.log` 里 `Output written on 论文.pdf (3 pages)`——但正文只有标题页+摘要+目录。

**根因链**（三层，缺一不可）：
1. LLM 在章节里写 `\includegraphics{../求解/问题一/图片/问题一_相关矩阵热力图.png}`（原始求解目录相对路径），而编译工作目录只有 `论文/图片/*.png` 副本（复制时加了 `问题X_` 前缀）→ 图片路径必然找不到。
2. `xelatex -interaction=nonstopmode -halt-on-error`：遇到第一个缺失图片即**中止排版**（`-halt-on-error` 是"第一个错误就停"）→ 后面 3~10 章全部没进 → 只有 3 页。
3. 成功判定只查"PDF 存在且 mtime 新"，把这种 3 页残缺当成功 → 静默交付。

by 或途中：缺图还会触发 `dvipdfmx:fatal: Image inclusion failed. Could not find file: ...` + `No output PDF file written`（连 PDF 都没有）。

## 修复三件套（全部已实现）

### 1. 源头：论文生成 prompt 注入《可用图片清单》
`_step_paper` 组装每章 user 时，把 `论文/图片/*.png` 实际文件名列表（clip 40 个）作为《可用图片清单》注入，系统规则加"图片引用铁律：绝对禁止 `../` 或 `求解/` 路径，`\includegraphics` 只能写 `{图片/<文件名>}`，文件名必须来自清单"。LLM 只能引用真实存在的图。

### 2. 兜底：编译前规范化 includegraphics 路径
`_step_compile` 开头扫描所有 `论文/*.tex`，`re.sub` 改写：
- **正则捕获组顺序**（踩过坑）：`r"\\includegraphics((?:\[[^\]]*\])?)\{([^}]+)\}"` → **group(1)=可选宽度参数** `[width=0.8\textwidth]`，**group(2)=花括号路径**。写 `m.group(1)` 当路径会让所有匹配都"未命中"（收集到一堆 `[width=...]`）。
- 匹配规则三档：
  1. 路径已 `图片/` 开头 → 原样保留
  2. 文件名精确命中 `论文/图片/` → 改 `图片/<name>`
  3. 剥离 `问题[一二三四五六七八九十\d]+_` 前缀后核心名相等（`问题一_残差图.png ↔ 问题1_残差图.png`）→ 命中
  4. 共同后缀 ≥ 8 字符兜底（`各BMI组... ↔ 各BMI分组...` 这类细命名差异）
- 输出 `\includegraphics{group(1)}{图片/<命中名>}`，记 `fixed_cnt` 打日志。

### 3. 编译策略：去掉 -halt-on-error + 页数判定
- `cmd = [xelatex, "-interaction=nonstopmode", main_tex]`——一处缺失图片不应断送整篇；nonstopmode 尽力排版全部章节。
- 成功判定：
  ```python
  fresh = pdf_path.exists() and pdf_path.stat().st_mtime >= start - 1
  pages  = 从日志 r"Output written on .* \((\d+) pages" 提取
  fatal  = any("Unable to load" in e or "Fatal error" in e or "No output PDF" in e for e in errors)
  ok     = fresh and pages >= 5 and not fatal
  ```
- **可恢复警告（不算 fatal，PDF 已渲染）**：`! Missing $ inserted`、`! Missing number, treated as zero`、`! Package calc Error: '.' invalid`、`! LaTeX Error: Not in outer par mode`、`! Emergency stop.`（伴随 `Output written ... (N pages)` 时——它是 `\end{document}` 处自动插入缺失 `}` 后到 EOF 的提示，PDF 已完整写出）。
- **真 fatal**：`Unable to load picture`（缺图且 dvipdfmx 阶段仍找不到）、`Fatal error`、`No output PDF file written`（dvipdfmx 生成失败，连 PDF 都没有）。
- errors 提取：`!` 开头 / Fatal / Unable / Emergency 的行，截 220 字符；返回 `errors[:10]` 但 **fatal 判定用全量 errors**（截断会漏致命项，曾把 `Emergency stop` 藏在第 11 条导致只显示非致命的前 10 条——排查时先在函数内 print 分量）。

## 论文分步生成（替代一次性 12000-token 一锅炖）

`_step_paper` 三阶段：
1. **大纲**：LLM 输出《论文大纲》（概述+各章要点+图表文件名+数值结果），存 `论文/大纲.md`，max_tokens=3000。
2. **逐章**：对每章独立调用（`abstract_file = "0.摘要.tex"` 放到**最后**生成——摘要要能收束全文），`max_tokens=6000`，user = 基础上下文 + 大纲 + 可用图片清单 + "只输出该章节 LaTeX 内容"。清理可能残留的 ``` 包裹。
3. **交火存档**：若 crossfire 启用，拼接整篇 → 审核者给意见+打分 → 只写 `论文/交火记录.md` 存档，不覆盖分章（原始 `_crossfire_text` 会整体重写，逐章模式下不能直接复用）。
- 验证：章节 .tex 非 0 字节；编译后 `Output written on 论文.pdf (N pages)` 且 N≥5。

## 验证清单
- 编译日志（`编译日志.txt`）末尾应含 `Output written on 论文.pdf (≥5 pages).` 且无 `Unable to load` / `No output PDF file written`。
- 单图缺失会怎样：nonstopmode 下该图留白/跳过，其余章节照常渲染；只有**全部章节缺关键图**时 dvipdfmx 才可能 fatal。