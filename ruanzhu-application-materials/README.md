# 软著申请材料生成 —— Claude Code / Codex CLI 版

把「软著申请材料生成」技能做成**同时适用于 Claude Code 与 Codex CLI** 的可移植版本。

## 为什么一份文件就能通吃两个工具

Claude Code 与 Codex CLI 读的是**同一套 Agent Skills 规范**：一个目录 + 一个
`SKILL.md`（YAML frontmatter 里的 `name` / `description`），外加可选的 `scripts/`、
`references/`。两边都是「启动时用 description 匹配请求 → 命中后加载正文」，
所以**不需要为哪个平台单独转换格式**，差别只在安装目录：

| 工具 | 个人技能目录 | 项目技能目录 | 直接调用 |
|---|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` | `/ruanzhu-application-materials` |
| Codex CLI | `~/.codex/skills/` | `.codex/skills/`、`.agents/skills/` | `$ruanzhu-application-materials` |

## 安装

```bash
# 装到 ~/.claude/skills 与 ~/.codex/skills（最常用）
python install.py

# 只装某一个
python install.py --target claude
python install.py --target codex

# 装进当前项目，随 git 提交给团队
python install.py --target project

# 先看看会做什么
python install.py --dry-run

# 查看现状 / 卸载
python install.py --list
python install.py --uninstall
```

装完**重启一下工具**（或开新会话）才会加载新技能。

## 依赖

| 依赖 | 必需性 | 说明 |
|---|---|---|
| Python 3.8+ | 必需 | 跑所有脚本 |
| LibreOffice | PDF 环节必需 | docx → pdf、UNO 更新目录；脚本会自动探测安装路径 |
| `python-docx` + `Pillow` | 仅插图时 | `md_to_docx_images.py` 用 |
| `PyMuPDF` | 可选 | 页数统计与目录校验；缺了回退到内置解析 |

```bash
pip install python-docx Pillow PyMuPDF
```

绝大多数转换脚本**只用标准库**，不需要 pandoc。各平台安装 LibreOffice 与
`python3-uno` 的说明见 [`references/platform-notes.md`](references/platform-notes.md)。

## 用法

技能靠 `description` 自动匹配，直接说需求即可：

> 帮我把 `~/projects/my-app` 这个项目做成软著申请材料。

也可以显式调用（Claude `/…`、Codex `$…`）。**关键约定**：技能的正文与脚本必须用
绝对路径调用，因为 agent 的工作目录是你的项目而不是技能目录：

```bash
SKILL_DIR="$HOME/.claude/skills/ruanzhu-application-materials"   # Claude Code
SKILL_DIR="$HOME/.codex/skills/ruanzhu-application-materials"    # Codex CLI

python "$SKILL_DIR/scripts/collect_source_code.py" . -o source-code.txt
python "$SKILL_DIR/scripts/convert_md_to_docx.py" technical-documentation.md
python "$SKILL_DIR/scripts/source_to_pdf.py" source-code.docx
python "$SKILL_DIR/scripts/uno_toc_pdf.py" technical-documentation.docx technical-documentation.pdf
```

## 目录结构

```
ruanzhu-application-materials/
├── SKILL.md                     技能入口（frontmatter + 完整工作流）
├── README.md                    本文件
├── AGENTS.md                    仓库级用法片段（可粘贴进项目 AGENTS.md）
├── install.py                   安装 / 卸载 / 体检
├── references/
│   ├── naming-rules.md          软著命名规范（正反例 + 5 种策略）
│   ├── domain-list.md           领域池 15 个
│   ├── output-specs.md          Explanation.txt 模板、技术文档结构、源程序规范
│   ├── style-list.md            前端 10 种视觉风格
│   └── platform-notes.md        三平台差异与依赖（本版新增）
└── scripts/
    ├── collect_source_code.py          源码收集（排除配置/依赖/构建目录）
    ├── remove_empty_lines.py           空行压缩
    ├── convert_md_to_docx.py           md → docx（封面+目录域+页眉页码）
    ├── convert_txt_to_docx.py          源程序 txt → docx（等宽紧凑）
    ├── convert_to_docx.py              轻量 md/txt → docx
    ├── convert_docx_to_pdf.py          docx → pdf + 60 页裁剪
    ├── update_toc_and_convert_pdf.py   docx → pdf + 更新目录（Word COM 优先）
    ├── source_to_pdf.py                源程序专用：pdf + 60 页规则
    ├── uno_toc_pdf.py                  UNO 精确更新目录（目录页码最准）
    └── md_to_docx_images.py            md → docx 且**支持真实插图**
```

## 相对 WorkBuddy 原版的改动

| 项 | 原版 | 本版 |
|---|---|---|
| frontmatter | 含 WorkBuddy 专有字段 `agent_created` | 只保留 `name` / `description` / `allowed-tools` |
| `description` | 面向 WorkBuddy 的匹配 | 重写并强化触发词（Claude/Codex 全靠它做发现） |
| 脚本路径 | 相对路径 `scripts/xxx.py`（依赖技能目录=工作目录） | 正文明确 `$SKILL_DIR` 绝对路径约定 |
| LibreOffice 定位 | `where soffice` 子进程 + 仅 Windows 路径 | `shutil.which` + 三平台路径（`convert_docx_to_pdf.py`、`update_toc_and_convert_pdf.py`） |
| `uno_toc_pdf.py` | **纯 Windows**：硬编码路径 + `taskkill` + 固定端口 2002 | 跨平台自举（无 uno 自动换 LO python）、`pkill`/`taskkill` 分流、随机空闲端口、独立 `UserInstallation` profile |
| 杀进程 | 每次运行无条件 `taskkill /F`（**会丢未保存的 Office 文档**） | 默认不杀；确需清理时用 `--force-kill`（按进程名杀**全部** soffice，用前先确认无人正在编辑） |
| 字体 | SimSun / SimHei 写死 | 新增 `--font-preset windows|macos|linux` 与 `--font-body/--font-head/--font-code`，默认仍是 SimSun/SimHei |
| 安装 | 手动放置 | `install.py` 一键装到两侧 + 体检 + 卸载 |

## 已知限制

- **未在 macOS / Linux 上实测**：Windows 路径已实测通过（含 UNO 自举、目录页码更新）。
  macOS / Linux 的 LibreOffice 路径与 `pkill` 分支按官方文档与通行部署位置编写，
  首次使用请先跑一次 `python install.py --list` 和一个最小转换验证。
- **中文字体**：macOS / Linux 上默认会由 LibreOffice 自动替换 SimSun/SimHei。
  最终提交给版权中心的版本建议在 Windows 上用默认字体再生成一次，避免评审环境显示异常。
- **`uno_toc_pdf.py` 依赖 LibreOffice 自带的 uno 模块**，Linux 需另装 `python3-uno`。

## 许可与来源

本技能由 WorkBuddy 版 `ruanzhu-application-materials` 移植而来，
原始脚本与规范内容保持原样，仅做跨平台与跨工具适配。
