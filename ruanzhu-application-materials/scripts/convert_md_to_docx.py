#!/usr/bin/env python3
"""Convert Markdown (.md) to .docx with cover page, TOC, and header."""

import argparse
import os
import re
import sys
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RML = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

def make_content_types():
    return (
        XML_DECL + '\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        '</Types>'
    )

def make_rels():
    return (
        XML_DECL + '\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="word/styles.xml"/>'
        '</Relationships>'
    )

def make_doc_rels():
    return (
        XML_DECL + '\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
        '</Relationships>'
    )

STYLES_XML = XML_DECL + '''
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
  <w:name w:val="Normal"/>
  <w:rPr><w:rFonts w:eastAsia="SimSun"/><w:sz w:val="24"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading1">
  <w:name w:val="heading 1"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr><w:outlineLvl w:val="0"/></w:pPr>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="36"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading2">
  <w:name w:val="heading 2"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr><w:outlineLvl w:val="1"/></w:pPr>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="30"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading3">
  <w:name w:val="heading 3"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr><w:outlineLvl w:val="2"/></w:pPr>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="26"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading4">
  <w:name w:val="heading 4"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr><w:outlineLvl w:val="3"/></w:pPr>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="24"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading5">
  <w:name w:val="heading 5"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr><w:outlineLvl w:val="4"/></w:pPr>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="22"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="CodeBlock">
  <w:name w:val="Code Block"/>
  <w:basedOn w:val="Normal"/>
  <w:rPr><w:rFonts w:eastAsia="SimSun" w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Header">
  <w:name w:val="header"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr>
    <w:tabs>
      <w:tab w:val="center" w:pos="4680"/>
      <w:tab w:val="right" w:pos="9360"/>
    </w:tabs>
    <w:jc w:val="both"/>
  </w:pPr>
  <w:rPr><w:rFonts w:eastAsia="SimSun"/><w:sz w:val="18"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="TOCHeading">
  <w:name w:val="TOC Heading"/>
  <w:basedOn w:val="Heading1"/>
  <w:pPr><w:outlineLvl w:val="9"/></w:pPr>
</w:style>
<w:style w:type="paragraph" w:styleId="TOC1">
  <w:name w:val="toc 1"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr>
    <w:tabs><w:tab w:val="right" w:pos="9072" w:leader="dot"/></w:tabs>
  </w:pPr>
</w:style>
<w:style w:type="paragraph" w:styleId="TOC2">
  <w:name w:val="toc 2"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr>
    <w:ind w:left="420"/>
    <w:tabs><w:tab w:val="right" w:pos="9072" w:leader="dot"/></w:tabs>
  </w:pPr>
</w:style>
<w:style w:type="paragraph" w:styleId="TOC3">
  <w:name w:val="toc 3"/>
  <w:basedOn w:val="Normal"/>
  <w:pPr>
    <w:ind w:left="840"/>
    <w:tabs><w:tab w:val="right" w:pos="9072" w:leader="dot"/></w:tabs>
  </w:pPr>
</w:style>
</w:styles>'''

def make_header_xml(software_name):
    return (
        XML_DECL + '\n'
        '<w:hdr xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
        '<w:p>'
        '<w:pPr>'
        '<w:pStyle w:val="Header"/>'
        '<w:tabs>'
        '<w:tab w:val="center" w:pos="4680"/>'
        '<w:tab w:val="right" w:pos="9360"/>'
        '</w:tabs>'
        '<w:jc w:val="both"/>'
        '</w:pPr>'
        '<w:r>'
        '<w:rPr>'
        '<w:rFonts w:eastAsia="SimSun"/>'
        '<w:sz w:val="18"/>'
        '</w:rPr>'
        f'<w:t xml:space="preserve">{software_name} V1.0</w:t>'
        '</w:r>'
        '<w:r>'
        '<w:rPr>'
        '<w:rFonts w:eastAsia="SimSun"/>'
        '<w:sz w:val="18"/>'
        '</w:rPr>'
        '<w:tab/>'
        '</w:r>'
        '<w:r>'
        '<w:rPr>'
        '<w:rFonts w:eastAsia="SimSun"/>'
        '<w:sz w:val="18"/>'
        '</w:rPr>'
        '<w:tab/>'
        '</w:r>'
        '<w:r>'
        '<w:rPr>'
        '<w:rFonts w:eastAsia="SimSun"/>'
        '<w:sz w:val="18"/>'
        '</w:rPr>'
        '<w:fldChar w:fldCharType="begin"/>'
        '</w:r>'
        '<w:r>'
        '<w:rPr>'
        '<w:rFonts w:eastAsia="SimSun"/>'
        '<w:sz w:val="18"/>'
        '</w:rPr>'
        '<w:instrText xml:space="preserve">PAGE</w:instrText>'
        '</w:r>'
        '<w:r>'
        '<w:rPr>'
        '<w:rFonts w:eastAsia="SimSun"/>'
        '<w:sz w:val="18"/>'
        '</w:rPr>'
        '<w:fldChar w:fldCharType="end"/>'
        '</w:r>'
        '</w:p>'
        '</w:hdr>'
    )

def wml_elem(tag):
    return Element(f"{{{WML}}}{tag}")

def body():
    return wml_elem("body")

def add_empty_para(body_e, count=1):
    for _ in range(count):
        SubElement(body_e, f"{{{WML}}}p")

def add_cover_title(body_e, software_name):
    para = SubElement(body_e, f"{{{WML}}}p")
    pPr = SubElement(para, f"{{{WML}}}pPr")
    jc = SubElement(pPr, f"{{{WML}}}jc")
    jc.set(f"{{{WML}}}val", "center")
    
    run = SubElement(para, f"{{{WML}}}r")
    rPr = SubElement(run, f"{{{WML}}}rPr")
    rFonts = SubElement(rPr, f"{{{WML}}}rFonts")
    rFonts.set(f"{{{WML}}}eastAsia", "SimSun")
    rFonts.set(f"{{{WML}}}ascii", "SimSun")
    rFonts.set(f"{{{WML}}}hAnsi", "SimSun")
    b = SubElement(rPr, f"{{{WML}}}b")
    sz = SubElement(rPr, f"{{{WML}}}sz")
    sz.set(f"{{{WML}}}val", "56")
    t = SubElement(run, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = f"\u300a{software_name}\u300b"

def add_page_break(body_e):
    para = SubElement(body_e, f"{{{WML}}}p")
    run = SubElement(para, f"{{{WML}}}r")
    br = SubElement(run, f"{{{WML}}}br")
    br.set(f"{{{WML}}}type", "page")

def add_toc_heading(body_e):
    para = SubElement(body_e, f"{{{WML}}}p")
    pPr = SubElement(para, f"{{{WML}}}pPr")
    pStyle = SubElement(pPr, f"{{{WML}}}pStyle")
    pStyle.set(f"{{{WML}}}val", "TOCHeading")
    run = SubElement(para, f"{{{WML}}}r")
    t = SubElement(run, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = "目录"

def add_toc_field(body_e):
    para = SubElement(body_e, f"{{{WML}}}p")
    
    run1 = SubElement(para, f"{{{WML}}}r")
    fldChar1 = SubElement(run1, f"{{{WML}}}fldChar")
    fldChar1.set(f"{{{WML}}}fldCharType", "begin")
    
    run2 = SubElement(para, f"{{{WML}}}r")
    instrText = SubElement(run2, f"{{{WML}}}instrText")
    instrText.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
    
    run3 = SubElement(para, f"{{{WML}}}r")
    fldChar2 = SubElement(run3, f"{{{WML}}}fldChar")
    fldChar2.set(f"{{{WML}}}fldCharType", "separate")
    
    run4 = SubElement(para, f"{{{WML}}}r")
    t = SubElement(run4, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = '请右键点击此处，选择"更新域"以生成目录'
    
    run5 = SubElement(para, f"{{{WML}}}r")
    fldChar3 = SubElement(run5, f"{{{WML}}}fldChar")
    fldChar3.set(f"{{{WML}}}fldCharType", "end")

def add_heading_para(body_e, level, text):
    h = SubElement(body_e, f"{{{WML}}}p")
    pPr = SubElement(h, f"{{{WML}}}pPr")
    pStyle = SubElement(pPr, f"{{{WML}}}pStyle")
    pStyle.set(f"{{{WML}}}val", f"Heading{level}")
    spacing = SubElement(pPr, f"{{{WML}}}spacing")
    spacing.set(f"{{{WML}}}before", "240")
    spacing.set(f"{{{WML}}}after", "120")
    run = SubElement(h, f"{{{WML}}}r")
    t = SubElement(run, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return h

def add_text_para(body_e, text, is_code=False):
    para = SubElement(body_e, f"{{{WML}}}p")
    if is_code:
        pPr = SubElement(para, f"{{{WML}}}pPr")
        pStyle = SubElement(pPr, f"{{{WML}}}pStyle")
        pStyle.set(f"{{{WML}}}val", "CodeBlock")
        ind = SubElement(pPr, f"{{{WML}}}ind")
        ind.set(f"{{{WML}}}left", "360")
    run = SubElement(para, f"{{{WML}}}r")
    t = SubElement(run, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return para

def add_table(body_e, rows):
    if not rows:
        return

    table = SubElement(body_e, f"{{{WML}}}tbl")

    tblPr = SubElement(table, f"{{{WML}}}tblPr")
    tblStyle = SubElement(tblPr, f"{{{WML}}}tblStyle")
    tblStyle.set(f"{{{WML}}}val", "TableGrid")
    tblW = SubElement(tblPr, f"{{{WML}}}tblW")
    tblW.set(f"{{{WML}}}w", "5000")
    tblW.set(f"{{{WML}}}type", "pct")
    tblBorders = SubElement(tblPr, f"{{{WML}}}tblBorders")

    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = SubElement(tblBorders, f"{{{WML}}}{border_name}")
        border.set(f"{{{WML}}}val", "single")
        border.set(f"{{{WML}}}sz", "4")
        border.set(f"{{{WML}}}space", "0")
        border.set(f"{{{WML}}}color", "000000")

    tblLook = SubElement(tblPr, f"{{{WML}}}tblLook")
    tblLook.set(f"{{{WML}}}val", "04A0")
    tblLook.set(f"{{{WML}}}firstRow", "1")
    tblLook.set(f"{{{WML}}}lastRow", "0")
    tblLook.set(f"{{{WML}}}firstColumn", "1")
    tblLook.set(f"{{{WML}}}lastColumn", "0")
    tblLook.set(f"{{{WML}}}noHBand", "0")
    tblLook.set(f"{{{WML}}}noVBand", "1")

    num_cols = len(rows[0]) if rows else 0

    tblGrid = SubElement(table, f"{{{WML}}}tblGrid")
    for _ in range(num_cols):
        gridCol = SubElement(tblGrid, f"{{{WML}}}gridCol")
        gridCol.set(f"{{{WML}}}w", str(9360 // num_cols))

    for row_idx, row_cells in enumerate(rows):
        tr = SubElement(table, f"{{{WML}}}tr")

        for cell_text in row_cells:
            tc = SubElement(tr, f"{{{WML}}}tc")
            tcPr = SubElement(tc, f"{{{WML}}}tcPr")
            tcW = SubElement(tcPr, f"{{{WML}}}tcW")
            tcW.set(f"{{{WML}}}w", str(9360 // num_cols))
            tcW.set(f"{{{WML}}}type", "dxa")

            if row_idx == 0:
                shd = SubElement(tcPr, f"{{{WML}}}shd")
                shd.set(f"{{{WML}}}val", "clear")
                shd.set(f"{{{WML}}}color", "auto")
                shd.set(f"{{{WML}}}fill", "D9E2F3")

            p = SubElement(tc, f"{{{WML}}}p")
            pPr = SubElement(p, f"{{{WML}}}pPr")
            spacing = SubElement(pPr, f"{{{WML}}}spacing")
            spacing.set(f"{{{WML}}}before", "40")
            spacing.set(f"{{{WML}}}after", "40")

            run = SubElement(p, f"{{{WML}}}r")
            rPr = SubElement(run, f"{{{WML}}}rPr")
            rFonts = SubElement(rPr, f"{{{WML}}}rFonts")
            rFonts.set(f"{{{WML}}}eastAsia", "SimSun")
            rFonts.set(f"{{{WML}}}ascii", "SimSun")
            rFonts.set(f"{{{WML}}}hAnsi", "SimSun")
            sz = SubElement(rPr, f"{{{WML}}}sz")
            sz.set(f"{{{WML}}}val", "20")

            if row_idx == 0:
                b = SubElement(rPr, f"{{{WML}}}b")

            t = SubElement(run, f"{{{WML}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = cell_text.strip()

def extract_software_name(content):
    for line in content.split("\n"):
        if line.startswith("# "):
            name = line[2:].strip()
            for suffix in ["使用说明书", "使用手册", "操作手册", "技术文档"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            return name
    return ""

def convert_markdown(input_path, output_path, software_name=None):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 章节标题归一化：### 七、配置说明 → ## 七、配置说明（与一~六章同级，避免层级错乱）
    content = re.sub(r'^(#{2,4})\s+([一二三四五六七八九十]+、[^\n]*)', r'## \2', content, flags=re.M)
    # 子节标题提升：#### 7.1 环境配置 → ### 7.1（两位数字编号进目录三级；#### 6.1.1 三位编号保持四级）
    content = re.sub(r'^####\s+(\d+\.\d+)(?!\.)\s+', r'### \1 ', content, flags=re.M)

    if not software_name:
        software_name = extract_software_name(content)

    b = body()
    
    # 第一页：封面
    add_empty_para(b, 2)
    add_cover_title(b, software_name)
    add_page_break(b)
    
    # 第二页：目录
    add_toc_heading(b)
    add_toc_field(b)
    add_page_break(b)
    
    # 正文内容
    in_code = False
    fence_lang = ""
    table_rows = []
    in_table = False

    for line in content.split("\n"):
        if line.startswith("```"):
            if not in_code:
                fence_lang = line[3:].strip().lower()
            in_code = not in_code
            continue

        if in_code:
            # 代码块未闭合防御：代码块内出现标题样式行（非注释型语言）→ 视为代码块提前结束
            # 避免未闭合的 ``` 吞掉后续所有标题（如 ### 七、配置说明）
            if (re.match(r'^#{1,6}\s+\S', line) and len(line.strip()) <= 30
                    and fence_lang not in ('yaml', 'yml', 'python', 'py', 'bash', 'sh', 'shell', 'powershell')):
                in_code = False
                fence_lang = ""
                # 继续走标题解析（不 continue）
            else:
                if in_table and table_rows:
                    add_table(b, table_rows)
                    table_rows = []
                    in_table = False
                if line.strip():
                    add_text_para(b, line, is_code=True)
                else:
                    add_text_para(b, "", is_code=False)
                continue

        if line.startswith("|") and "|" in line[1:]:
            if re.match(r'^\|[\s\-:|]+\|$', line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            table_rows.append(cells)
            in_table = True
            continue
        else:
            if in_table and table_rows:
                add_table(b, table_rows)
                table_rows = []
                in_table = False

        if not line.strip():
            continue

        h1 = re.match(r"^# (.+)", line)
        if h1:
            add_heading_para(b, 1, h1.group(1).strip())
            continue
        h2 = re.match(r"^## (.+)", line)
        if h2:
            add_heading_para(b, 2, h2.group(1).strip())
            continue
        h3 = re.match(r"^### (.+)", line)
        if h3:
            add_heading_para(b, 3, h3.group(1).strip())
            continue
        h4 = re.match(r"^#### (.+)", line)
        if h4:
            add_heading_para(b, 4, h4.group(1).strip())
            continue
        h5 = re.match(r"^##### (.+)", line)
        if h5:
            add_heading_para(b, 5, h5.group(1).strip())
            continue

        if re.match(r"^[\-\*]\s+", line):
            text = re.sub(r"^[\-\*]\s+", "", line)
            para = SubElement(b, f"{{{WML}}}p")
            pPr = SubElement(para, f"{{{WML}}}pPr")
            ind = SubElement(pPr, f"{{{WML}}}ind")
            ind.set(f"{{{WML}}}left", "720")
            ind.set(f"{{{WML}}}hanging", "360")
            run = SubElement(para, f"{{{WML}}}r")
            t = SubElement(run, f"{{{WML}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = "- " + text
            continue

        ol = re.match(r"^\d+[\.\)、]\s*(.+)", line)
        if ol:
            text = ol.group(1)
            para = SubElement(b, f"{{{WML}}}p")
            pPr = SubElement(para, f"{{{WML}}}pPr")
            ind = SubElement(pPr, f"{{{WML}}}ind")
            ind.set(f"{{{WML}}}left", "720")
            ind.set(f"{{{WML}}}hanging", "360")
            run = SubElement(para, f"{{{WML}}}r")
            t = SubElement(run, f"{{{WML}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = text
            continue

        add_text_para(b, line)

    if in_table and table_rows:
        add_table(b, table_rows)

    doc = wml_elem("document")
    doc.append(b)
    
    sectPr = SubElement(b, f"{{{WML}}}sectPr")
    
    pgMar = SubElement(sectPr, f"{{{WML}}}pgMar")
    pgMar.set(f"{{{WML}}}top", "1440")
    pgMar.set(f"{{{WML}}}right", "1800")
    pgMar.set(f"{{{WML}}}bottom", "1440")
    pgMar.set(f"{{{WML}}}left", "1800")
    pgMar.set(f"{{{WML}}}header", "851")
    pgMar.set(f"{{{WML}}}footer", "992")
    pgMar.set(f"{{{WML}}}gutter", "0")
    
    pgSz = SubElement(sectPr, f"{{{WML}}}pgSz")
    pgSz.set(f"{{{WML}}}w", "11906")
    pgSz.set(f"{{{WML}}}h", "16838")
    
    headerRef = SubElement(sectPr, f"{{{WML}}}headerReference")
    headerRef.set(f"{{{WML}}}type", "default")
    headerRef.set(f"{{{RML}}}id", "rId3")
    
    doc_xml = (
        XML_DECL + '\n' +
        tostring(doc, encoding="unicode")
        .replace("<ns0:document", '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"')
        .replace("ns0:", "w:")
        .replace("ns1:", "r:")
    )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", make_content_types())
        zf.writestr("_rels/.rels", make_rels())
        zf.writestr("word/document.xml", doc_xml)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/_rels/document.xml.rels", make_doc_rels())
        zf.writestr("word/header1.xml", make_header_xml(software_name))
    print(f"[OK] {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to DOCX with cover, TOC, and header")
    parser.add_argument("input", help="Input .md file path")
    parser.add_argument("--output", "-o", help="Output .docx file path")
    parser.add_argument("--name", "-n", help="Software name for cover and header")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(args.input)[1].lower()
    if ext != ".md":
        print(f"Error: input must be .md file, got {ext}", file=sys.stderr)
        sys.exit(1)

    output = args.output or os.path.splitext(args.input)[0] + ".docx"
    convert_markdown(args.input, output, args.name)

if __name__ == "__main__":
    main()