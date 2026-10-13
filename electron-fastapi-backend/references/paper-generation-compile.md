# AI 论文生成 + LaTeX 编译（M4 模式）

## 论文生成策略

### 模板复制
- 从 `templates/模板名/` 复制 `.tex`/`.cls`/`fonts/` 到 `论文/` 目录
- 保留 `论文.tex` 骨架文件不动（其 `\input{}` 结构由 LLM 内容填充）
- 无模板时写最小骨架：`\documentclass{format}` + `\usepackage{ctex}` + `\input{0.摘要}`

### 图片复制
- 扫描 `求解/问题X/图片/*.png`，复制到 `论文/图片/`，重命名加 `问题X_` 前缀
- 避免 LaTeX 编译时中文路径/跨目录引用问题

### LLM 生成
- 上下文：题目分析 + 求解计划 + 求解结果摘要（图名 + CSV 前 5 行）+ 章节规范
- 输出格式要求：`【=== 文件名.tex ===】` 标记分隔，每章完整 LaTeX 内容
- 图引用：`\includegraphics[width=0.8\textwidth]{图片/问题X_xxx.png}`
- 表格：`\textwidth` 宽，表头中文，格子文字不换行
- 禁止：`\newpage`、分点符号、模板占位符、`\textbf{正文}`

### 解析（按行扫描，最鲁棒）
```python
line_pattern = re.compile(r"(?:【===|===)\s*([^=\n]+?\.tex)\s*(?:===】|===)?")
current_file = None
current_lines = []
for line in reply.split("\n"):
    m = line_pattern.match(line.strip())
    if m:
        if current_file and current_lines and current_file != "论文.tex":
            (paper_dir / current_file).write_text(
                "\n".join(current_lines).strip(), encoding="utf-8")
        current_file = m.group(1).strip()
        current_lines = []
    elif current_file:
        current_lines.append(line)
# flush last
if current_file and current_lines and current_file != "论文.tex":
    (paper_dir / current_file).write_text(...)
```
- 写正则捕获组容易漏掉开头几章（因为 LLM 回复开头可能有说明文字），按行扫描不受影响
- 保存 AI 回复原文到 `论文/_ai_reply.txt` 调试用
- 回退：0 章节命中 → 全文写入 `0.摘要.tex` 保底

## 编译

```python
def _step_compile(self):
    import latex as latex_mod
    result = latex_mod.compile_tex(str(paper_dir))
    if result["ok"]:
        meta["has_pdf"] = True
    else:
        raise WorkflowError(f"编译失败：{errs[:200]}")
```

- `import latex` 在函数内执行（避免顶层循环引用）
- 失败时抛出 WorkflowError，工作流状态变 error 不阻塞其他步骤

## 已知 TeX 环境问题

- MiKTeX 安装损坏（xelatex.exe DLL 版本不匹配，`STATUS_DLL_NOT_FOUND 0xC0000135`）时，`miktex packages update` 显示"no updates available"也无法修复。需要重装 MiKTeX 或从官网下载最新安装包覆盖。
- TinyTeX（MRITE_2.50 内置）的 `xelatex.fmt` 可能因路径硬编码无法加载，`fmtutil` 重建也因 Perl 依赖失败。不推荐作为备选编译引擎。
- 编译前用 `xelatex --version >nul 2>&1` 或直接调用 `compile_tex` 捕获异常，给用户清晰提示。

## IPC 打开 PDF

```js
// 主进程
ipcMain.handle('open-path', async (event, p) => shell.openPath(p));
// preload
openPath: (p) => ipcRenderer.invoke('open-path'),
// 前端
if (window.mUltra?.openPath) await window.mUltra.openPath(filePath);
```

## 验证

- 论文生成后检查：`论文/*.tex` 非 0 字节，`论文/图片/*.png` 存在
- 编译后：`论文/论文.pdf` 存在且非空
- 编译失败时日志（`论文/编译日志.txt`）含具体错误