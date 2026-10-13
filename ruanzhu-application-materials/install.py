#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本技能安装到 Claude Code / Codex CLI 的 skills 目录。

用法:
    python install.py                     # 装到 ~/.claude/skills 与 ~/.codex/skills
    python install.py --target claude     # 只装 Claude Code
    python install.py --target codex      # 只装 Codex CLI
    python install.py --target agents     # 只装 ~/.agents/skills（部分 Codex 版本也扫这里）
    python install.py --target project    # 装到 ./.claude/skills 与 ./.codex/skills（可提交给团队）
    python install.py --list              # 查看各目标现状，不动文件
    python install.py --uninstall         # 从上述位置卸载
    python install.py --dry-run           # 只打印会做什么
    python install.py --force             # 覆盖已存在的同名技能

安装方式就是**整目录复制**（SKILL.md + scripts/ + references/）。Claude Code 与
Codex CLI 读的是同一套 SKILL.md 规范，因此不需要为哪个平台单独转换格式。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_NAME = "ruanzhu-application-materials"
SRC = Path(__file__).resolve().parent
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "*.log")


def target_dirs(name: str) -> list[Path]:
    """目标名 → 目标 skills 目录列表。"""
    home = Path.home()
    if name == "claude":
        return [home / ".claude" / "skills"]
    if name == "codex":
        return [home / ".codex" / "skills"]
    if name == "agents":
        return [home / ".agents" / "skills"]
    if name == "project":
        cwd = Path.cwd()
        return [cwd / ".claude" / "skills", cwd / ".codex" / "skills"]
    raise ValueError(f"未知目标：{name}")


TARGET_LABEL = {
    "claude": "Claude Code（个人）",
    "codex": "Codex CLI（个人）",
    "agents": "共享 skills 目录（部分 Codex 版本扫描）",
    "project": "当前项目（可提交给团队）",
}

ALL_TARGETS = ["claude", "codex"]


def resolve_targets(arg: str) -> list[str]:
    return ALL_TARGETS if arg == "all" else [arg]


def check_source() -> bool:
    if not (SRC / "SKILL.md").is_file():
        print(f"Error: {SRC} 下没有 SKILL.md，无法作为技能源。", file=sys.stderr)
        return False
    return True


def do_list(targets: list[str]) -> int:
    print(f"技能名：{SKILL_NAME}\n技能源：{SRC}\n")
    print(f"{'目标':<14}{'状态':<10}{'文件数':<8}路径")
    print("-" * 78)
    for name in targets:
        for base in target_dirs(name):
            dest = base / SKILL_NAME
            if dest.is_dir():
                count = sum(1 for p in dest.rglob("*") if p.is_file())
                status = "已安装"
            else:
                count = 0
                status = "未安装"
            print(f"{name:<14}{status:<10}{count:<8}{dest}")
    return 0


def do_install(targets: list[str], force: bool, dry_run: bool) -> int:
    installed = 0
    for name in targets:
        for base in target_dirs(name):
            dest = base / SKILL_NAME
            print(f"\n[{TARGET_LABEL.get(name, name)}]")
            print(f"  {dest}")
            if dest.exists():
                if not force:
                    print("    ⚠ 已存在，跳过（加 --force 覆盖）")
                    continue
                if dry_run:
                    print("    将删除旧版本并重新复制")
                else:
                    shutil.rmtree(dest)
            if dry_run:
                print("    将复制 SKILL.md + scripts/ + references/")
                installed += 1
                continue
            base.mkdir(parents=True, exist_ok=True)
            shutil.copytree(SRC, dest, ignore=IGNORE)
            files = sum(1 for p in dest.rglob("*") if p.is_file())
            print(f"    ✓ 已复制 {files} 个文件")
            installed += 1

    if dry_run:
        print(f"\n[dry-run] 未改动任何文件，计划安装 {installed} 处。")
        return 0

    print(f"\n完成：安装 {installed} 处。")
    return 0 if installed else 1


def do_uninstall(targets: list[str], dry_run: bool) -> int:
    removed = 0
    for name in targets:
        for base in target_dirs(name):
            dest = base / SKILL_NAME
            if not dest.is_dir():
                print(f"  - 未安装，跳过：{dest}")
                continue
            if dry_run:
                print(f"  将删除：{dest}")
            else:
                shutil.rmtree(dest)
                print(f"  ✓ 已删除：{dest}")
            removed += 1
    if dry_run:
        print(f"\n[dry-run] 计划删除 {removed} 处。")
    else:
        print(f"\n完成：删除 {removed} 处。")
    return 0


def report_sources(targets: list[str]) -> None:
    paths = []
    for name in targets:
        paths += [str(base / SKILL_NAME) for base in target_dirs(name)]
    print("\n各工具里脚本的调用路径（技能目录 = SKILL.md 所在目录）：")
    for p in dict.fromkeys(paths):
        print(f"  SKILL_DIR=\"{p}\"")
    print("\nClaude Code 里可直接 /ruanzhu-application-materials 调用；")
    print("Codex CLI 里用 $ruanzhu-application-materials，或直接描述任务自动匹配。")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"安装 {SKILL_NAME} 到 Claude Code / Codex CLI")
    parser.add_argument("--target", default="all",
                        choices=["all", "claude", "codex", "agents", "project"],
                        help="安装目标，默认 all（claude + codex）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的同名技能")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不动文件")
    parser.add_argument("--list", action="store_true", help="查看各目标现状")
    parser.add_argument("--uninstall", action="store_true", help="卸载")
    args = parser.parse_args()

    if not check_source():
        return 1

    targets = resolve_targets(args.target)

    if args.list:
        return do_list(targets)
    if args.uninstall:
        return do_uninstall(targets, args.dry_run)
    code = do_install(targets, args.force, args.dry_run)
    if code == 0 and not args.dry_run:
        report_sources(targets)
    return code


if __name__ == "__main__":
    sys.exit(main())
