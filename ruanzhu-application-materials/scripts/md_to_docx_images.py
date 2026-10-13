#!/usr/bin/env python3
"""Markdown → .docx（封面 + 目录域 + 页眉页码 + 真实插图）。

与同目录 convert_md_to_docx.py 的区别：
那个脚本按 OOXML 手工拼装 XML，启动快，但**不支持图片**——Markdown 里的
`![图注](xxx.png)` 会被当成普通文字丢掉。本脚本基于 python-docx，能把图片
真正嵌入文档（等比缩放居中 + 图片下方自动加小五号图注），用于
「截图已经拿到、需要把截图插进文档对应位置」的场景。

排版沿用 skill 规范：正文宋体小四、标题黑体、代码 Courier New 小五、
页眉「软件名 V1.0 + 页码右对齐到页面最右侧」（与源程序文档同一位置）、
封面 + 目录域（TOC \\o "1-3"）。

用法：
  python md_to_docx_images.py 技术文档.md -o 技术文档.docx -n "软件全称"
可选：
  --version V1.0      页眉与封面上的版本号
  --subtitle 文字     封面副标题（默认取 Markdown 首个一级标题）
  --toc / --no-toc    是否生成目录域（默认生成）
  --no-cover-break    目录后不分页（默认为目录后分页，正文另起一页）
  --font-preset NAME  windows / macos / linux / auto（默认 auto=SimSun+SimHei）
  --font-body / --font-head / --font-code   逐个覆盖字体名
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BODY_FONT = "SimSun"          # 正文宋体（软著提交件的通行字体，Windows Office 自带）
HEAD_FONT = "SimHei"          # 标题黑体
CODE_FONT = "Courier New"     # 代码等宽
BODY_SIZE = Pt(12)            # 小四
CODE_SIZE = Pt(9)             # 小五
SMALL_SIZE = Pt(9)            # 小五
TABLE_SIZE = Pt(10)
HEAD_SIZES = {1: Pt(20), 2: Pt(16), 3: Pt(14), 4: Pt(12)}

# macOS / Linux 上通常没有 SimSun / SimHei，需要时的等价替换：
#   macOS   宋体→STSong      黑体→STHeiti
#   Linux   宋体→Noto Serif CJK SC   黑体→Noto Sans CJK SC
# （LibreOffice 一般能自动替换，仅在字体缺失导致排版明显异常时才需要手动指定。）
FONT_PRESETS = {
    "windows": ("SimSun", "SimHei", "Courier New"),
    "macos": ("STSong", "STHeiti", "Menlo"),
    "linux": ("Noto Serif CJK SC", "Noto Sans CJK SC", "DejaVu Sans Mono"),
}


def apply_fonts(preset: str = "auto", body: str | None = None,
                head: str | None = None, code: str | None = None) -> None:
    """把字体选择写回模块全局。

    set_run / add_inline 的默认值在**调用时**读这些全局，所以在这里改就能全局生效。
    默认保持 SimSun / SimHei —— 这是软著提交件的通行约定，Windows Office 自带，
    换成别的字体反而可能让评审环境显示异常。仅在 macOS / Linux 上因缺字导致排版
    明显走样时，才用 --font-preset 或 --font-body / --font-head 换成平台等价字体。
    """
    global BODY_FONT, HEAD_FONT, CODE_FONT
    if preset and preset != "auto":
        BODY_FONT, HEAD_FONT, CODE_FONT = FONT_PRESETS[preset]
    if body:
        BODY_FONT = body
    if head:
        HEAD_FONT = head
    if code:
        CODE_FONT = code

CONTENT_WIDTH_CM = 14.66      # A4(21cm) 减去左右各 3.17cm 页边距
MAX_IMAGE_HEIGHT_CM = 22.0
# 截图是按 1440px 视口宽度采的，按同一比例换算可保持各图之间文字大小一致
SCREENSHOT_PX_BASE = 1440
MIN_IMAGE_WIDTH_CM = 9.0
MAX_IMAGE_WIDTH_CM = CONTENT_WIDTH_CM

# 页眉页码的右端位置。取 9360 twips = 16.51cm，与 convert_txt_to_docx.py 生成的
# 源程序文档完全一致——页眉横跨整页宽度，页码落在页面最右侧（而不是版心右边界）。
# 这里刻意不用 CONTENT_WIDTH_CM：技术文档与源程序文档是一套材料，两份的页眉右端
# 必须对齐在同一个位置，否则并列翻阅时明显不齐。
HEADER_RIGHT_TAB_TWIPS = 9360
# python-docx 默认模板的 Header 样式自带 center@4680 + right@9360 两个制表位，
# 其中居中位会抢先吃掉制表符，必须显式 clear 掉（见 set_header_tabs）。
STYLE_HEADER_CENTER_TAB_TWIPS = 4680

IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|$")
INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


# --------------------------------------------------------------------------- #
# 基础排版工具
# --------------------------------------------------------------------------- #
def set_run(run, font: str | None = None, size: Pt | None = None, bold: bool = False):
    """设置 run 的字体，同时写入 eastAsia，否则中文会回落到默认字体。

    font / size 的默认值在**调用时**从模块全局解析（而非 def 时的默认参数），
    这样命令行调整字体后所有调用点都能生效。
    """
    font = font or BODY_FONT
    size = size or BODY_SIZE
    run.font.name = font
    run.font.size = size
    run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), font)


def shade(element, fill: str):
    """给段落或单元格加底色。"""
    pr = element.get_or_add_pPr() if element.tag.endswith("}p") else element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def add_inline(paragraph, text: str, size: Pt | None = None, font: str | None = None):
    """处理 **粗体**、`行内代码`、*斜体*。"""
    size = size or BODY_SIZE
    font = font or BODY_FONT
    for piece in INLINE_RE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            set_run(paragraph.add_run(piece[2:-2]), font=font, size=size, bold=True)
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            set_run(paragraph.add_run(piece[1:-1]), font=CODE_FONT, size=Pt(size.pt - 1))
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            run = paragraph.add_run(piece[1:-1])
            set_run(run, font=font, size=size)
            run.italic = True
        else:
            set_run(paragraph.add_run(piece), font=font, size=size)


def field(paragraph, instruction: str, placeholder: str = ""):
    """插入一个 Word 域（目录域 / 页码域）。"""
    for kind in ("begin", None, "separate", None, "end"):
        run = paragraph.add_run()
        set_run(run, size=SMALL_SIZE)
        if kind:
            char = OxmlElement("w:fldChar")
            char.set(qn("w:fldCharType"), kind)
            run._element.append(char)
        elif instruction and "instrText" not in paragraph._element.xml:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = f" {instruction} "
            run._element.append(instr)
        elif placeholder:
            text = OxmlElement("w:t")
            text.text = placeholder
            run._element.append(text)


def add_page_number_field(paragraph):
    field(paragraph, "PAGE", "1")


def add_toc_field(paragraph):
    field(paragraph, 'TOC \\o "1-3" \\h \\z \\u', "请右键点击此处，选择“更新域”以生成目录")


def set_header_tabs(paragraph) -> None:
    """把页眉段落设为「左端软件名 + 页面最右侧页码」。

    **这里有个必须避开的坑**：OOXML 中段落级的 `<w:tabs>` 是**追加**到样式继承
    来的制表位，而不是替换。python-docx 默认模板的 Header 样式自带
    `center@4680` + `right@9360` 两个制表位；如果只在段落上 add 一个右制表位，
    制表符仍会先停在 4680 的居中位上，页码就被居中到版心中部（约为版心宽度的 55%
    处），看起来完全不像右对齐——而且不报任何错。

    正确做法是先用 `w:val="clear"` 显式清掉样式里的居中位，再放自己的右制表位。
    clear 是靠 **位置相等** 生效的，所以位置值要和样式里的完全一致（4680）。
    """
    tabs = paragraph._p.get_or_add_pPr().get_or_add_tabs()
    for old in list(tabs):
        tabs.remove(old)
    for pos, val in ((STYLE_HEADER_CENTER_TAB_TWIPS, "clear"),
                     (HEADER_RIGHT_TAB_TWIPS, "right")):
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), val)
        tab.set(qn("w:pos"), str(pos))
        tabs.append(tab)


# --------------------------------------------------------------------------- #
# 图片尺寸
# --------------------------------------------------------------------------- #
def image_width_cm(path: Path) -> float:
    try:
        from PIL import Image

        with Image.open(path) as img:
            px_w, px_h = img.size
    except Exception:
        return MAX_IMAGE_WIDTH_CM

    width = px_w / SCREENSHOT_PX_BASE * CONTENT_WIDTH_CM
    width = min(MAX_IMAGE_WIDTH_CM, max(MIN_IMAGE_WIDTH_CM, width))
    height = width * px_h / px_w
    if height > MAX_IMAGE_HEIGHT_CM:          # 太高的图按高度回缩，避免跨页断裂
        width = width * MAX_IMAGE_HEIGHT_CM / height
    return round(width, 2)


def add_image(doc: Document, src: Path, alt: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.add_run().add_picture(str(src), width=Cm(image_width_cm(src)))
    if alt:
        caption = doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption.paragraph_format.space_after = Pt(10)
        run = caption.add_run(alt)
        set_run(run, size=SMALL_SIZE)
        run.font.color.rgb = RGBColor(0x40, 0x40, 0x40)


# --------------------------------------------------------------------------- #
# 文档骨架
# --------------------------------------------------------------------------- #
def new_document(name: str, version: str, subtitle: str, with_toc: bool,
                 break_after_cover: bool) -> Document:
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)

    # 页眉：软件名 V1.0（左端） + 页码（页面最右侧）
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.text = ""
    set_header_tabs(hp)
    set_run(hp.add_run(f"{name} {version}"), size=SMALL_SIZE)
    hp.add_run("\t")
    add_page_number_field(hp)

    # 正文默认字体
    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = BODY_SIZE
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    style.paragraph_format.line_spacing = 1.5

    # 封面
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(150)
    title.paragraph_format.space_after = Pt(24)
    # 书名较长时自动缩号，避免《……》被折成两行（正文可用宽度 14.66cm）
    title_pt = 28 if len(name) <= 12 else (24 if len(name) <= 16 else 20)
    set_run(title.add_run(f"《{name}》"), font=HEAD_FONT, size=Pt(title_pt), bold=True)

    if subtitle:
        sub = doc.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run(sub.add_run(subtitle), font=HEAD_FONT, size=Pt(14))

    if with_toc:
        doc.add_page_break()          # 封面独立成页，目录另起一页
        toc_head = doc.add_paragraph()
        toc_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run(toc_head.add_run("目录"), font=HEAD_FONT, size=Pt(16), bold=True)
        add_toc_field(doc.add_paragraph())

    if break_after_cover:
        doc.add_page_break()

    return doc


def add_heading(doc: Document, text: str, level: int):
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(text)
    set_run(run, font=HEAD_FONT, size=HEAD_SIZES.get(level, Pt(12)), bold=True)
    run.font.color.rgb = RGBColor(0, 0, 0)
    return paragraph


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    width = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=width)
    table.style = "Table Grid"
    table.autofit = True
    for r_index, row in enumerate(rows):
        for c_index in range(width):
            cell = table.cell(r_index, c_index)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.space_after = Pt(0)
            value = row[c_index] if c_index < len(row) else ""
            add_inline(paragraph, value, size=TABLE_SIZE)
            if r_index == 0:
                for run in paragraph.runs:
                    run.bold = True
                shade(cell._tc, "EDF1F7")
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def add_code_block(doc: Document, lines: list[str]) -> None:
    for line in lines:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.left_indent = Cm(0.6)
        set_run(paragraph.add_run(line if line else " "), font=CODE_FONT, size=CODE_SIZE)
        shade(paragraph._p, "F5F6F8")
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


# --------------------------------------------------------------------------- #
# 主转换流程
# --------------------------------------------------------------------------- #
def convert(md_path: Path, out_path: Path, name: str, version: str,
            subtitle: str | None, with_toc: bool, break_after_cover: bool) -> dict:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    doc = new_document(name, version, subtitle or "", with_toc, break_after_cover)

    stats = {"headings": 0, "images": 0, "tables": 0, "missing": [], "code": 0}
    index = 0
    first_heading_used = False

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        # 代码块
        if stripped.startswith("```"):
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            add_code_block(doc, block)
            stats["code"] += 1
            continue

        # 图片
        match = IMAGE_RE.match(stripped)
        if match:
            src = Path(match.group("src"))
            if not src.is_absolute():
                src = (md_path.parent / src).resolve()
            if src.exists():
                add_image(doc, src, match.group("alt").strip())
                stats["images"] += 1
            else:
                stats["missing"].append(match.group("src"))
                paragraph = doc.add_paragraph()
                add_inline(paragraph, f"【缺图：{match.group('alt')}】")
            index += 1
            continue

        # 标题
        match = HEADING_RE.match(stripped)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            if level == 1 and not first_heading_used:
                # 首个一级标题与封面重复，作为正文标题处理一次即可
                first_heading_used = True
            add_heading(doc, text, min(level, 4))
            stats["headings"] += 1
            index += 1
            continue

        # 分隔线
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            index += 1
            continue

        # 表格（| a | b | 换行 |---|）
        if stripped.startswith("|") and index + 1 < len(lines) and TABLE_SEP_RE.match(lines[index + 1].strip()):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                raw = lines[index].strip().strip("|")
                if not TABLE_SEP_RE.match(lines[index].strip()):
                    rows.append([cell.strip() for cell in raw.split("|")])
                index += 1
            add_table(doc, rows)
            stats["tables"] += 1
            continue

        # 列表
        bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if bullet or numbered:
            style = "List Bullet" if bullet else "List Number"
            paragraph = doc.add_paragraph(style=style)
            paragraph.paragraph_format.line_spacing = 1.5
            add_inline(paragraph, (bullet or numbered).group(1))
            index += 1
            continue

        # 引用
        if stripped.startswith(">"):
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.8)
            add_inline(paragraph, stripped.lstrip("> ").strip())
            index += 1
            continue

        # 空行
        if not stripped:
            index += 1
            continue

        # 普通段落
        paragraph = doc.add_paragraph()
        add_inline(paragraph, stripped)
        index += 1

    doc.save(str(out_path))
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown 转 docx（支持真实插图）")
    parser.add_argument("md", type=Path, help="Markdown 文件")
    parser.add_argument("-o", "--output", type=Path, required=True, help="输出 docx")
    parser.add_argument("-n", "--name", required=True, help="软件全称（用于封面与页眉）")
    parser.add_argument("--version", default="V1.0")
    parser.add_argument("--subtitle", default=None, help="封面副标题，默认取首个一级标题")
    parser.add_argument("--no-toc", action="store_true", help="不生成目录域")
    parser.add_argument("--no-cover-break", action="store_true", help="封面后不分页")
    parser.add_argument("--font-preset", choices=["auto", "windows", "macos", "linux"],
                        default="auto",
                        help="按平台切换中文字体组合，默认 auto 保持 SimSun/SimHei")
    parser.add_argument("--font-body", default=None, help="覆盖正文字体名（默认 SimSun）")
    parser.add_argument("--font-head", default=None, help="覆盖标题字体名（默认 SimHei）")
    parser.add_argument("--font-code", default=None, help="覆盖代码字体名（默认 Courier New）")
    args = parser.parse_args()

    apply_fonts(args.font_preset, args.font_body, args.font_head, args.font_code)

    if not args.md.exists():
        print(f"找不到 {args.md}", file=sys.stderr)
        return 1

    subtitle = args.subtitle
    if subtitle is None:
        for line in args.md.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                subtitle = line[2:].strip()
                break

    stats = convert(args.md, args.output, args.name, args.version, subtitle,
                     not args.no_toc, not args.no_cover_break)
    print(f"已生成 {args.output}")
    print(f"  标题 {stats['headings']} 个 / 插图 {stats['images']} 张 / "
          f"表格 {stats['tables']} 个 / 代码块 {stats['code']} 个")
    if stats["missing"]:
        print(f"  ⚠ 缺失图片 {len(stats['missing'])} 张：{stats['missing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
