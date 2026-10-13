#!/usr/bin/env python3
"""Convert source code DOCX to PDF, keeping only first 60 pages."""

import argparse
import os
import shutil
import subprocess
import sys
import time


def find_libreoffice():
    """跨平台定位 LibreOffice 可执行文件。

    顺序：SOFFICE / LIBREOFFICE 环境变量 → 各平台常见安装路径 → PATH 查找。
    用 shutil.which 而非 which/where 子进程：三平台行为一致，不依赖 shell，
    也不会在中文系统上因 GBK 输出抛 UnicodeDecodeError。
    """
    candidates = []
    env = os.environ.get("SOFFICE") or os.environ.get("LIBREOFFICE")
    if env:
        candidates.append(env)

    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                candidates.append(os.path.join(base, "LibreOffice", "program", "soffice.exe"))
    elif sys.platform == "darwin":
        candidates += [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            os.path.expanduser("~/Applications/LibreOffice.app/Contents/MacOS/soffice"),
        ]
    else:
        candidates += [
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/usr/bin/libreoffice",
            "/usr/local/bin/libreoffice",
            "/snap/bin/libreoffice",
            "/usr/lib/libreoffice/program/soffice",
            "/opt/libreoffice/program/soffice",
            "/var/lib/flatpak/exports/bin/org.libreoffice.LibreOffice",
        ]

    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def truncate_docx_to_pages(input_docx, output_docx, max_pages=60):
    """Truncate DOCX to specified number of pages using python-docx."""
    try:
        from docx import Document
        from docx.shared import Pt
        import copy
    except ImportError:
        print("Error: python-docx not installed. Run: pip install python-docx", file=sys.stderr)
        return False

    try:
        doc = Document(input_docx)

        lines_per_page = 58
        max_lines = max_pages * lines_per_page

        body = doc.element.body
        all_elements = list(body)

        sect_pr = None
        if all_elements and all_elements[-1].tag.endswith('}sectPr'):
            sect_pr = all_elements[-1]
            all_elements = all_elements[:-1]

        total_elements = len(all_elements)

        if total_elements <= max_lines:
            print(f"[INFO] Document has {total_elements} elements, no truncation needed")
            return True

        keep_elements = all_elements[:max_lines]

        for elem in all_elements:
            body.remove(elem)

        for elem in keep_elements:
            body.append(elem)

        if sect_pr is not None:
            body.append(sect_pr)

        doc.save(output_docx)
        print(f"[OK] Truncated to {max_pages} pages: {output_docx}")
        return True

    except Exception as e:
        print(f"Error truncating DOCX: {e}", file=sys.stderr)
        return False


def convert_docx_to_pdf(input_docx, output_pdf, max_pages=60):
    """Convert DOCX to PDF with page limit."""
    if not os.path.exists(input_docx):
        print(f"Error: {input_docx} not found", file=sys.stderr)
        sys.exit(1)

    abs_input = os.path.abspath(input_docx)
    abs_output = os.path.abspath(output_pdf)

    temp_docx = None
    if max_pages > 0:
        temp_docx = os.path.splitext(abs_input)[0] + "_truncated.docx"
        if not truncate_docx_to_pages(abs_input, temp_docx, max_pages):
            print("[WARN] Failed to truncate, converting full document")
            temp_docx = None

    # 修复：truncate 可能返回 True 但未实际创建截断文件（元素数不足时不写文件）
    source_docx = temp_docx if (temp_docx and os.path.exists(temp_docx)) else abs_input

    lo_path = find_libreoffice()
    if not lo_path:
        print("Error: LibreOffice not found. Install LibreOffice from https://www.libreoffice.org/", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.dirname(abs_output)

    try:
        print(f"[INFO] Converting DOCX to PDF using LibreOffice...")

        clean_env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "PYTHONSTARTUP", "PYTHONUSERBASE")}
        result = subprocess.run(
            [lo_path, "--headless", "--convert-to", "pdf", "--outdir", output_dir, source_docx],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=clean_env
        )

        if result.returncode != 0:
            print(f"LibreOffice error: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        generated_pdf = os.path.join(output_dir, os.path.splitext(os.path.basename(source_docx))[0] + ".pdf")

        if os.path.exists(generated_pdf) and generated_pdf != abs_output:
            if os.path.exists(abs_output):
                os.remove(abs_output)
            os.rename(generated_pdf, abs_output)

        if os.path.exists(abs_output):
            print(f"[OK] PDF generated: {abs_output}")
        else:
            print("Error: PDF file not generated", file=sys.stderr)
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("Error: LibreOffice conversion timed out", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if temp_docx and os.path.exists(temp_docx):
            os.remove(temp_docx)


def main():
    parser = argparse.ArgumentParser(description="Convert source code DOCX to PDF with page limit")
    parser.add_argument("input", help="Input .docx file path")
    parser.add_argument("--output", "-o", help="Output .pdf file path (default: same name as input)")
    parser.add_argument("--max-pages", "-m", type=int, default=60,
                        help="Maximum pages to keep (default: 60, 0 = no limit)")
    args = parser.parse_args()

    if not args.input.lower().endswith(".docx"):
        print("Error: input must be .docx file", file=sys.stderr)
        sys.exit(1)

    output = args.output or os.path.splitext(args.input)[0] + ".pdf"
    convert_docx_to_pdf(args.input, output, args.max_pages)


if __name__ == "__main__":
    main()
