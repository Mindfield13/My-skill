---
name: codebase-audit-refactor
description: "Audit a whole project, then fix and verify tier by tier."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, refactoring, code-quality, audit, refactor, python]
---

# Codebase Audit & Batch Refactor

Full-project review and improvement workflow. Distinct from git-diff reviews (the `code-review` skill) — this is when the user wants the **whole codebase** audited and improved, often saying "看看有什么要改的" / "review the project" / "what should we improve".

## Workflow

### Step 1 — Read breadth-first, then debug narrow

- Map the structure first: `search_files`/`find` for the file tree, then `wc -l` per file to find hot spots (the biggest file usually holds the smell-bloat).
- Read the entry point + the largest / churn-heavy files fully. Skim the rest.
- Note environment facts that matter (e.g. user-data dir is `Path.home()/".<name>"` — check for **naming drift** between the app's product name and its code-name/data-dir across versions; that's a real migration bug class).

### Step 2 — Classify findings into severity tiers

Produce a table `# | 位置 | 问题 | 建议`. Assign tiers:

- **P0 (must fix)** — correctness, privacy, unbounded growth, broken encapsulation, obvious bugs, per-frame performance sins.
- **P1 (important)** — file bloat, hardcoded values, dead code, missing versioning, no user feedback after an action, platform-breaking calls.
- **P2 (worth improving)** — magic numbers, missing project config, template-code duplication, UI-thread blocking, param-signature mismatch.
- **P3 (suggestions)** — missing type hints, over-frequent effects, no tests, subjective UX.

### Step 3 — Fix tier by tier, batch + verify each tier

- Present the audit table first, then ask which tier to start. If the user says "一步步改" / "continue" / "P2", go in order P0→P1→P2→P3. Do NOT fix everything in one pass.
- Fix one tier as a batch, then **verify the whole batch before moving on** (compile + a purpose-built check per fix).
- **Verification pattern**: write a throwaway script `C:\Users\...\Temp\hermes-verify-<tier>.py` that imports the changed modules and asserts each fix's observable behavior. Run it, confirm all checks pass, then delete it. Faster and more reliable than a full GUI app launch.

## Reusable Python refactor patterns

- **Config-property boilerplate → descriptor.** A settings class with N read/write `@property`+`@setter` pairs (~6 lines each) collapses to N one-liners with a data descriptor:
  ```python
  class _Setting:
      def __init__(self, *keys, default=None): self._keys, self._default = keys, default
      def __get__(self, obj, objtype=None):
          if obj is None: return self
          return obj.get(*self._keys, default=self._default)
      def __set__(self, obj, value): obj.set(*self._keys, value=value)
  # in class body:
  scale = _Setting("window", "scale", default=1.0)
  ```
  Settings refactors are high-blast-radius: verify get/set/persist round-trip after converting.
- **Per-frame image transform → cache.** If a hot path (e.g. `current_frame` at 60fps) calls `image.transpose()` every read, cache keyed by `(state, index, flip)` and clear the cache when state/flip changes. Verify the cached object is **reused (same identity)**, not just recomputed.
- **AI prompt inflation → separate field.** Don't `set_system_prompt(existing + dynamic_line)` each call (grows unbounded). Add a dedicated context field (`_mood_context`) that the message-rebuild injects fresh each call.
- **PyQt5/Tk UI thread safety.** Never call blocking IO (`requests.get`) on the UI thread — freezes the dialog up to the timeout. Move network into a daemon `threading.Thread`, marshal UI updates back with `QTimer.singleShot(0, lambda: ...)`. Wrap error paths the same way.
- **Dead code check.** Before deleting a method, `grep -rn "<name>" --include="*.py"` across the repo. If the only hit is its own definition, it's dead — delete it.
- **Hardcoded Magic numbers → named class constants.** Extract `QTimer.start(45*60*1000)` into `WATER_REMINDER_MS`-style constants so tuning is a one-edit change.

## Pitfalls

- `read_file` may report a large/odd UTF-8 file as "binary" (0 content). Cleanest on Windows+MSYS: read via `execute_code` with `open(p, encoding='utf-8').read().replace('\r\n','\n')` then split lines — avoids both the binary flag and CRLF noise.
- After each tier batch, syntax-check right after patching: `python -m py_compile <changed files>` for Python; **`node --check <file>.js` for JS/Node** (works even for browser scripts — it's syntax-only, window/document globals are fine). For behavior, `node -e` one-liners are the fast loop.
- A recurring JS runtime bug to probe in JS audits: **`'\\n'` literal vs `'\n'` newline**. Code using `join('\\n')`, `split('\\n')`, `endsWith('\\n')` with a literal double-backslash silently breaks line counting and prompt formatting. Detect: `grep -c "'\\\\n'" file.js` (nonzero = suspect); confirm behaviorally with `node -e "console.log('a\\nb'.split('\\n').length)"` — 1 means literal `\n` text, 2 means real newline.
- When fixing subprocess cleanup (kill_process, taskkill, soffice), never kill by image name (`taskkill /F /IM x /T`) — it kills the user's own running instances and can lose unsaved work. Snapshot pre-existing PIDs (`tasklist /FI "IMAGENAME eq x" /FO CSV /NH`), then kill only PIDs NOT in that whitelist.
- `grep -c` returns exit 1 when count is 0 — don't chain it in `&&` pipelines expecting count output (the chain silently dies). Run greps separately or use `for` loops with `awk` sums.
- If a patch diff warns "file was modified since you last read it", re-read before the next patch — stale line numbers will miss. Whitespace in CRLF files can also drift after patch — verify indentation by re-reading the region, fix via `execute_code` string replace, then re-run the syntax check.
- When a test assertion fails, diagnose whether the **code** or the **assertion** is wrong (e.g. a substring check `"import X" in src` fails on `import a, b, X` — use a regex `import\s+.*\bX\b`).