---
name: skill-library-governance
description: "Audit, prune, and govern a Hermes skill library in batches."
version: 1.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, curation, audit, token-cost, hermes]
    related_skills: [skill-creator, hermes-agent, writing-great-skills]
---

# Skill Library Governance

Auditing and pruning a Hermes skill library (hundreds of skills) so that what loads per turn is what the user actually uses, with every action reversible. This is asset governance of the library as a whole — for creating or improving a single skill, use skill-creator instead.

## When to Use

- The user wants to 管理/整理/治理/体检 skills or the skill 库, cut skill-related token cost, disable unused skills, or resolve duplicate skill names.
- The user asks 「我有很多 skill 怎么办」 or proposes any skill-library 方案.
- The user hands over a `HANDOFF` / `治理方案` / audit document about skills.
- NOT for writing a new skill or improving one skill's content — that is skill-creator.

## Standing rules

- **Read-only first.** Produce an inventory report before any change; execution starts only after the user picks a tier — if the user skips the choice, run the recommended tier with an explicit protect list and state the one-command revert in the reply (this user prefers forward motion over confirmation stalls). Deletions, registry edits, and system-permission changes need explicit per-action approval — disabling/archiving is preferred over deleting because both are reversible.
- **Report = measured rows + reproduction commands.** Every claim carries the command that produced it. No generic analysis, no disclaimers, no historical diff in the report — the user's documented preference is only the current measured facts.
- **Console output ASCII-only** on this machine (Windows console code page mangles CJK in pipes); Chinese is fine in files written to disk.
- Write config through `hermes config set`, never by hand-editing `config.yaml` (a stray indent breaks the live gateway).

## Procedure

### 0. Check for prior governance work first

Use `search_files(target='files')` on the working directory for `HANDOFF*`, `*方案*`, `*audit*`, `*体检*` files. Skill governance is recurring for this user and past sessions leave handoffs with baselines, pending decisions, and ready-made scripts — read them before collecting data, or you duplicate a finished audit and miss decisions already framed.

### 1. Collect the inventory

```bash
hermes skills list                 # registered skills, source (builtin/hub/local), enabled state
hermes skills list --enabled-only  # what actually loads for this profile
hermes curator status              # managed vs unmanaged counts, archive policy
hermes curator usage --json        # per-skill use/view/patch counts + provenance (the decision evidence)
hermes bundles list                # grouping state
hermes skills list-modified        # drift from bundled originals
find $LOCALAPPDATA/hermes/skills -name SKILL.md | wc -l   # on-disk total incl. .archive
```

### 2. Measure per-turn injection cost

The skill index injected into the system prompt is snapshotted at `<hermes-home>/.skills_prompt_snapshot.json` — a JSON object whose `skills` array has `skill_name` (directory), `frontmatter_name`, `category`, `description` per entry. Injected cost ≈ Σ(len(skill_name) + len(description)) chars; chars ÷ 4 ≈ tokens. This is the per-turn cost of the library; SKILL.md *bodies* only cost when loaded, so big bodies are a load-time concern, not an always-on one.

The snapshot is written **only when a prompt is built** — `hermes skills list` does NOT refresh it, so post-change reads of the file can be stale. Rebuild it deterministically (no API call) and re-measure:

```python
import sys, os
from pathlib import Path
sys.path.insert(0, os.environ['LOCALAPPDATA'] + r'\hermes\hermes-agent')  # repo root ONLY
from agent.prompt_builder import _build_skills_system_prompt_inner
_build_skills_system_prompt_inner(Path(os.environ['LOCALAPPDATA'])/'hermes'/'skills', [], None, None, None)
```
Add only the repo root to `sys.path`: adding `hermes_cli/` puts its `gateway.py` ahead of the `gateway/` package and the build dies with ModuleNotFoundError.

### 3. Join usage telemetry (dual-key)

Usage records key on `name`, but that key is sometimes the directory name and sometimes the frontmatter name (a broken frontmatter even produces a key like `>-`). When matching telemetry to a skill, try **both** `skill_name` and `frontmatter_name` (plus the leaf directory) before concluding a skill is unused. A skill with use=0 and view=0 is a disable candidate, not automatically an archive candidate.

`created_at` / `first_seen_at` describe the **telemetry record**, not the skill — they reset when the usage store rebuilds, so never use them as an "installed recently" guard (it misclassifies most of the library as new). Skills created mid-governance are covered by the use/view check itself: `skill_view` logs a view, so opening a skill during the audit already marks it used.

### 4. Detect conflicts and true duplicates

- **Nested SKILL.md files register too.** `productivity/docx/SKILL.md` is a second `docx` in the index, not a sub-file. Filter nested paths with `len(rel.parts) > 2` for a `SKILL.md` relative path (counting `depth = len(parts) - 1` then testing `depth > 0` matches top-level files too — off-by-one that inflates every nested finding).
- **Name conflict ≠ duplicate content.** Group by frontmatter name across directories: byte-compare (`sha256sum`) before deciding. Byte-identical → archive one copy. Different content under one name → **rename the frontmatter** (each variant is a real skill); never delete the 'other copy'.
- Watch for frontmatter folded scalars: `name: >-` followed by an indented line — a naive `key: value` regex captures `>-`, and the directory name becomes a second, colliding registration. Parse multi-line YAML scalars when scanning.
- Sub-skill directories with missing/partial frontmatter still get scanned; flag them as fix-list items.

### 5. Build the decision table

| Tier | Criterion | Action |
|---|---|---|
| Keep | use > 0 | untouched |
| Fix | name conflict, broken frontmatter, byte-identical dup | rename / patch / archive one copy |
| Protect | 0 telemetry but the user's live project lines (their current work, per memory/user profile) | keep regardless of telemetry — a wrong disable fails silently when they ask for that work |
| Disable | use = 0, still plausible for the user's domain | `skills.disabled` (reversible) |
| Skip | entries with `requires_*`/`fallback_*` conditions or `platforms` | keep — hidden when the condition matches, so they cost nothing per turn; disabling buys no tokens and loses the fallback |
| Archive | byte-identical dup or confirmed obsolete | `hermes curator archive` (lands in `.archive/`, excluded from prompt; restorable) |
| Ask | domain line the user may still run | leave undecided, put in report |

Estimate token savings at two tiers (large idle families only vs all unused) so the user picks a budget, not a pile of rows.

When the user asks what the library contains (分类/统计/表格/what does each do), produce a classified table: ordered regex rules over `skill_name` plus a MANUAL override map for the leftovers, joined with telemetry + disabled set + bundle membership, written to a file as markdown grouped by category — an overview count table (数量/启用/禁用/用过) first, then per-row 用途/状态/使用/场景包. Keep the chat reply to the overview table + structural observations; the 200-row detail lives in the file.

### 6. Execute in batches, verify each

1. **Structural fixes**: archive byte-identical dups, patch folded-scalar/nested frontmatter, rename shared names. Verify: `hermes skills list` shows no duplicate names, every name resolves via `skill_view`, snapshot entry count dropped (rebuild it first — step 2).
   `hermes curator archive <name>` resolves *managed/registered* names; an unmanaged skill returns `skill not found`. For those: confirm `.archive/<name>` is free, then `mv` the directory there by hand — same effect (excluded from index, restorable).
   Which copy of a duplicated builtin survives: keep the copy `hermes update` re-seeds (the Hermes-maintained one, usually under its category dir); archive the copy the sync client delivered. Both may differ in content — verify with `sha256sum` and the update log, not with age alone.
2. **Disable**: `hermes config set skills.disabled '["name1","name2"]'` — the value is parsed as YAML, so pass a list literal. Essential skills (e.g. `hermes-agent`) are silently dropped from the list — that's expected, not an error. Re-baseline the disable list right before writing: `hermes update` re-seeds bundled skills between audit and execution and reclassifies builtin/local counts. Verify: `--enabled-only` count drops by the list length and the rebuilt prompt (step 2) no longer contains the disabled names.
3. **Governance**: `hermes curator adopt <name>` for unmanaged skills (they are never auto-pruned otherwise), consider `curator.consolidate` for LLM merge of overlapping families, `hermes skills snapshot` for a config baseline. **Pin the protect-list first** (`hermes curator pin <name>`, one per call): once adopted, idle skills are fed to the 30-day auto-archiver by the next scheduled run, and a pinned skill is the only thing that exempts an episodic domain line from it.
4. **Integrate into scenario packs.** The end state the user wants is one slash command per scenario, not a flat list of names to remember. Group the enabled skills a scenario needs into a bundle:
   ```bash
   hermes bundles create <slug> --skill a --skill b \
     --description "<场景一句话>" --instruction "<该场景的长期规矩,不是技能内容>" --force
   ```
   Non-interactive form; files land in `<hermes-home>/skill-bundles/<slug>.yaml`. The bundle loader **skips disabled members**, so packs contain enabled skills only — build them after the disable batch, not before. Pick short slugs that collide with no skill name (on a collision the bundle wins slash dispatch). Verify: `hermes bundles list`, `hermes bundles show <slug>` (members + instruction).
5. **Delete** — only when the user explicitly says remove/删, not archive. Gate: verify every target has a copy in the central store (`test -d ~/.cc-switch/skills/<name>` per target; any target missing there is the only copy — archive it instead). Write a rollback manifest (name, `sha256sum` prefix of SKILL.md, store restore path) to scratch, then `shutil.rmtree`. Afterwards purge the deleted names from `skills.disabled`: `hermes config get skills.disabled` prints a **YAML list** (`- item` per line — `ast.literal_eval` chokes on it); parse line-wise, filter, `hermes config set`. Report freed size honestly — a thin family costs registry slots and attention, not disk.

Report before/after counts per batch; do not start the next batch until the current one verifies.

### 7. Run the bundled probe

`scripts/audit.py` performs steps 1–4 in one read-only pass (inventory, frontmatter-name conflicts, nested registrations, never-used families, injection estimate) and prints ASCII output. Run it first, then read its output for the decision table.

## Pitfalls

- **Same name across roots is the normal state of a multi-root estate** (central store + per-agent delivery dirs are physical copies, not links) — deduplicate by content hash, and only within one root; cross-root 'duplicates' are the delivery mechanism, not waste. Verify delivery mode instead of trusting the sync client's setting: walk the root with `os.stat(path, follow_symlinks=False)` and test `st_file_attributes & 0x400` (reparse), plus `grep -c 'os error 1314'` on the sync client's log — zero reparse points with a non-zero error count means copy fallback regardless of what the UI claims.
- **File-level fixes are local while delivery is by copy**: the next sync from the central store re-copies store-owned skills and silently reverts renames and archives. Durable levers are `skills.disabled` (config.yaml, untouched by sync) and fixes made in the store itself; after any sync, re-run the structural batch.
- **Never `rm -rf` a delivery directory** once symlink delivery is active — recursive delete follows links into the central store. Check `REPARSE_POINT` first and unlink only.
- **Zero telemetry does not mean zero value** for domain families (academic, fiction lines): surface them as an 'ask' tier instead of folding into disable — the cost of a wrong disable is a skill that silently never triggers.
- **`hermes skills list` counts and snapshot entry counts are different books** (shadowed duplicates and nested registrations are counted differently): compare each against its own baseline, and verify injection cost from the rebuilt prompt, never by cross-subtracting the two.