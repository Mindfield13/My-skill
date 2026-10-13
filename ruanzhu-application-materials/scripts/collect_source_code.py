#!/usr/bin/env python3
"""把已有项目中的源代码汇总为一个 UTF-8 文本文件（软著源程序文档）。

自动排除：
- 依赖 / 构建 / 版本控制目录：node_modules、venv、dist、build、target、.git ...
- 配置文件与锁定文件：package.json、requirements.txt、pom.xml、.env、*.lock ...
- 二进制 / 媒体 / 文档文件：图片、字体、压缩包、.md/.txt/.pdf ...

用法：
    python collect_source_code.py <项目根目录> [-o 输出文件] [--with-separators]
    python collect_source_code.py . -o MD/source-code.txt
    python collect_source_code.py . -o MD/source-code.txt --include-dir packages
"""

import argparse
import os
import sys

# 默认跳过的目录（依赖、构建产物、版本控制、IDE 等）
SKIP_DIRS = {
    # 依赖与虚拟环境
    "node_modules", "venv", ".venv", "env", ".env", "virtualenv",
    "site-packages", "vendor", "bower_components", "jspm_packages",
    "Pods", "Carthage", ".gradle", ".mvn", ".tox",
    # 构建产物
    "dist", "build", "target", "out", "bin", "obj", ".next", ".nuxt",
    ".output", ".parcel-cache", ".cache", "coverage", "htmlcov",
    ".pytest_cache", ".mypy_cache", "__pycache__", ".ruff_cache",
    # 版本控制与 IDE
    ".git", ".svn", ".hg", ".idea", ".vscode", ".vscode-server", ".vs",
    # 其他（第三方代码、CI 配置目录、系统目录）
    "__MACOSX", "third_party", "3rdparty", ".github", ".gitlab",
}

# 按文件名精确跳过的配置文件 / 锁定文件 / 环境变量 / 文档
SKIP_FILES = {
    # JS/前端配置
    "package.json", "package-lock.json", "npm-shrinkwrap.json",
    "yarn.lock", "pnpm-lock.yaml", "pnpm-workspace.yaml",
    "bun.lock", "bun.lockb", ".npmrc", ".yarnrc", ".nvmrc", ".node-version",
    "tsconfig.json", "tsconfig.node.json", "jsconfig.json",
    "vite.config.js", "vite.config.ts", "vue.config.js", "vue.config.ts",
    "webpack.config.js", "webpack.config.ts",
    "next.config.js", "next.config.mjs", "nuxt.config.js", "nuxt.config.ts",
    "babel.config.js", "babel.config.cjs", ".babelrc",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.cjs",
    ".prettierrc", ".prettierrc.js", ".prettierrc.json",
    "tailwind.config.js", "tailwind.config.ts",
    "postcss.config.js", "postcss.config.cjs", ".browserslistrc",
    "angular.json", "workspace.json", "project.json", "manifest.json",
    ".editorconfig", ".gitignore", ".gitattributes",
    # Python 配置
    "requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock",
    "pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "pytest.ini",
    ".flake8", ".python-version",
    # Java/构建配置
    "pom.xml", "build.gradle", "build.gradle.kts",
    "settings.gradle", "settings.gradle.kts", "gradle.properties",
    "gradle-wrapper.properties", "gradlew", "gradlew.bat",
    "mvnw", "mvnw.cmd",
    # 其他语言配置
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
    "composer.json", "composer.lock", "Gemfile", "Gemfile.lock",
    # 环境变量
    ".env", ".env.local", ".env.development", ".env.production", ".env.test",
    # 部署/CI
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "docker-compose.override.yml", "Makefile", "CMakeLists.txt",
    ".gitlab-ci.yml", ".travis.yml", "Jenkinsfile",
    # 文档
    "README.md", "README", "README.txt", "LICENSE", "LICENSE.txt",
    "CHANGELOG.md", "CHANGELOG",
}

# 视为源代码的扩展名（其余一律跳过）
INCLUDE_EXTS = {
    # Python
    ".py",
    # JavaScript / TypeScript
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue",
    # Web
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".styl",
    # Java / JVM
    ".java", ".kt", ".kts", ".groovy", ".scala",
    # C 系
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".cs",
    # 其他语言
    ".go", ".rb", ".php", ".swift", ".m", ".mm", ".rs", ".dart",
    # 脚本
    ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1",
    # 数据 / 标记
    ".sql", ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".properties", ".conf", ".proto", ".graphql", ".gql",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 超过 5MB 视为生成物/打包产物，跳过
MIN_LINES_DEFAULT = 5000         # 行数提示阈值（不含空行）


def is_skipped_by_suffix(name):
    low = name.lower()
    return low.endswith(".min.js") or low.endswith(".min.css")


def read_text(path):
    """按 二进制BOM → utf-8 → gb18030 → latin-1 顺序解码，返回 (文本, 实际编码)。"""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace"), "utf-16"
    for enc in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace"), "latin-1"


def collect(root, output_path, include_dirs, with_separators):
    root = os.path.abspath(root)
    out_abs = os.path.abspath(output_path)
    if not os.path.isdir(root):
        sys.exit(f"错误：项目根目录不存在 {root}")

    files = []
    skipped_dirs, skipped_binary, skipped_noncode = [], [], []
    enc_warnings = []

    for dirpath, dirnames, filenames in os.walk(root):
        keep = []
        for d in dirnames:
            if d in SKIP_DIRS and d not in include_dirs:
                skipped_dirs.append(os.path.join(dirpath, d))
            else:
                keep.append(d)
        dirnames[:] = keep

        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.abspath(full) == out_abs:
                continue
            if name in SKIP_FILES or is_skipped_by_suffix(name):
                skipped_noncode.append(full)
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in INCLUDE_EXTS:
                skipped_noncode.append(full)
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size == 0 or size > MAX_FILE_SIZE:
                skipped_noncode.append(full)
                continue
            with open(full, "rb") as f:
                head = f.read(8192)
            if b"\x00" in head:
                skipped_binary.append(full)
                continue
            files.append(full)

    files.sort()
    chunks = []
    total_lines = 0
    ext_stats = {}
    for full in files:
        text, enc = read_text(full)
        if enc not in ("utf-8-sig", "utf-8"):
            enc_warnings.append((full, enc))
        lines = text.splitlines()
        total_lines += len([ln for ln in lines if ln.strip()])
        ext = os.path.splitext(full)[1].lower()
        ext_stats[ext] = ext_stats.get(ext, 0) + 1
        rel = os.path.relpath(full, root)
        if with_separators:
            chunks.append("// ====== %s ======" % rel)
        chunks.append("\n".join(lines) + "\n")

    content = "".join(chunks)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    # ---- 统计报告 ----
    print("[OK] 已生成 %s" % output_path)
    print("[INFO] 收集文件数: %d" % len(files))
    print("[INFO] 源程序总行数（不含空行）: %d" % total_lines)
    ext_sorted = sorted(ext_stats.items(), key=lambda kv: -kv[1])
    print("[INFO] 文件类型分布: %s"
          % ", ".join("%s=%d" % (k, v) for k, v in ext_sorted))
    if enc_warnings:
        print("[WARN] %d 个文件按非 UTF-8 编码读取（已统一转码为 UTF-8 输出）:"
              % len(enc_warnings))
        for p, e in enc_warnings[:10]:
            print("       %s: %s" % (e, os.path.relpath(p, root)))
        if len(enc_warnings) > 10:
            print("       ... 共 %d 个" % len(enc_warnings))
    if skipped_binary:
        print("[INFO] 跳过二进制文件: %d" % len(skipped_binary))
    if skipped_noncode:
        print("[INFO] 跳过非代码/配置文件/超大文件: %d" % len(skipped_noncode))
    if skipped_dirs:
        print("[INFO] 跳过依赖/构建目录: %d" % len(skipped_dirs))
    if total_lines < MIN_LINES_DEFAULT:
        print("[WARN] 源程序总行数（不含空行）%d < %d，软著源程序材料通常以 60 页左右为宜"
              "（约 3000 行以上），行数过少可能造成材料单薄。"
              "可考虑 --include-dir 纳入更多目录，或与用户确认。" % (total_lines, MIN_LINES_DEFAULT))


def main():
    ap = argparse.ArgumentParser(
        description="收集已有项目源代码，汇总为软著源程序文档（UTF-8 文本）")
    ap.add_argument("project_root", help="项目根目录")
    ap.add_argument("-o", "--output", default="source-code.txt",
                    help="输出文件路径（默认当前目录 source-code.txt）")
    ap.add_argument("--with-separators", action="store_true",
                    help="文件之间添加路径分隔标记（默认不加，符合软著源程序文档惯例）")
    ap.add_argument("--include-dir", dest="include_dirs", action="append",
                    default=[], metavar="DIRNAME",
                    help="额外纳入默认跳过的目录名（可多次指定）")
    ap.add_argument("--min-lines", type=int, default=MIN_LINES_DEFAULT,
                    help="行数提示阈值（默认 %d）" % MIN_LINES_DEFAULT)
    args = ap.parse_args()

    collect(args.project_root, args.output, args.include_dirs, args.with_separators)


if __name__ == "__main__":
    main()
