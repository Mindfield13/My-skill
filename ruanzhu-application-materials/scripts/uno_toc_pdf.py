#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 LibreOffice UNO 更新 Word 目录（TOC）后导出 PDF —— 跨平台版。

用法:
    python uno_toc_pdf.py <input.docx> <output.pdf> [选项]

选项:
    --force-kill    运行前强制结束残留 soffice 进程（会丢失未保存的 Office 文档！）
    --port N        指定桥接端口，默认自动挑一个空闲端口
    --timeout N     等待 soffice 就绪的秒数，默认 60
    --no-toc        只转换 PDF，不更新目录

为什么必须走 UNO：
    LibreOffice 的 `soffice --convert-to pdf` **不会更新目录域**。用那条路生成的
    PDF，目录页会留「请右键点击此处，选择"更新域"以生成目录」这行占位，整块目录
    空着，而且**退出码为 0、不报任何错**，极易漏检。UNO 方式连上 soffice 后遍历
    getDocumentIndexes() 逐个 update() 再导出，目录页码才准确。

关于 python 解释器：
    UNO 依赖 LibreOffice 自带的 `uno` 模块。本脚本若发现当前解释器没有 uno，
    会自动用探测到的 LibreOffice 自带 python 重新执行自己（os.execve），
    因此三种平台都可以直接 `python uno_toc_pdf.py ...` 起手。

    各平台自带 python 的位置：
      Windows  <LO>/program/python.exe
      macOS    LibreOffice.app/Contents/Resources/python
      Linux    通常需系统 python3 装 python3-uno；否则回退 <LO>/program/python

关于用户配置目录：
    脚本为每次运行创建**独立的 UserInstallation 临时 profile**，
    不会挂到用户正在使用的 LibreOffice 实例上，也不会与并发的转换互相争抢。
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REEXEC_FLAG = "RUANZHU_UNO_REEXEC"
DEFAULT_TIMEOUT = 60


# --------------------------------------------------------------------------- #
# LibreOffice 定位
# --------------------------------------------------------------------------- #
def find_soffice() -> str | None:
    """跨平台定位 soffice 可执行文件。"""
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


def candidate_pythons(soffice: str) -> list[str]:
    """列出可能带 uno 模块的 python 解释器候选。"""
    program = Path(soffice).parent
    cands: list[Path] = []

    if sys.platform == "win32":
        cands += [program / "python.exe", program / "python.bat"]
    elif sys.platform == "darwin":
        contents = program.parent                     # .../LibreOffice.app/Contents
        cands += [
            contents / "Resources" / "python",
            contents / "MacOS" / "python",
            contents / "Frameworks" / "Python.framework" / "Versions" / "Current" / "bin" / "python3",
        ]
    else:
        cands += [
            program / "python",
            Path("/usr/lib/libreoffice/program/python"),
            Path("/usr/bin/python3"),
            Path("/usr/local/bin/python3"),
        ]

    # 当前解释器也试一次，覆盖"系统 python 已装 python3-uno"的情况
    cands.append(Path(sys.executable))

    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        s = str(c)
        if c.exists() and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def python_has_uno(python_exe: str) -> bool:
    try:
        r = subprocess.run(
            [python_exe, "-c", "import uno"],
            capture_output=True, timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def ensure_uno() -> bool:
    """保证当前进程能 import uno；否则换 LibreOffice 自带的 python 重新执行本脚本。

    返回 True 表示当前解释器可用；找到替代解释器时本函数**不会返回**（直接退出）；
    返回 False 表示彻底找不到带 uno 的解释器。
    """
    try:
        import uno  # noqa: F401
        return True
    except ImportError:
        pass

    if os.environ.get(REEXEC_FLAG):
        print("Error: 已切换到 LibreOffice 自带 python，但仍无法 import uno。", file=sys.stderr)
        return False

    soffice = find_soffice()
    if not soffice:
        print("Error: 找不到 LibreOffice。请安装 LibreOffice 或设置 SOFFICE 环境变量。",
              file=sys.stderr)
        return False

    for cand in candidate_pythons(soffice):
        if os.path.abspath(cand) == os.path.abspath(sys.executable):
            continue
        if python_has_uno(cand):
            print(f"[INFO] 当前解释器无 uno 模块，改用 {cand} 重新执行", flush=True)
            env = dict(os.environ, **{REEXEC_FLAG: "1"})
            _reexec_child([cand, os.path.abspath(__file__)] + sys.argv[1:], env)

    print("Error: 未找到带 uno 模块的 python 解释器。", file=sys.stderr)
    print("       Windows/macOS: 应随 LibreOffice 一并安装，请检查安装完整性。", file=sys.stderr)
    print("       Linux: 请安装 python3-uno（Debian/Ubuntu: apt install python3-uno）。",
          file=sys.stderr)
    return False


def _reexec_child(argv: list[str], env: dict) -> None:
    """用带 uno 的解释器重新执行本脚本，透传退出码。

    不用 os.execve：它在 Windows 上对管道型 stdio（例如 `python x.py | tail`）
    不可靠，会丢掉输出（缓冲区随进程映像被替换而消失）。
    spawn 子进程 + 透传退出码在三平台行为一致，且输出能实时流式透出。
    """
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        code = subprocess.run(argv, env=env).returncode
    except Exception as exc:                              # noqa: BLE001
        print(f"Error: 重新执行失败：{exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# 进程与端口
# --------------------------------------------------------------------------- #
def kill_lingering_soffice() -> None:
    """强制结束残留 soffice 进程。**会丢失未保存的 Office 文档**，仅在 --force-kill 时调用。"""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/IM", "soffice.bin", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "soffice.exe", "/T"], capture_output=True)
    else:
        if shutil.which("pkill"):
            subprocess.run(["pkill", "-f", "soffice"], capture_output=True)
        elif shutil.which("killall"):
            subprocess.run(["killall", "soffice"], capture_output=True)
    time.sleep(2)


def free_port() -> int:
    """向系统要一个空闲端口，避免固定端口被占用或与并发实例撞车。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_profile_dir() -> str:
    """为本次运行创建独立的 UserInstallation 目录（避免挂到用户正在用的 LO 实例）。"""
    base = os.getcwd() if os.access(os.getcwd(), os.W_OK) else tempfile.gettempdir()
    path = os.path.join(base, f".lo_profile_{os.getpid()}_{int(time.time())}")
    os.makedirs(path, exist_ok=True)
    return path


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run(args) -> int:
    docx_path = os.path.abspath(args.docx)
    pdf_path = os.path.abspath(args.pdf)

    if not os.path.exists(docx_path):
        print(f"Error: 找不到输入文件 {docx_path}", file=sys.stderr)
        return 1

    if not ensure_uno():
        return 1

    import uno
    from com.sun.star.beans import PropertyValue

    soffice = find_soffice()
    if not soffice:
        print("Error: 找不到 LibreOffice。", file=sys.stderr)
        return 1

    if args.force_kill:
        print("[WARN] 正在强制结束残留 soffice 进程（未保存的 Office 文档会丢失）")
        kill_lingering_soffice()

    port = args.port or free_port()
    profile = make_profile_dir()
    profile_url = uno.systemPathToFileUrl(os.path.abspath(profile))

    cmd = [
        soffice, "--headless", "--invisible", "--norestore", "--nologo",
        f"-env:UserInstallation={profile_url}",
        f"--accept=socket,host=127.0.0.1,port={port};urp;",
    ]
    print(f"[INFO] 启动 soffice（端口 {port}，独立 profile）")
    popen_kwargs = {} if sys.platform == "win32" else {"start_new_session": True}
    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)

    ctx = None
    deadline = time.time() + args.timeout
    resolved = f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx)

    while time.time() < deadline:
        time.sleep(1)
        try:
            ctx = resolver.resolve(resolved)
            break
        except Exception:
            if proc.poll() is not None:
                print("Error: soffice 启动后立即退出。", file=sys.stderr)
                break
            continue

    if ctx is None:
        print(f"Error: {args.timeout}s 内无法连接 LibreOffice。", file=sys.stderr)
        _shutdown(proc, None)
        shutil.rmtree(profile, ignore_errors=True)
        return 1

    desktop = None
    try:
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

        hidden = PropertyValue()
        hidden.Name = "Hidden"
        hidden.Value = True

        doc = desktop.loadComponentFromURL(
            uno.systemPathToFileUrl(docx_path), "_blank", 0, (hidden,))
        if doc is None:
            print("Error: 无法打开文档。", file=sys.stderr)
            return 1

        if not args.no_toc:
            try:
                indexes = doc.getDocumentIndexes()
                count = indexes.getCount()
                for i in range(count):
                    indexes.getByIndex(i).update()
                print(f"Updated {count} TOC index(es)")
            except Exception as exc:                      # noqa: BLE001
                print(f"TOC update warning: {exc}", file=sys.stderr)

        pdf_props = PropertyValue()
        pdf_props.Name = "FilterName"
        pdf_props.Value = "writer_pdf_Export"
        doc.storeToURL(uno.systemPathToFileUrl(pdf_path), (pdf_props,))
        doc.close(False)
        print(f"PDF generated: {pdf_path}")
        return 0
    finally:
        _shutdown(proc, desktop)
        shutil.rmtree(profile, ignore_errors=True)


def _shutdown(proc, desktop) -> None:
    if desktop is not None:
        try:
            desktop.terminate()
        except Exception:
            pass
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="用 LibreOffice UNO 更新目录并导出 PDF（跨平台）")
    parser.add_argument("docx", help="输入 .docx")
    parser.add_argument("pdf", help="输出 .pdf")
    parser.add_argument("--force-kill", action="store_true",
                        help="运行前强制结束残留 soffice（会丢失未保存的 Office 文档）")
    parser.add_argument("--port", type=int, default=0, help="桥接端口，默认自动选择")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"等待 soffice 就绪的秒数，默认 {DEFAULT_TIMEOUT}")
    parser.add_argument("--no-toc", action="store_true", help="只转换 PDF，不更新目录")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
