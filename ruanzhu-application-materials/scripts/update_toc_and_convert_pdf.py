#!/usr/bin/env python3
"""Update TOC in DOCX and convert to PDF.

Supports two modes:
1. Word COM automation (requires Microsoft Word)
2. LibreOffice command line (requires LibreOffice installed)
"""

import argparse
import os
import shutil
import subprocess
import sys
import time


def update_toc_with_word(input_docx, output_pdf):
    """Update TOC using Word COM automation and convert to PDF."""
    try:
        import comtypes.client
    except ImportError:
        print("Error: comtypes not installed. Run: pip install comtypes", file=sys.stderr)
        return False

    abs_input = os.path.abspath(input_docx)
    abs_output = os.path.abspath(output_pdf)

    word = None
    doc = None

    try:
        word = comtypes.client.CreateObject("Word.Application")
        word.Visible = False

        doc = word.Documents.Open(abs_input)

        for toc in doc.TablesOfContents:
            toc.Update()

        for tof in doc.TablesOfFigures:
            tof.Update()

        time.sleep(1)

        doc.SaveAs(abs_output, FileFormat=17)

        print(f"[OK] PDF generated: {abs_output}")
        return True

    except Exception as e:
        print(f"Word COM error: {e}", file=sys.stderr)
        return False
    finally:
        if doc:
            doc.Close(False)
        if word:
            word.Quit()


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


def update_toc_with_libreoffice(input_docx, output_pdf):
    """Update TOC and convert to PDF using LibreOffice."""
    lo_path = find_libreoffice()

    if not lo_path:
        print("Error: LibreOffice not found. Install LibreOffice or use --mode word", file=sys.stderr)
        return False

    abs_input = os.path.abspath(input_docx)
    abs_output = os.path.abspath(output_pdf)
    output_dir = os.path.dirname(abs_output)

    try:
        print("[INFO] Converting DOCX to PDF using LibreOffice...")

        clean_env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "PYTHONSTARTUP", "PYTHONUSERBASE")}
        result = subprocess.run(
            [lo_path, "--headless", "--convert-to", "pdf", "--outdir", output_dir, abs_input],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=clean_env
        )

        if result.returncode != 0:
            print(f"LibreOffice error: {result.stderr}", file=sys.stderr)
            return False

        generated_pdf = os.path.join(output_dir, os.path.splitext(os.path.basename(input_docx))[0] + ".pdf")

        if os.path.exists(generated_pdf) and generated_pdf != abs_output:
            if os.path.exists(abs_output):
                os.remove(abs_output)
            os.rename(generated_pdf, abs_output)

        if os.path.exists(abs_output):
            print(f"[OK] PDF generated: {abs_output}")
            return True
        else:
            print("Error: PDF file not generated", file=sys.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("Error: LibreOffice conversion timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"LibreOffice error: {e}", file=sys.stderr)
        return False


def update_toc_and_convert_pdf(input_docx, output_pdf=None, mode="auto"):
    """Update TOC in DOCX file and convert to PDF."""
    if not os.path.exists(input_docx):
        print(f"Error: {input_docx} not found", file=sys.stderr)
        sys.exit(1)

    if output_pdf is None:
        output_pdf = os.path.splitext(input_docx)[0] + ".pdf"

    if mode == "auto":
        try:
            import comtypes.client
            mode = "word"
        except ImportError:
            mode = "libreoffice"

    print(f"[INFO] Using mode: {mode}")

    if mode == "word":
        success = update_toc_with_word(input_docx, output_pdf)
        if not success:
            print("[INFO] Word mode failed, trying LibreOffice...")
            success = update_toc_with_libreoffice(input_docx, output_pdf)
    elif mode == "libreoffice":
        success = update_toc_with_libreoffice(input_docx, output_pdf)
        if not success:
            print("[INFO] LibreOffice mode failed, trying Word COM...")
            success = update_toc_with_word(input_docx, output_pdf)
    else:
        print(f"Error: Unknown mode '{mode}'. Use 'auto', 'word', or 'libreoffice'", file=sys.stderr)
        sys.exit(1)

    if not success:
        print("Error: Failed to generate PDF with all available methods", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Update TOC in DOCX and convert to PDF")
    parser.add_argument("input", help="Input .docx file path")
    parser.add_argument("--output", "-o", help="Output .pdf file path (default: same name as input)")
    parser.add_argument("--mode", "-m", choices=["auto", "word", "libreoffice"],
                        default="auto", help="Conversion mode (default: auto)")
    args = parser.parse_args()

    if not args.input.lower().endswith(".docx"):
        print("Error: input must be .docx file", file=sys.stderr)
        sys.exit(1)

    update_toc_and_convert_pdf(args.input, args.output, args.mode)


if __name__ == "__main__":
    main()
