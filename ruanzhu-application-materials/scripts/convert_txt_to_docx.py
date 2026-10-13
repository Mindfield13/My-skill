#!/usr/bin/env python3
"""Convert plain text (.txt) to .docx with header (software name + page number)."""

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

def wml_elem(tag):
    return Element(f"{{{WML}}}{tag}")

def body():
    return wml_elem("body")

def estimate_pages(lines, lines_per_page=58):
    return (len(lines) + lines_per_page - 1) // lines_per_page

def find_module_boundary(lines, max_lines):
    if max_lines >= len(lines):
        return len(lines)
    
    for i in range(max_lines, max(0, max_lines - 100), -1):
        line = lines[i].strip()
        if not line:
            continue
        if line.startswith('def ') or line.startswith('class '):
            return i
        if line.startswith('import ') or line.startswith('from '):
            continue
        if line.startswith('#') or line.startswith('//'):
            continue
        if line.startswith('@'):
            continue
        if line == '' and i > 0 and lines[i-1].strip() == '':
            continue
    
    for i in range(max_lines, max(0, max_lines - 50), -1):
        line = lines[i].strip()
        if not line:
            return i + 1
    
    return max_lines

def extract_software_name_from_md(md_path):
    if not os.path.exists(md_path):
        return None
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        if line.startswith("# "):
            name = line[2:].strip()
            for suffix in ["使用说明书", "使用手册", "操作手册", "技术文档"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            return name
    return None

def find_software_name(input_path):
    input_dir = os.path.dirname(os.path.abspath(input_path))
    
    md_path = os.path.join(input_dir, "Technical-documentation.md")
    name = extract_software_name_from_md(md_path)
    if name:
        return name
    
    for file in os.listdir(input_dir):
        if file.endswith(".md"):
            md_path = os.path.join(input_dir, file)
            name = extract_software_name_from_md(md_path)
            if name:
                return name
    
    return "软件"

def convert_text(input_path, output_path, software_name=None, max_pages=0):
    if not software_name:
        software_name = find_software_name(input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    
    if max_pages > 0:
        total_pages = estimate_pages(lines)
        if total_pages > max_pages:
            lines_per_page = 58
            max_lines = max_pages * lines_per_page
            cut_point = find_module_boundary(lines, max_lines)
            lines = lines[:cut_point]
            print(f"[INFO] 内容超过{max_pages}页，已截断至{cut_point}行（约{max_pages}页）")

    b = body()
    for line in lines:
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
    parser = argparse.ArgumentParser(description="Convert text file to DOCX with header")
    parser.add_argument("input", help="Input .txt file path")
    parser.add_argument("--output", "-o", help="Output .docx file path")
    parser.add_argument("--name", "-n", help="Software name for header")
    parser.add_argument("--max-pages", "-m", type=int, default=0, help="Maximum pages (0 = no limit, default: 0)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(args.input)[1].lower()
    if ext != ".txt":
        print(f"Error: input must be .txt file, got {ext}", file=sys.stderr)
        sys.exit(1)

    output = args.output or os.path.splitext(args.input)[0] + ".docx"
    convert_text(args.input, output, args.name, args.max_pages)

if __name__ == "__main__":
    main()