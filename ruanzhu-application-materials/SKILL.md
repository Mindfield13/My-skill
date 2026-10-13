---
name: ruanzhu-application-materials
description: 生成中国版权保护中心《计算机软件著作权登记》全套申请材料（软著）。两条工作流：①从零生成一个可运行项目并同步产出材料；②对已有项目做源码整理与材料补正。产出软件说明书/技术文档、源程序文档、Explanation.txt、软件名称说明及其 docx/pdf 定稿。当用户提到"软著""软件著作权""申请材料""登记材料""说明书""源程序文档""60页""补正""版权中心""CPCC"时使用本技能。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# 软著申请材料生成

面向中国版权保护中心（CPCC）软件著作权登记的成套材料生成。核心是**两件事**：把一个软件"造"出来，或者"读懂"一个已有项目，然后按登记格式产出四份文档。

## 快速开始

**先确定技能目录。** 本 SKILL.md 所在目录记为 `$SKILL_DIR`；agent 当前工作目录通常是用户项目而不是技能目录，所以**所有脚本都必须用绝对路径调用**：

```bash
# Claude Code
SKILL_DIR="$HOME/.claude/skills/ruanzhu-application-materials"
# Codex CLI
SKILL_DIR="$HOME/.codex/skills/ruanzhu-application-materials"

python "$SKILL_DIR/scripts/collect_source_code.py" . -o source-code.txt
```

**两条工作流怎么选**：

| 用户情况 | 走哪条 | 入口 |
|---|---|---|
| 手上没代码，要"造"一个 | 工作流 A（从零生成） | 第二节 |
| 已有项目，要出材料或补正 | 工作流 B（存量补正） | 第三节 |
| 材料已被驳回 | 工作流 B + 逐条对齐驳回意见 | 第三节铁律 |

**交付物（四份文档）**：

| 文件 | 内容 | 页数/篇幅 |
|------|------|-----------|
| `source-code.txt` → `.docx`/`.pdf` | 源程序文档，纯代码，无注释无配置 | 60 页（前 30 + 后 30） |
| `technical-documentation.md` → `.docx`/`.pdf` | 软件说明书/技术文档，分模块操作说明 | 按模块数，通常 20-40 页 |
| `Explanation.txt` | 开发/运行环境、开发目的、主要功能、技术特点 | 固定字段，主要功能约 700 字 |
| `software-name-notes.md` → `.docx` | 软件名称说明：臆造词释义、取名缘由、不侵权保证 | 1-2 页 |

**源程序文档的 60 页规则（硬性）**：转换后 PDF 页数 ≤ 60 → 全保留；> 60 → 只留**前 30 页 + 后 30 页**共 60 页，完整版另存 `-full.pdf`。这条规则由 `source_to_pdf.py` 自动执行，不要手工裁剪。

**环境依赖**：Python 3.8+；PDF 环节需要 LibreOffice（`soffice`）。转换脚本本身**只用标准库**（`zipfile` + `xml.etree` 手搓 OOXML），不需要 pandoc。可选增强：`python-docx` + `Pillow`（插图用）、`PyMuPDF`（页数统计与校验，缺了会回退到内置解析）。

## 一、工作流 A：从零生成

用户手上没有代码，需要"造"一个符合软著要求的项目。

```
1. 定名称   → 读 references/naming-rules.md，生成 5 个候选
2. 定领域   → 读 references/domain-list.md（15 个领域池，勿用固定品牌词）
3. 定技术栈 → 见下表，或用户自定义
4. 定前端   → 是否需要前端界面（决定纯后端还是全栈）
5. 生成功能规格
6. 生成代码（分批，见下）
7. 汇总源程序 source-code.txt
8. 生成技术文档 + Explanation.txt + 软件名称说明
9. 转 docx → 更新目录 → 转 pdf
```

### 名称生成

- **品牌词必须随机即兴创作**：每次生成都重新随机组合，禁止复用任何固定品牌词，不得与已生成名称重复（维护"已生成"排除表）。
- 结构：`品牌词 + 业务功能描述 + 软件类型后缀`
- 后缀必须是 系统 / 平台 / 软件 / 工具 / 程序 / 助手 之一
- 长度 5-30 字；不得含国家字样、地名简称、注册商标、版本号、夸大词（第一/最强/最全）
- 详细规则与正反例见 `references/naming-rules.md`

### 领域池（用这 15 个）

企业管理信息化、移动互联网应用、人工智能与机器学习、大数据与数据分析、云计算与云原生、物联网与嵌入式、工业互联网与智能制造、金融科技、医疗健康信息化、智慧教育、游戏与数字娱乐、网络安全与密码、智慧交通与车联网、基础软件与开发工具、政务与公共服务

要求：个性化、差异化、体现多领域业务功能，越独特越好（通过率高）。

### 技术栈

**纯后端**

| 标识 | 框架 | 特征 |
|------|------|------|
| `flask-sqlite` | Flask + SQLite | 轻量级，零配置，适合快速开发 |
| `django-mysql` | Django + MySQL | 全功能框架，适合复杂业务 |
| `springboot-mysql` | Spring Boot + MySQL | 企业级，分层严格 |
| `express-mongodb` | Express + MongoDB | Node 异步，文档模型 |
| `gin-postgres` | Gin + PostgreSQL | Go 高并发，SQL 严谨 |

**全栈（后端 + 前端）**

| 标识 | 组合 |
|------|------|
| `vue-flask` | Vue 3 + Flask |
| `react-express` | React + Express |
| `vue-springboot` | Vue 3 + Spring Boot |
| `vue-django` | Vue 3 + Django |
| `react-springboot` | React + Spring Boot |

也可由用户自定义技术栈。前端视觉风格从 `references/style-list.md` 的 10 种里选一种，写进 `frontend.md`。

### 代码生成（关键技术约束）

**文件清单按技术栈固定**，例如：

- `flask-sqlite` → `models.py`（连接池、通用查询函数、全部表 CRUD/分页/统计）、`routes_main.py`（前 3 个模块的全部 API）、`routes_*.py`（其余模块）、`app.py`、公共模块（统一响应封装、分页参数解析、日期时间处理、数据校验、日志记录、文件操作）
- `django-mysql` → `models.py`（全部业务表实体）、`serializers.py`（全部模型序列化+校验）、`views.py`（全部接口，含分页/搜索/统计）、路由
- `springboot-mysql` → Entity、Mapper/Repository、Service（事务、分页、统计）、Controller（统一返回、全局异常处理、分页工具、日期工具）
- `express-mongodb` → `routes/` 下全部路由文件 + `app.js`（中间件、路由挂载、错误处理）
- `gin-postgres` → `handlers/` 下全部业务处理器 + `main.go`
- 全栈 → 再加前端：`api.js`/`api.ts`（封装全部后端接口）、登录页、每个业务模块一个页面（列表、分页、搜索、增删改）

**生成时必须遵守**：

1. **只输出代码文件内容**：每个文件用 ` ``` ` 包住完整代码，文件之间以 ` ``` ` 分隔；不要说明文字、不要元信息。
2. **必须包含人为痕迹**：偶尔出现不规范的变量名、少量冗余代码、风格不统一、函数长度参差。这是为了规避"AI 生成"特征。
3. **禁止截断**：输出被截断（如未闭合的三引号）即判定失败，须重新生成完整版本。
4. **必须能跑**：生成后做语法验证，未通过则重新生成该批次。
5. **分批生成**：单次生成量超限时按模块拆批续写。

### 源程序汇总

```bash
python "$SKILL_DIR/scripts/collect_source_code.py" <项目根目录> -o source-code.txt
```

自动排除：依赖/构建/版本控制目录（node_modules、venv、dist、build、target、.git…）、配置文件与锁文件（package.json、requirements.txt、pom.xml、.env、*.lock…）、二进制与媒体文件、`*.min.js`/`*.min.css`。只保留真正的源代码扩展名。

输出**不带文件分隔标记**（软著惯例）；需要时加 `--with-separators`。脚本会报告总行数，**低于 3000 行会告警**（材料单薄）。

若需去空行压缩篇幅：

```bash
python "$SKILL_DIR/scripts/remove_empty_lines.py" source-code.txt          # 连续空行合并为一行
python "$SKILL_DIR/scripts/remove_empty_lines.py" source-code.txt --all    # 删除全部空行
```

## 二、工作流 B：存量项目补正

用户已有项目，需要产出软著材料（或对已驳回的材料做补正）。

```
1. 绑定项目目录
2. 扫描项目树，识别技术栈与功能模块
3. 基于真实源码推荐 5 个软著名称候选
4. 确认名称 / 技术栈 / 是否含前端
5. 生成功能规格 → 说明书 → 技术文档
6. 收集真实源码 → source-code.txt → 转 pdf
```

**补正模式的铁律（写进 prompt 的硬约束）**：

- 接口、数据库表结构、交互流程**必须来自项目真实源码**，逐字对照源码提取，**严禁虚构**、严禁编造项目中不存在的功能。
- 约束从代码提取；若项目未使用数据库，明确写出"未使用数据库"。
- 若某类信息在源码中不存在，**如实说明**，不得编造。
- 功能模块必须覆盖项目**全部**业务功能，不可遗漏（有多少写多少，模块数量不限）。
- 接口必须列出全部真实接口，一个不漏，逐条编号。
- 文档结构固定为四章：一、功能模块（全部模块 + 功能描述）；二、接口规范（方法、路径、请求参数、返回值格式）；三、数据库表结构（表名、字段名、字段类型、约束条件）；四、接口交互流程（按真实接口调用链文字描述）。

## 三、技术文档写作规范

### 结构

```
一、一级模块名称        ← 对应一个真实功能模块，有几个模块写几章
1.1 二级功能名称
（操作说明文字）
1.2 二级功能名称
（操作说明文字）

二、一级模块名称
2.1 ...
```

- 章节号与小节号保持不变；**模块章节数量与模块名必须与功能规格中的真实模块一一对应**，不要多写也不要漏写。
- 每个小节都必须**展开编写详细内容**，不能只列标题，用自然段落。

### 写作风格（关键）

- **拒绝 AI 味**：不用"综上所述"、"总而言之"、"此外值得一提的是"、"用户可通过…实现"等句式。
- **模拟人工语气**：多用短句，像真人写的操作手册，直接说怎么操作、出现什么结果。
- **截图标注**：凡需截图处用 `【图X-X：XXX界面截图】` 占位，格式必须为 `【图数字-数字：描述】`。**默认不插真实图片**。默认模式下交付时提醒用户自行补图；若用户明确要求"你自己跑起来截图并插进文档"，见第五节「真实插图」。
- 每个功能模块写清操作步骤：打开哪个页面、点击什么按钮、输入什么内容、看到什么结果。

示例片段：

```
一、用户管理模块
1.1 用户登录
打开系统首页，在右上角找到登录入口。输入已注册的用户名和密码，点击登录按钮。
系统验证信息后跳转主界面，右上角会显示用户名。【图1-1：用户登录界面截图】

1.2 用户注册
没有账号的话，点击登录页下方的"立即注册"。填写用户名、密码、邮箱，点击注册即可。
注册成功后会自动跳转到登录页。【图1-2：用户注册界面截图】
```

### 章节归一化（脚本自动处理）

`convert_md_to_docx.py` 会做两步标题修复，避免层级错乱：

- `### 七、配置说明` → `## 七、配置说明`（与"一~六章"同级）
- `#### 7.1 环境配置` → `### 7.1`（两位数字编号升为三级进目录；`#### 6.1.1` 三位编号保持四级）

因此**写 md 时不必纠结标题层级**，按语义写即可。

## 四、文档转换链（docx / pdf）

```bash
# 1) 说明书/技术文档：md → docx（含封面、目录域、页眉"软件名 V1.0 + 页码"）
python "$SKILL_DIR/scripts/convert_md_to_docx.py" technical-documentation.md

# 2) 源程序：txt → docx（等宽字体、行距紧凑，页眉带软件名 + 页码）
python "$SKILL_DIR/scripts/convert_txt_to_docx.py" source-code.txt

# 3) 轻量版（无封面无目录，标题样式齐全）
python "$SKILL_DIR/scripts/convert_to_docx.py" <file>            # 自动识别 .md / .txt

# 4) docx → pdf，并做 60 页裁剪（推荐，功能最全）
python "$SKILL_DIR/scripts/source_to_pdf.py" source-code.docx

# 5) docx → pdf + 更新目录（Word COM 优先，回退 LibreOffice）
python "$SKILL_DIR/scripts/update_toc_and_convert_pdf.py" technical-documentation.docx

# 6) docx → pdf，固定截断前 60 页（不可用时回退）
python "$SKILL_DIR/scripts/convert_docx_to_pdf.py" <file.docx> --max-pages 60

# 7) UNO 精确更新 TOC 并导出 PDF（目录页码最准，推荐用于说明书）
python "$SKILL_DIR/scripts/uno_toc_pdf.py" technical-documentation.docx technical-documentation.pdf
```

**转换顺序（说明书）**：`md → docx →（UNO 更新目录）→ pdf`。目录页码依赖最终排版，必须最后一步用 UNO 重算。

### 目录更新：必须用 UNO（最重要的一条）

`update_toc_and_convert_pdf.py` 在无 MS Word 的机器上会回退 LibreOffice，而 LibreOffice 的
`soffice --convert-to pdf` **不会更新目录域**——PDF 目录页会留
「请右键点击此处，选择"更新域"以生成目录」占位，整块目录空着，
**且退出码为 0、不报任何错，极易漏检**。

**交付前必做校验**：

```python
import pymupdf
d = pymupdf.open('技术文档.pdf')
print('\n'.join(x for x in d[1].get_text().split('\n') if x.strip())[:600])
```

看到 "请右键点击此处" 即为未更新，必须改用 `uno_toc_pdf.py` 重跑：

```bash
python "$SKILL_DIR/scripts/uno_toc_pdf.py" technical-documentation.docx technical-documentation.pdf
# 期望输出：Updated 1 TOC index(es) / PDF generated: ...
```

`uno_toc_pdf.py` 已跨平台自举：**直接 `python` 起手即可**，它发现当前解释器没有 `uno`
模块时会自动换用 LibreOffice 自带的 python 重新执行（Linux 需 `apt install python3-uno`）。
它还会为每次运行创建独立的 `UserInstallation` 临时 profile，不会干扰用户正在使用的
LibreOffice；桥接端口也自动选空闲端口。

### 转换环节的踩坑记录（脚本已内置处理，勿改）

- **页眉固定格式**：`<软件名> V1.0` + 右对齐页码域，宋体小五（sz 18）；页码右端须落在
  **页面最右侧**（右制表位 9360 twips = 16.51cm，与源程序文档同一位置，两份材料页眉右端必须齐）。
- **页眉页码"不右对齐"的坑**：OOXML 里段落级 `<w:tabs>` 是**追加**到样式继承的制表位，
  不是替换。python-docx 默认模板的 `Header` 样式自带 `center@4680` + `right@9360`，
  只 add 一个右制表位的话，制表符会先停在 4680 的**居中位**上——页码被居中到版心中部
  （实测右端 x≈328pt，应为 ≈558pt），而且**不报错**。必须先 `<w:tab w:val="clear" w:pos="4680"/>`
  再放右制表位（clear 靠位置相等生效）。`md_to_docx_images.py` 的 `set_header_tabs()` 已内置。
- **源程序文档 60 页裁剪后页码不连续（1–30 + 236–265）不是缺陷**：`source_to_pdf.py`
  是对 **PDF** 做页选取，不是在转换前删正文，PAGE 域因此保留原始页码——这正是"前 30 页 +
  后 30 页"应有的呈现。别"修"成 1–60；确需连续编号须在 docx 层裁剪后重新转换。
- **页面设置**：A4（11906×16838 twips），上下边距 1440，左右 1800。
- **字体**：正文宋体（SimSun），标题黑体（SimHei），代码 Courier New 小五。macOS/Linux 上
  若装了中文字体，LibreOffice 会自动替换；需强制指定时用 `--font-body` / `--font-head`
  （见 `md_to_docx_images.py --help`）。
- **LibreOffice 找不到**：脚本按 `SOFFICE` / `LIBREOFFICE` 环境变量 → 各平台常见安装路径
  → `shutil.which` 顺序探测，Windows / macOS / Linux 均已内置。
- **转换并发**：多个转换会争抢 LibreOffice 用户配置目录，脚本用 `convertLock`（文件锁）+
  独立 `-env:UserInstallation` 临时 profile 隔离。
- **沙箱环境**：某些沙箱禁止创建命名管道、拒绝写入系统临时目录 —— 脚本已改为
  「子进程输出重定向到文件」并在**当前工作目录**创建临时目录（带写探针校验）。
  不要改回 `subprocess.PIPE` 或 `tempfile.mkdtemp`。
- **页数统计**：优先 PyMuPDF → pypdf → PyPDF2 → pikepdf → 内置正则兜底。内置解析取
  「叶子 `/Type /Page` 数量」与「页面树 `/Count`」的**较小值**（PyMuPDF `garbage=2`
  保存后可能残留未引用页面对象）。
- **PDF 裁剪**：`garbage=2` 足够，**不要用 `garbage=4`**（会重建整份 PDF，大文件极慢）。

### 真实插图（用户要求插入实际截图时）

`convert_md_to_docx.py` 是手搓 OOXML，**不支持图片** —— md 里的 `![图注](x.png)` 会被当
普通文字丢掉。需要插图时改用 `md_to_docx_images.py`（需 `python-docx` + `Pillow`）：

```bash
python "$SKILL_DIR/scripts/md_to_docx_images.py" technical-documentation.md \
       -o technical-documentation.docx \
       -n "软件全称" --version V1.0 --subtitle "软件说明书"
# 随后仍走 UNO 更新目录域（插图会让页码大幅变化，必须重算）
python "$SKILL_DIR/scripts/uno_toc_pdf.py" technical-documentation.docx technical-documentation.pdf
```

排版与 `convert_md_to_docx.py` 一致，另加：

- 图片**等比缩放居中**：`px宽 / 1440 × 14.66cm`，钳在 9.0～14.66cm；高度超 22cm 按高度回缩避免跨页断裂。
- 图片下方自动加**居中小五号深灰图注**（取 `![这里的文字]`）。
- 封面书名按字数自动缩号（≤12 字 28pt / ≤16 字 24pt / 更长 20pt），避免《……》折成两行。
- 封面独立成页，目录另起一页。

**插图前必须做的两件事**：

1. **图片必须独占一行**。md 里占位符常在段末行内，直接替换会让引用留在段落中而被丢弃
   （转换器只识别整行图片，且**静默不报错**）。用
   `re.sub(r"[ \t]*!\[…\]\(…\)[ \t]*", "\n\n![…](…)\n\n", text)` 提到独立段落，
   再 `re.sub(r"\n{3,}", "\n\n", text)` 规整空行。
2. **复核数量**。清点 docx 内嵌图片数（`zipfile` 读 `word/media/`）与 PDF 实际绘制图片数，
   两者都应等于插图总数。注意 PyMuPDF 的 `page.get_images(full=True)` 会因资源字典共享
   给出 `插图数 × 页数` 的**假数量**，必须用 `page.get_image_info()` 统计真正绘制在页上的图。

### 脚本维护要点（改动时别踩回去）

1. **别用 `subprocess.run(..., text=True)` 硬解 UTF-8**：中文系统上 `where soffice` 的输出是
   GBK，会抛 `UnicodeDecodeError`（异常被吞、最终仍能回退，但会打难看的堆栈）。
   要么显式 `encoding="utf-8", errors="replace"`，要么直接用 `shutil.which` 免掉子进程。
2. **注意 `truncate_docx_to_pages` 的"假成功"**：元素数不足时若只 `return True` 而不写文件，
   后续会去转换一个不存在的临时文件。用 `os.path.exists(temp_docx)` 兜底判断。
3. **不要在 `uno_toc_pdf.py` 里无条件杀 soffice**：那会丢掉用户未保存的 Office 文档。
   现已改为 `--force-kill` 显式开启（**默认不杀**）。注意 `--force-kill` 是按**进程名**杀的
   （Windows `taskkill /F /IM soffice.bin`、类 Unix `pkill -f soffice`），**会杀掉机器上
   所有 soffice 实例**，只在确认没人正在编辑文档时才用——它不是"只杀自己启的那个"。
   日常并不需要它：脚本本就为每次运行创建独立临时 profile + 随机空闲端口。

## 五、实战补充：`collect_source_code.py` 的扩展名白名单偏宽

脚本的保留扩展名包含 `.json` / `.html` / `.css` / `.mjs`，并且会把项目里的辅助目录
（如 `tools/` 下的开发脚本、`docs/` 下的产物）一并纳入。补正模式下若项目带有构建/调试
脚本，收上来的文件会夹带非源码内容（实测 97 个文件里混入 3 个 .json、1 个 .mjs）。

**更干净的做法**：手写一份"有序文件清单 + 直接拼接"的汇编脚本，显式罗列
`ORDER: list[Path]`，逐项 `read_text().strip('\n')` 后 `'\n'.join()`。好处有三：

1. 可精确排除配置文件与辅助目录；
2. 可**控制拼接顺序**，而顺序直接决定 60 页裁剪后保留哪部分代码——建议前端按
   "基础设施 → 样式/组件 → 页面（由简至繁，核心业务页面收尾）"排列，
   让"后 30 页"落在大页面代码上而不是样式文件上；
3. 清单里任一文件缺失立即报错（`raise SystemExit`），避免静默漏收。

## 六、60 页规则的页数实测

以 16026 行非空代码 + 1724 行空行（17750 行）为例：`.docx` → PDF 共 **265 页**，
裁剪后交付 60 页，完整版另存 `-full.pdf`。抽样核对每页物理行数约 **59 行**
（A4、上下边距 1440 twips、Courier New 小五紧凑行距）。

判据是"每页不少于 50 行（结束页除外）"，故末页只剩十几行属正常，**不要为此去凑行数**；
但若某页因空行过多导致物理行数不足 50，可对 `source-code.txt` 跑
`remove_empty_lines.py --all` 删除全部空行后重新生成。

## 七、资料索引

- `references/naming-rules.md` — 软著命名规范（含正反例、5 种命名策略）
- `references/domain-list.md` — 领域池（15 个）+ 通用领域备选
- `references/style-list.md` — 前端 10 种视觉风格（选定后在 frontend.md 写具体落地方案）
- `references/output-specs.md` — Explanation.txt 模板、技术文档结构、源程序文档规范
- `references/platform-notes.md` — Windows / macOS / Linux 三平台差异与依赖清单

## 八、交付前自检

- [ ] 名称符合命名规范（后缀、长度、无违禁词、品牌词随机）
- [ ] 源程序无配置文件、无依赖目录、无注释、无文件路径分隔标记
- [ ] 源程序总行数 ≥ 3000（否则材料单薄，需扩大收集范围）
- [ ] 源程序 PDF 已执行 60 页规则（前 30 + 后 30），完整版另存 `-full.pdf`
- [ ] 技术文档模块章节数与功能规格中的模块数一致
- [ ] 技术文档无 AI 味句式，全部小节都有展开正文
- [ ] 截图占位格式统一为 `【图X-X：描述】`，无残留其他格式
- [ ] 若已插图：docx `word/media/` 内嵌图片数 == PDF `get_image_info()` 绘制图片数 == 插图总数
- [ ] Explanation.txt 八项字段齐全，"主要功能"约 700 字且为自然段落
- [ ] docx 页眉为「软件名 V1.0 + 页码」，且页码真的贴到**页面最右侧**
      （A4 实测右端 x≈558pt；若 x≈328pt 说明被样式自带的居中制表位截住了）
- [ ] **技术文档 PDF 第 2 页目录已带页码**（无 MS Word 时必须用 `uno_toc_pdf.py` 重跑）
