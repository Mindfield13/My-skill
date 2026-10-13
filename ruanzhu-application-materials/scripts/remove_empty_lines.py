#!/usr/bin/env python3
"""Remove empty lines from source code file."""

import argparse
import os
import sys


def remove_empty_lines(input_path, output_path=None, remove_all=False):
    """Remove empty lines from file.

    Args:
        input_path: Input file path
        output_path: Output file path (default: overwrite input)
        remove_all: If True, remove all empty lines. If False, keep single empty lines.
    """
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    if output_path is None:
        output_path = input_path

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    result = []

    if remove_all:
        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped:
                result.append(stripped)
    else:
        prev_empty = False
        for line in lines:
            stripped = line.rstrip("\n\r")
            if not stripped:
                if not prev_empty:
                    result.append("")
                prev_empty = True
            else:
                result.append(stripped)
                prev_empty = False

        if result and not result[-1]:
            result.pop()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(result) + "\n")

    removed = len(lines) - len(result)
    print(f"[OK] Removed {removed} empty lines, {len(result)} lines remaining")
    print(f"[OK] Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Remove empty lines from source code file")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("--output", "-o", help="Output file path (default: overwrite input)")
    parser.add_argument("--all", "-a", action="store_true", help="Remove all empty lines")
    args = parser.parse_args()

    remove_empty_lines(args.input, args.output, args.all)


if __name__ == "__main__":
    main()
