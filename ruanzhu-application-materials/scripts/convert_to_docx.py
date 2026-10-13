#!/usr/bin/env python3
"""Convert Markdown (.md) and plain text (.txt) to .docx using only stdlib (zipfile + xml)."""

import argparse
import os
import re
import sys
import zipfile
import html
from xml.etree.ElementTree import Element, SubElement, tostring

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

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
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="36"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading2">
  <w:name w:val="heading 2"/>
  <w:basedOn w:val="Normal"/>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="30"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading3">
  <w:name w:val="heading 3"/>
  <w:basedOn w:val="Normal"/>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="26"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading4">
  <w:name w:val="heading 4"/>
  <w:basedOn w:val="Normal"/>
  <w:rPr><w:rFonts w:eastAsia="SimHei"/><w:b/><w:sz w:val="24"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading5">
  <w:name w:val="heading 5"/>
  <w:basedOn w:val="Normal"/>
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

WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def wml_elem(tag):
    return Element(f"{{{WML}}}{tag}")

def body():
    return wml_elem("body")

def p():
    return wml_elem("p")

def r():
    return wml_elem("r")

def rPr():
    return wml_elem("rPr")

def t(text=""):
    e = wml_elem("t")
    e.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    e.text = text
    return e

def add_run(para, text, bold=False, font_east=None, font_ascii=None, size=None, color=None):
    run = SubElement(para, f"{{{WML}}}r")
    rpr = SubElement(run, f"{{{WML}}}rPr")
    if bold:
        b = SubElement(rpr, f"{{{WML}}}b")
    rFonts = SubElement(rpr, f"{{{WML}}}rFonts")
    if font_east:
        rFonts.set(f"{{{WML}}}eastAsia", font_east)
    if font_ascii:
        rFonts.set(f"{{{WML}}}ascii", font_ascii)
        rFonts.set(f"{{{WML}}}hAnsi", font_ascii)
    if size:
        sz = SubElement(rpr, f"{{{WML}}}sz")
        sz.set(f"{{{WML}}}val", str(size))
    if color:
        c = SubElement(rpr, f"{{{WML}}}color")
        c.set(f"{{{WML}}}val", color)
    t = SubElement(run, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return run

def add_heading_para(body_e, level, text):
    h = SubElement(body_e, f"{{{WML}}}p")
    pPr = SubElement(h, f"{{{WML}}}pPr")
    pStyle = SubElement(pPr, f"{{{WML}}}pStyle")
    pStyle.set(f"{{{WML}}}val", f"Heading{level}")
    # Spacing
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
        # Indent
        ind = SubElement(pPr, f"{{{WML}}}ind")
        ind.set(f"{{{WML}}}left", "360")
    run = SubElement(para, f"{{{WML}}}r")
    t = SubElement(run, f"{{{WML}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return para

def convert_markdown(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 章节标题归一化：### 七、配置说明 → ## 七、配置说明（与一~六章同级，避免层级错乱）
    content = re.sub(r'^(#{2,4})\s+([一二三四五六七八九十]+、[^\n]*)', r'## \2', content, flags=re.M)
    # 子节标题提升：#### 7.1 环境配置 → ### 7.1（两位数字编号进目录三级；#### 6.1.1 三位编号保持四级）
    content = re.sub(r'^####\s+(\d+\.\d+)(?!\.)\s+', r'### \1 ', content, flags=re.M)

    # Extract software name from first line (e.g., "# 智汇记账软件使用说明书")
    software_name = ""
    for line in content.split("\n"):
        if line.startswith("# "):
            # Remove "使用说明书" or similar suffixes
            name = line[2:].strip()
            for suffix in ["使用说明书", "使用手册", "操作手册", "技术文档"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            software_name = name
            break

    b = body()
    in_code = False
    fence_lang = ""

    for line in content.split("\n"):
        # Code block toggle
        if line.startswith("```"):
            if not in_code:
                fence_lang = line[3:].strip().lower()
            in_code = not in_code
            continue

        if in_code:
            # 代码块未闭合防御：代码块内出现标题样式行（非注释型语言）→ 视为代码块提前结束
            if (re.match(r'^#{1,6}\s+\S', line) and len(line.strip()) <= 30
                    and fence_lang not in ('yaml', 'yml', 'python', 'py', 'bash', 'sh', 'shell', 'powershell')):
                in_code = False
                fence_lang = ""
                # 继续走标题解析（不 continue）
            else:
                if line.strip():
                    add_text_para(b, line, is_code=True)
                else:
                    add_text_para(b, "", is_code=False)
                continue

        if not line.strip():
            continue

        # Table rows - skip or convert to simple text
        if line.startswith("|") and "|" in line[1:]:
            if re.match(r'^\|[\s\-:|]+\|$', line):
                continue  # separator row
            cells = [c.strip() for c in line.strip("|").split("|")]
            para = SubElement(b, f"{{{WML}}}p")
            run = SubElement(para, f"{{{WML}}}r")
            t = SubElement(run, f"{{{WML}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = "  |  ".join(cells)
            continue

        # Headings
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

        # Unordered list
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

        # Ordered list
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

        # Normal paragraph
        add_text_para(b, line)

    # Create document with body
    doc = wml_elem("document")
    doc.append(b)
    
    # Add header reference to document
    RML = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    sectPr = SubElement(b, f"{{{WML}}}sectPr")
    
    # Add page margins
    pgMar = SubElement(sectPr, f"{{{WML}}}pgMar")
    pgMar.set(f"{{{WML}}}top", "1440")
    pgMar.set(f"{{{WML}}}right", "1800")
    pgMar.set(f"{{{WML}}}bottom", "1440")
    pgMar.set(f"{{{WML}}}left", "1800")
    pgMar.set(f"{{{WML}}}header", "851")
    pgMar.set(f"{{{WML}}}footer", "992")
    pgMar.set(f"{{{WML}}}gutter", "0")
    
    # Add page size
    pgSz = SubElement(sectPr, f"{{{WML}}}pgSz")
    pgSz.set(f"{{{WML}}}w", "11906")
    pgSz.set(f"{{{WML}}}h", "16838")
    
    # Add header reference
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


def convert_text(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    b = body()
    for line in content.split("\n"):
        para = SubElement(b, f"{{{WML}}}p")
        pPr = SubElement(para, f"{{{WML}}}pPr")
        spacing = SubElement(pPr, f"{{{WML}}}spacing")
        spacing.set(f"{{{WML}}}line", "240")
        spacing.set(f"{{{WML}}}lineRule", "auto")
        spacing.set(f"{{{WML}}}before", "0")
        spacing.set(f"{{{WML}}}after", "0")
        run = SubElement(para, f"{{{WML}}}r")
        rpr = SubElement(run, f"{{{WML}}}rPr")
        rFonts = SubElement(rpr, f"{{{WML}}}rFonts")
        rFonts.set(f"{{{WML}}}eastAsia", "SimSun")
        rFonts.set(f"{{{WML}}}ascii", "Courier New")
        rFonts.set(f"{{{WML}}}hAnsi", "Courier New")
        sz = SubElement(rpr, f"{{{WML}}}sz")
        sz.set(f"{{{WML}}}val", "16")
        t = SubElement(run, f"{{{WML}}}t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = line

    # Create document with body
    doc = wml_elem("document")
    doc.append(b)
    
    doc_xml = (
        XML_DECL + '\n' +
        tostring(doc, encoding="unicode")
        .replace("<ns0:document", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"')
        .replace("ns0:", "w:")
    )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", make_content_types())
        zf.writestr("_rels/.rels", make_rels())
        zf.writestr("word/document.xml", doc_xml)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/_rels/document.xml.rels", make_doc_rels())
    print(f"[OK] {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert files to DOCX")
    parser.add_argument("input", help="Input file path (.md or .txt)")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(args.input)[1].lower()
    output = args.output or os.path.splitext(args.input)[0] + ".docx"

    if ext == ".md":
        convert_markdown(args.input, output)
    elif ext == ".txt":
        convert_text(args.input, output)
    else:
        print(f"Error: unsupported type {ext}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()