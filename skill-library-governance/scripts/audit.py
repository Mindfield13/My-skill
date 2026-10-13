#!/usr/bin/env python3
"""Read-only audit of the Hermes skill library. Prints ASCII only.

Covers: inventory, frontmatter-name conflicts (incl. nested SKILL.md),
usage join (dual-key), never-used families, injection-cost estimate.
Exits non-zero if structural defects are found (CI-friendly).
"""
import json, os, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME") or (Path(os.environ["LOCALAPPDATA"]) / "hermes"))
SK = HOME / "skills"

def frontmatter(p):
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None, 0, False
    m = re.match(r"^---\s*\n(.*?)\n---", t, re.S)
    name = desc = None
    folded = False
    if m:
        # multi-line aware: keep scanning indented continuation lines (YAML folded scalars)
        lines = (m.group(1) + "\n").splitlines()
        buf, key = None, None
        for ln in lines + [""]:
            km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", ln)
            if km and not ln[:1].isspace():
                if key == "name": name = buf
                elif key == "description": desc = buf
                key = km.group(1)
                buf = km.group(2).strip().strip("'\"")
                # YAML folded/literal indicator: value lives on continuation
                # lines only; drop the indicator so 'name: >-\n  x' yields 'x'
                # and still collides with a real 'name: x' elsewhere.
                if re.fullmatch(r"[>|][+-]?", buf or ""):
                    folded = folded or (key == "name")
                    buf = ""
            elif key and ln[:1].isspace() and buf is not None:
                buf += " " + ln.strip()
        if key == "name": name = buf
        elif key == "description": desc = buf
    return name, desc, t.count("\n") + 1, folded

def main():
    if not SK.is_dir():
        print(f"skills root missing: {SK}"); return 1
    # 1. inventory
    all_md = list(SK.rglob("SKILL.md"))
    active = [p for p in all_md if ".archive" not in p.parts]
    rows = []
    for p in active:
        rel = p.relative_to(SK)
        name, desc, lines, folded = frontmatter(p)
        rows.append({"rel": rel, "nested": len(rel.parts) > 2,
                     "name": name, "desc": desc or "", "lines": lines,
                     "folded": folded})
    print(f"SKILL.md active={len(active)} archived={len(all_md)-len(active)} total={len(all_md)}")

    # 2. frontmatter name conflicts across directories
    byname = defaultdict(list)
    for r in rows:
        if r["name"]: byname[r["name"]].append(str(r["rel"]))
    defects = 0
    print("-- name conflicts (same frontmatter name, multiple dirs) --")
    for n, ps in sorted(byname.items()):
        if len(ps) > 1:
            defects += 1
            print(f"  {n}: " + " | ".join(ps))
    for r in rows:
        if not r["name"] or r["name"] == ">-":
            defects += 1
            print(f"  broken frontmatter name: {r['rel']}")
        elif r["folded"]:
            # Hermes' own loader may key a folded name differently (e.g. '>-')
            defects += 1
            print(f"  folded name scalar (registration may diverge): {r['rel']}")
    print(f"nested registrations: {sum(1 for r in rows if r['nested'])}")
    for r in rows:
        if not r["desc"]:
            print(f"  missing description: {r['rel']}")

    # 3. usage join (dual-key: directory name OR frontmatter name OR leaf stem)
    try:
        out = subprocess.run(["hermes", "curator", "usage", "--json"],
                             capture_output=True, text=True, timeout=60)
        usage = json.loads(out.stdout)
    except Exception as e:
        print(f"usage telemetry unavailable: {e}"); usage = []
    umap = {u["name"]: u for u in usage}
    def used(r):
        for k in (r["name"], r["rel"].parts[0], r["rel"].stem):
            u = umap.get(k)
            if u and (u["use_count"] > 0 or u["view_count"] > 0): return True
        return False
    never = [r for r in rows if not used(r)]
    print(f"never-used (use=0,view=0): {len(never)} / {len(rows)}")
    def fam(n):
        for f in ("cli-anything", "seedance", "nature-", "story", "writing-", "grill", "taste", "electron-", "design", "brand", "imagegen-", "migrate-"):
            if n.startswith(f): return f
        return "other"
    fams = Counter(fam(r["rel"].parts[0]) for r in never)
    print("never-used by family: " + ", ".join(f"{k}={v}" for k, v in fams.most_common()))

    # 4. injection cost from the prompt snapshot
    snap = HOME / ".skills_prompt_snapshot.json"
    if snap.is_file():
        s = json.loads(snap.read_text(encoding="utf-8"))
        inj = sum(len(x.get("skill_name", "")) + len(x.get("description") or "") for x in s["skills"])
        print(f"injected index: {len(s['skills'])} skills, {inj:,} chars ~ {inj//4:,} tokens/turn")
    else:
        print("prompt snapshot not found (open a session once to regenerate)")
    print(f"DEFECTS={defects}")
    return 1 if defects else 0

if __name__ == "__main__":
    sys.exit(main())
