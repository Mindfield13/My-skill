# 三平台差异与依赖清单

本技能在 Windows / macOS / Linux 上都能用，但有若干平台差异。脚本已尽量内置处理，
本文件说明"哪些是自动的、哪些需要手动装"。

## 一、依赖

| 依赖 | 必需性 | 用途 | 缺失后果 |
|---|---|---|---|
| Python 3.8+ | **必需** | 跑所有脚本 | 无法使用 |
| LibreOffice | **必需**（PDF 环节） | docx → pdf、UNO 更新目录 | 只能交付 docx，无法出 pdf |
| `python-docx` | 只在插图时需要 | `md_to_docx_images.py` | 该脚本报 ImportError |
| `Pillow` | 只在插图时需要 | 按像素算图片宽度 | 图片按最大宽度嵌入，可能超页 |
| `PyMuPDF` | 可选 | 页数统计、目录校验 | 回退到内置 OOXML 正则解析，结果通常一致 |

安装：

```bash
pip install python-docx Pillow PyMuPDF
```

其余转换脚本（`convert_md_to_docx.py`、`convert_txt_to_docx.py`、`convert_to_docx.py`、
`collect_source_code.py`、`remove_empty_lines.py`）**只用标准库**，不需要 pandoc，
也不需要 python-docx。

## 二、LibreOffice 定位

三个脚本（`convert_docx_to_pdf.py`、`update_toc_and_convert_pdf.py`、`uno_toc_pdf.py`）
和 `source_to_pdf.py` 都按同一顺序探测 soffice：

1. 环境变量 `SOFFICE` 或 `LIBREOFFICE`
2. 各平台常见安装路径
3. `shutil.which("soffice")` / `shutil.which("libreoffice")`

各平台的候选路径：

| 平台 | 常见路径 |
|---|---|
| Windows | `%ProgramFiles%\LibreOffice\program\soffice.exe`、`%ProgramFiles(x86)%\...` |
| macOS | `/Applications/LibreOffice.app/Contents/MacOS/soffice`、`~/Applications/...` |
| Linux | `/usr/bin/soffice`、`/usr/local/bin/soffice`、`/snap/bin/libreoffice`、`/usr/lib/libreoffice/program/soffice`、`/opt/libreoffice/program/soffice`、flatpak 导出路径 |

装到非标准位置时直接给环境变量：

```bash
export SOFFICE=/path/to/soffice        # bash / zsh
setx SOFFICE "D:\Apps\LibreOffice\program\soffice.exe"    # Windows CMD（新开窗口生效）
```

## 三、UNO 更新目录（`uno_toc_pdf.py`）

UNO 依赖 LibreOffice 自带的 `uno` 模块。脚本能自举：**直接用系统 python 起手即可**，
它会检测到当前解释器没有 `uno`，自动换用探测到的 LibreOffice python 重新执行自己。

各平台自带 python 的位置：

| 平台 | LibreOffice 自带 python |
|---|---|
| Windows | `<LO>/program/python.exe` |
| macOS | `LibreOffice.app/Contents/Resources/python` |
| Linux | 通常**没有**随包 python，需系统装 `python3-uno` |

Linux 上要先装 uno 绑定：

```bash
# Debian / Ubuntu
sudo apt install python3-uno
# Fedora / RHEL
sudo dnf install libreoffice-pyuno
# Arch
sudo pacman -S libreoffice-fresh  # 已含 python-uno
```

**macOS 注意**：LibreOffice 从 7.x 起对 Apple Silicon 的 python 打包方式有变动，
若自举失败，可显式指定：

```bash
SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice \
  /Applications/LibreOffice.app/Contents/Resources/python uno_toc_pdf.py x.docx x.pdf
```

### 关于 `--force-kill`

旧版脚本**每次运行都无条件执行 `taskkill /F /IM soffice.bin /T`**，这会丢掉用户
**未保存的 Office 文档**。现改为默认不杀，仅在传 `--force-kill` 时清理残留进程；
且脚本只终止自己启动的那个 soffice 实例。跨平台实现：

| 平台 | 清理命令 |
|---|---|
| Windows | `taskkill /F /IM soffice.bin /T`、`taskkill /F /IM soffice.exe /T` |
| macOS / Linux | `pkill -f soffice`，无 pkill 时退回 `killall soffice` |

### 独立 profile 与随机端口

脚本为每次运行创建独立的 `-env:UserInstallation` 临时目录（跑完即删），
因此**不会挂到用户正在使用的 LibreOffice 上**，多个转换并发也不会互相争抢。
桥接端口用 `free_port()` 向系统要空闲端口，不再固定 2002（避免端口占用和撞车）。

## 四、中文字体

默认字体是 **正文宋体（SimSun）+ 标题黑体（SimHei）+ 代码 Courier New** —— 这是软著
提交件的通行约定，也是 Windows Office 自带的字体，**不要随意改**，否则评审环境可能显示异常。

macOS / Linux 上一般没有 SimSun / SimHei，LibreOffice 会自动替换成系统里最接近的中文字体，
**通常不影响交付**（内容才是评审重点）。仅在替换导致排版明显走样时，才用平台等价字体：

```bash
# 整组切换
python md_to_docx_images.py 技术文档.md -o 技术文档.docx -n "软件名" --font-preset macos
python md_to_docx_images.py 技术文档.md -o 技术文档.docx -n "软件名" --font-preset linux

# 逐个指定
python md_to_docx_images.py 技术文档.md -o 技术文档.docx -n "软件名" \
       --font-body "PingFang SC" --font-head "PingFang SC"
```

| 用途 | Windows | macOS | Linux |
|---|---|---|---|
| 正文（宋体） | SimSun | STSong | Noto Serif CJK SC |
| 标题（黑体） | SimHei | STHeiti | Noto Sans CJK SC |
| 代码 | Courier New | Menlo | DejaVu Sans Mono |

> 用非 SimSun/SimHei 生成的 docx，拿到 Windows 上打开可能被替换显示。
> 最终要提交给版权中心的版本，**建议在 Windows 上用默认字体重新生成一次**。

## 五、临时目录与沙箱

部分沙箱环境不允许创建命名管道、或拒写系统临时目录。所有脚本因此遵循两条约定：

1. **不用 `tempfile.mkdtemp`**，改为在**当前工作目录**下 `os.makedirs` 创建临时目录，
   并写入探针文件验证可写性（见 `source_to_pdf.py` 的 `make_workdir`）。
2. **不把子进程输出接到 `subprocess.PIPE`**，改为重定向到文件。

改动这些逻辑前请先确认目标环境允许，否则会在沙箱里静默失败。

## 六、路径与命令差异

| 事项 | Windows | macOS / Linux |
|---|---|---|
| 路径分隔 | 反斜杠，命令行里建议用引号包住带空格的路径 | 正斜杠 |
| LibreOffice python | `<LO>/program/python.exe` | `<LO>/.../python` 或系统 `python3` |
| 结束进程 | `taskkill` | `pkill` / `killall` |
| 环境变量 | `setx VAR value`（新窗口生效） | `export VAR=value` |

**Git Bash / MSYS 用户注意**：把 `/c/Users/...` 这类路径传给原生 Windows python.exe
会被解析成 `E:\c\Users\...`（相对当前盘符）。给 Windows 程序传路径一律用 `C:/...` 盘符形式。
