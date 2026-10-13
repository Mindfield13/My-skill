---
name: long-doc-delivery
description: Use when distilling experience into a long .md reference.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [documentation, writing, verification, docx, distillation]
---

# Long-form Document Delivery

Produce a standalone long-form reference document (guide, experience digest, command reference) as `.md`, verified programmatically, with a `.docx` twin when the target directory keeps one. Distinct from `doc-coauthoring` (interactive co-writing with the user) and `research` (web investigation captured into a repo).

## Procedure

1. **Check the delivery convention first.** `ls` the target directory. If sibling documents exist as md+docx pairs, this deliverable is a pair too — convert at the end (step 6). Match existing file naming.

2. **Gather sources in parallel before writing anything.** Independent lookups belong in ONE turn:
   - persistent memory + user profile (already in the system prompt) — preferences, environment rules;
   - `skills_list` → `skill_view` the 2-4 class skills covering the domain — their pitfalls sections are the highest-density material;
   - `session_search` discovery queries per project/topic (limit 5-8) plus a recent/oldest browse for the project timeline — extract architecture decisions, corrections, and fixed bugs, not chat narration.
   Record which source each fact came from; claims in the document must trace to one of them.

3. **Outline before writing:** numbered chapters with a TOC at the top; pitfalls as tables (`| # | 坑 | 解法 |`); one chapter per source domain; include a lessons/corrections chapter when corrections exist. One pass, complete — do not plan to return and append later.

4. **Write in quoted-heredoc chunks, ~100-150 lines per terminal call:** first chunk `cat > file << 'EOF'`, subsequent chunks `cat >> file << 'EOF'`, then `wc -l` after every chunk and compare against the running total. Never one giant heredoc; never `write_file` for long mixed prose/code content (it can mangle literal escapes — verify any file it does write with a parse check).

5. **Verify programmatically after each chunk and at the end**, reading the RAW file with `open()` inside `execute_code`:
   - every chapter/subheading present (count and names);
   - one anchor phrase per chapter found;
   - no heredoc delimiter residue;
   - tables: consistent column counts, separator rows present, row counts as expected.
   Report only counts that were actually checked this way.

6. **`.docx` twin** (directory convention or explicit request):
   - `skill_view(name='productivity/docx')` (the bare name `docx` is ambiguous — two skills match) to get `skill_dir`;
   - convert: `py <skill_dir>/scripts/md2docx_spec.py input.md out.spec.json` (this skill's converter emits the A4 spec `docx_create.py` expects);
   - build: `py <skill_dir>/scripts/docx_create.py out.spec.json out.docx`;
   - verify: `docx_validate.py out.docx` must return ok, then `docx_read.py out.docx --structure` — heading outline and table shapes (rows incl. header × cols) must match the md.

7. **Deliver:** absolute paths plus the verified counts. In CLI, state paths as plain text.

## Which deliverable shape

- **Comprehensive guide** (this skill): everything verified from sources, chapters + tables, complete in one pass.
- **Change report** (`*_本次改动.md`, a different deliverable): only this session's changed files, edited code, commands, and verification results — no history comparison, no general analysis, no hardening suggestions, no disclaimers. Do not apply the comprehensive style to a change report or vice versa.

## Pitfalls

- Verify structure on the raw file, never on `read_file` output — its `NN|` line-number prefix silently fails every `startswith('#')` / `startswith('|')` check and reports zero headers and zero tables on a healthy file.
- Table-separator detection must include the pipe inside the character class (`^\|[\s:|\-]+\|?$`, not `[\s:-]`) — a separator row is mostly pipes, so the narrow class never matches and every table row silently degrades into a paragraph while the docx still validates ok.
- A single oversized heredoc (several hundred lines) can die at shell parse time with an EOF/quote error before writing anything — treat that as "split the chunk", not "debug the content"; the file is untouched.
- Run converter scripts under a native Windows interpreter (`py`) from an explicit `C:/...` path — bash `$TMPDIR` / `/tmp` resolves to an MSYS location the native interpreter cannot open.
- Pandoc is absent in this environment — use the spec-converter route above rather than a md-to-docx one-liner.
