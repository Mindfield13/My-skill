#!/usr/bin/env python3
"""source-code.docx → PDF（LibreOffice）+ 页数判定 + 前/后各30页裁剪。

硬性规则（不可跳过）：
  * 转换后 PDF 页数 N <= 60 页  → 全部保留，source-code.pdf 即完整版
  * 转换后 PDF 页数 N >  60 页  → 只保留前 30 页 + 后 30 页，共 60 页；
    完整版另存为 source-code-full.pdf

用法：
    python source_to_pdf.py MD/source-code.docx
    python source_to_pdf.py MD/source-code.docx --outdir MD
    python source_to_pdf.py MD/source-code.docx --threshold 60 --head 30 --tail 30

依赖：
    - LibreOffice（soffice），默认检测常见安装路径，也可用环境变量 SOFFICE 指定
    - PDF 统计/裁剪优先 PyMuPDF（pymupdf/fitz），其次 pypdf / PyPDF2 / pikepdf；
      全部缺失时自动尝试 pip 安装 pypdf
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

DEFAULT_THRESHOLD = 60
DEFAULT_KEEP = 30


def find_soffice():
    candidates = []
    env = os.environ.get("SOFFICE") or os.environ.get("LIBREOFFICE")
    if env:
        candidates.append(env)
    which = shutil.which("soffice")
    if which:
        candidates.append(which)
    if os.name == "nt":
        candidates += [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    else:
        candidates += [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/usr/bin/soffice",
            "/usr/lib/libreoffice/program/soffice",
            "/opt/libreoffice/program/soffice",
        ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def make_workdir(prefix):
    """在可写位置创建临时目录：优先当前工作目录（沙箱环境系统临时目录常不可写）。

    注意：不使用 tempfile.mkdtemp —— 部分沙箱环境对 mkdtemp 创建的目录拒绝写入，
    改用 os.makedirs 创建并写入探针文件验证可写性。
    """
    for base in (os.getcwd(), tempfile.gettempdir()):
        d = os.path.join(base, "%s%d_%d" % (prefix, os.getpid(), int(time.time() * 1000) % 100000))
        try:
            os.makedirs(d, exist_ok=False)
            probe = os.path.join(d, "probe")
            with open(probe, "wb") as f:
                f.write(b"x")
            os.remove(probe)
            return d
        except Exception:
            continue
    return None


def convert_docx_to_pdf(docx_path, out_dir, soffice):
    """调用 LibreOffice 将 docx 转为 PDF，返回生成的 PDF 路径。"""
    tmp_profile = make_workdir("lo_profile_")
    if not tmp_profile:
        sys.exit("错误：无法创建临时目录（当前目录与系统临时目录均不可写）")
    try:
        profile_url = "file:///" + quote(tmp_profile.replace("\\", "/"), safe="/:")
        cmd = [soffice, "--headless",
               "-env:UserInstallation=" + profile_url,
               "--convert-to", "pdf",
               "--outdir", out_dir,
               docx_path]
        print("[INFO] 执行: %s" % " ".join(cmd))
        # 输出重定向到文件而非管道：沙箱环境禁止子进程创建命名管道
        stdout_log = os.path.join(tmp_profile, "soffice_stdout.log")
        stderr_log = os.path.join(tmp_profile, "soffice_stderr.log")
        with open(stdout_log, "wb") as so, open(stderr_log, "wb") as se:
            try:
                proc = subprocess.run(cmd, stdout=so, stderr=se, timeout=300)
            except subprocess.TimeoutExpired:
                sys.exit("错误：LibreOffice 转换超时（300 秒）")

        expected = os.path.join(
            out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
        deadline = time.time() + 60
        while (not os.path.exists(expected)
               or os.path.getsize(expected) == 0) and time.time() < deadline:
            time.sleep(1)
        if not os.path.exists(expected) or os.path.getsize(expected) == 0:
            def tail(path):
                try:
                    with open(path, "rb") as f:
                        return f.read()[-2000:].decode("utf-8", "replace")
                except Exception:
                    return ""
            sys.exit("错误：LibreOffice 转换失败（退出码 %s），未生成 PDF。\n"
                     "stdout: %s\nstderr: %s"
                     % (getattr(proc, "returncode", "?"),
                        tail(stdout_log), tail(stderr_log)))
        return expected
    finally:
        try:
            shutil.rmtree(tmp_profile, ignore_errors=True)
        except Exception:
            pass


def count_pages_regex(path):
    """零依赖的页数兜底：统计 PDF 中叶子页面对象 /Type /Page（排除 /Pages）。

    同时解析页面树 /Count 值，取两者较小者作为页数：
    - PyMuPDF 以 garbage=2 保存的裁剪结果可能残留未引用的 /Type /Page 对象，
      而页面树根 /Count 是权威值（如 /Count=60 但残留 91 个页面对象）；
    - 普通 PDF（LibreOffice、qpdf、pypdf 输出）两者一致。
    """
    with open(path, "rb") as f:
        data = f.read()
    leaf = len(re.findall(rb"/Type\s*/Page(?![s\w])", data))
    counts = [int(c) for c in re.findall(rb"/Count\s+(\d+)", data)]
    root_count = max(counts) if counts else 0
    if leaf and root_count:
        return min(leaf, root_count)
    return leaf or root_count


def count_pdf_pages(path):
    """返回 (页数, 统计方式)；无法统计时返回 (None, None)。"""
    try:
        import pymupdf
        with pymupdf.open(path) as doc:
            return len(doc), "PyMuPDF"
    except Exception:
        pass
    try:
        import fitz
        with fitz.open(path) as doc:
            return len(doc), "PyMuPDF(fitz)"
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages), "pypdf"
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader
        return len(PdfReader(path).pages), "PyPDF2"
    except Exception:
        pass
    try:
        import pikepdf
        with pikepdf.open(path) as pdf:
            return len(pdf.pages), "pikepdf"
    except Exception:
        pass
    n = count_pages_regex(path)
    if n:
        return n, "内置解析"
    return None, None


def ensure_pypdf():
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        pass
    print("[INFO] 未检测到 PDF 处理库（pymupdf/pypdf），尝试自动安装 pypdf ...")
    attempts = [
        [sys.executable, "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "pypdf"],
        ["python", "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "pypdf"],
        ["python3", "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "pypdf"],
        ["py", "-3", "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "pypdf"],
    ]
    tmp = make_workdir("pip_log_")
    if not tmp:
        return False
    try:
        for cmd in attempts:
            try:
                # 输出重定向到文件而非管道（沙箱环境禁止创建命名管道）
                with open(os.path.join(tmp, "pip_stdout.log"), "wb") as so, \
                        open(os.path.join(tmp, "pip_stderr.log"), "wb") as se:
                    r = subprocess.run(cmd, stdout=so, stderr=se, timeout=300)
                if r.returncode == 0:
                    try:
                        import pypdf  # noqa: F401
                        return True
                    except ImportError:
                        continue
            except Exception:
                continue
        return False
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


def trim_pdf(src_path, keep_pages, out_path):
    """按 1 起始页号列表裁剪 PDF，返回使用的工具名；失败返回 None。"""
    pages = [p - 1 for p in keep_pages]
    # PyMuPDF
    try:
        import pymupdf
        doc = pymupdf.open(src_path)
        doc.select(pages)
        # 注意：garbage=2 足够清理未引用对象；garbage=4 会重建整份 PDF，大文件极慢
        doc.save(out_path, garbage=2)
        doc.close()
        return "PyMuPDF"
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(src_path)
        doc.select(pages)
        doc.save(out_path, garbage=2)
        doc.close()
        return "PyMuPDF(fitz)"
    except Exception:
        pass
    # pypdf
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(src_path)
        writer = PdfWriter()
        for p in pages:
            writer.add_page(reader.pages[p])
        with open(out_path, "wb") as f:
            writer.write(f)
        return "pypdf"
    except Exception:
        pass
    # PyPDF2
    try:
        from PyPDF2 import PdfReader, PdfWriter
        reader = PdfReader(src_path)
        writer = PdfWriter()
        for p in pages:
            writer.add_page(reader.pages[p])
        with open(out_path, "wb") as f:
            writer.write(f)
        return "PyPDF2"
    except Exception:
        pass
    # pikepdf
    try:
        import pikepdf
        src = pikepdf.open(src_path)
        dst = pikepdf.Pdf.new()
        for p in pages:
            dst.pages.append(src.pages[p])
        dst.save(out_path)
        src.close()
        dst.close()
        return "pikepdf"
    except Exception:
        pass
    # qpdf 命令行
    qpdf = shutil.which("qpdf")
    if qpdf:
        spec = ",".join(str(p) for p in keep_pages)
        tmp = make_workdir("qpdf_log_")
        if tmp:
            try:
                with open(os.path.join(tmp, "qpdf_out.log"), "wb") as so, \
                        open(os.path.join(tmp, "qpdf_err.log"), "wb") as se:
                    r = subprocess.run([qpdf, "--pages", src_path, spec, "--", out_path],
                                       stdout=so, stderr=se, timeout=120)
                if r.returncode == 0 and os.path.exists(out_path) \
                        and os.path.getsize(out_path) > 0:
                    return "qpdf"
            except Exception:
                pass
            finally:
                try:
                    shutil.rmtree(tmp, ignore_errors=True)
                except Exception:
                    pass
    # 自动安装 pypdf 后重试一次
    if ensure_pypdf():
        return trim_pdf(src_path, keep_pages, out_path)
    return None


def main():
    ap = argparse.ArgumentParser(
        description="source-code.docx → PDF（LibreOffice），并按页数规则裁剪")
    ap.add_argument("input", help="输入 .docx 路径（如 MD/source-code.docx）")
    ap.add_argument("--outdir", "-o", default=None,
                    help="输出目录（默认与输入文件同目录）")
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                    help="页数阈值，超过则裁剪（默认 %d）" % DEFAULT_THRESHOLD)
    ap.add_argument("--head", type=int, default=DEFAULT_KEEP,
                    help="超过阈值时保留的前部页数（默认 %d）" % DEFAULT_KEEP)
    ap.add_argument("--tail", type=int, default=DEFAULT_KEEP,
                    help="超过阈值时保留的后部页数（默认 %d）" % DEFAULT_KEEP)
    ap.add_argument("--no-keep-full", action="store_true",
                    help="超过阈值时不保留完整版 PDF（默认保留为 <名>-full.pdf）")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit("错误：输入文件不存在 %s" % args.input)
    if os.path.splitext(args.input)[1].lower() != ".docx":
        sys.exit("错误：输入必须是 .docx 文件")

    base = os.path.splitext(os.path.basename(args.input))[0]
    outdir = args.outdir or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(outdir, exist_ok=True)
    final_pdf = os.path.join(outdir, base + ".pdf")

    soffice = find_soffice()
    if not soffice:
        sys.exit("错误：未找到 LibreOffice（soffice）。请安装 LibreOffice，"
                 "或设置环境变量 SOFFICE 指向 soffice 可执行文件。")

    print("[INFO] 使用 LibreOffice: %s" % soffice)
    print("[INFO] 转换 %s -> PDF ..." % args.input)
    full_pdf = convert_docx_to_pdf(args.input, outdir, soffice)

    n, method = count_pdf_pages(full_pdf)
    if not n:
        sys.exit("错误：无法统计 PDF 页数（未安装 PyMuPDF/pypdf 且内置解析失败）")
    print("[INFO] 源程序 PDF 共 %d 页（统计方式: %s）" % (n, method))
    print("[INFO] 页数阈值: %d（超过则保留前 %d 页 + 后 %d 页）"
          % (args.threshold, args.head, args.tail))

    if n <= args.threshold:
        if os.path.abspath(full_pdf) != os.path.abspath(final_pdf):
            if os.path.exists(final_pdf):
                os.remove(final_pdf)
            os.replace(full_pdf, final_pdf)
        m, _ = count_pdf_pages(final_pdf)
        print("[OK] 页数 %d <= %d，全部保留" % (n, args.threshold))
        print("[OK] 最终文件: %s（%d 页）" % (final_pdf, m))
        return

    keep = list(range(1, args.head + 1)) + list(range(n - args.tail + 1, n + 1))
    keep = [p for p in keep if 1 <= p <= n]  # 防止自定义参数越界
    print("[INFO] 页数 %d > %d，保留前 %d 页 + 后 %d 页，共 %d 页"
          % (n, args.threshold, args.head, args.tail, len(keep)))

    if args.no_keep_full:
        trim_src = full_pdf
    else:
        full_keep = os.path.join(outdir, base + "-full.pdf")
        if os.path.exists(full_keep):
            os.remove(full_keep)
        os.replace(full_pdf, full_keep)
        trim_src = full_keep

    tool = trim_pdf(trim_src, keep, final_pdf)
    if not tool:
        sys.exit("错误：PDF 裁剪失败（无可用 PDF 库且自动安装 pypdf 失败）")

    m, _ = count_pdf_pages(final_pdf)
    expected = len(keep)
    print("[OK] 裁剪完成（工具: %s）" % tool)
    print("[OK] 原始 %d 页 -> 提交 %d 页（前 %d + 后 %d）"
          % (n, m, args.head, args.tail))
    if m != expected:
        print("[WARN] 复核页数 %d 与预期 %d 不一致，请人工检查 %s"
              % (m, expected, final_pdf))
    else:
        print("[OK] 复核通过：%s 共 %d 页" % (final_pdf, m))
    if not args.no_keep_full:
        print("[INFO] 完整版保留在: %s（%d 页）" % (full_keep, n))
    print("[DONE] 交付文件: %s" % final_pdf)


if __name__ == "__main__":
    main()
