---
name: software-development-workflow
description: "Software development process skills — root cause debugging, TDD, spiking, code review/simplify, pre-commit verification, Node.js debugging, and codebase inspection"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [development, debugging, tdd, testing, code-review, spike, prototyping, code-quality]
---

# Software Development Workflow

Process and methodology skills for day-to-day development work. Covers **debugging**, **testing (TDD)**, **prototyping (spikes)**, **code review**, **pre-commit verification**, **code simplification**, **debugging tools**, and **codebase analysis**.

---

## Section 1: Systematic Debugging

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### The Iron Law
```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

### Four Phases

**Phase 1: Root Cause Investigation** — DO NOT SKIP
1. Read error messages carefully (stack traces, line numbers, error codes)
2. Reproduce consistently — can you trigger it every time?
3. Check recent changes — `git log --oneline -10`, `git diff`
4. Trace data flow upstream — where does the bad value originate?
5. Add diagnostic instrumentation at component boundaries

**Phase 2: Pattern Analysis**
- Find working examples in the same codebase
- Compare working vs. broken — list every difference
- Understand dependencies and assumptions

**Phase 3: Hypothesis & Testing**
- Form ONE hypothesis: "I think X is the root cause because Y"
- Make the SMALLEST possible change to test it
- One variable at a time. If it doesn't work → new hypothesis

**Phase 4: Implementation**
- Create a failing test case first (see TDD)
- Implement ONE fix addressing the root cause
- Verify: regression test + full test suite
- **Rule of Three**: If 3+ fixes failed, STOP and question the architecture

### The "3 Fixes" Rule
If 3+ fixes have failed:
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere
→ STOP. Question the architecture. Discuss with user.

---

## Section 2: Test-Driven Development (TDD)

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

### The Iron Law
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

### RED-GREEN-REFACTOR Cycle

**RED — Write Failing Test**
- One behavior per test
- Clear descriptive name
- Real code, not mocks (unless unavoidable)

**Verify RED — Watch It Fail (MANDATORY)**
```bash
pytest tests/test_feature.py::test_specific_behavior -v
```
- Test fails for expected reason (feature missing, not typo)
- If test passes immediately → testing existing behavior → fix the test

**GREEN — Minimal Code**
- Write simplest code to pass. Nothing more.
- Cheating is OK in GREEN: hardcode, copy-paste, skip edge cases
- Fix in REFACTOR

**Verify GREEN — Watch It Pass**
```bash
pytest tests/test_feature.py::test_specific_behavior -v
pytest tests/ -q  # full suite for regressions
```

**REFACTOR — Clean Up**
- Remove duplication, improve names, extract helpers
- Keep tests green throughout
- If tests fail during refactor → undo immediately, take smaller steps

### Common Rationalizations to Reject

| Excuse | Truth |
|--------|-------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Delete code is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "TDD will slow me down" | TDD is faster than debugging. |

---

## Section 3: Spike — Throwaway Experiments

Validate an idea before committing to a real build. Spikes are disposable by design.

### When to Spike
- User says "let me try this", "see if X works", "quick prototype"
- Answer isn't knowable from docs — you must build to learn
- Comparing A vs B approaches

### Core Loop
```
decompose → research → build → verdict
    ↑______________________________↓
```

1. **Decompose**: Break into 2-5 independent feasibility questions
2. **Research briefly**: Surface competing approaches, pick one
3. **Build**: One directory per spike, standalone, no complex tooling
4. **Verdict**: Each spike's README closes with VALIDATED / PARTIAL / INVALIDATED

### Structure
```
spikes/
├── 001-websocket-streaming/
│   ├── README.md    # question, approach, results, verdict
│   └── main.py      # throwaway code
├── 002a-pdf-parse-pdfjs/
└── 002b-pdf-parse-camelot/    # comparison spikes
```

### Verdict Format
```
## Verdict: VALIDATED | PARTIAL | INVALIDATED
### What worked
### What didn't
### Surprises
### Recommendation for the real build
```

### Tips
- Bias toward something the user can interact with (CLI, HTML page, web server)
- Test edge cases — never declare "it works" after one happy-path run
- For comparison spikes (A vs B), build in parallel via `delegate_task`

---

## Section 4: Simplify Code — Parallel 3-Agent Cleanup

Review recent changes with three focused reviewers running in parallel.

### When to Use
User says: "simplify", "review my recent changes", "clean up"

### Process

**Phase 1 — Capture the diff**
```bash
git diff                      # uncommitted changes
git diff HEAD                 # includes staged
git diff main...HEAD          # branch changes
```

**Phase 2 — Launch three reviewers in parallel** via `delegate_task(tasks=[...])`:

1. **Code Reuse** — existing functions/constants being duplicated; search utilities, shared helpers
2. **Code Quality** — redundant state, parameter sprawl, copy-paste-with-variation, stringly-typed code
3. **Efficiency** — unnecessary work, missed concurrency, N+1 patterns, TOCTOU anti-patterns

**Phase 3 — Aggregate and apply**
- Merge findings, dedup, discard false positives
- Resolve conflicts: correctness > user's focus > readability > micro-perf
- Apply fixes with `patch`/`write_file`, verify with tests/lint

---

## Section 5: Pre-Commit Verification

Automated verification pipeline before code lands.

### Steps

1. **Get the diff**: `git diff --cached` (staged) or `git diff HEAD`
2. **Static security scan**: Check for hardcoded secrets, SQL injection, eval/exec, shell injection
3. **Baseline tests + linting**: Run tests/linters, stash changes first to measure baseline, compare
4. **Self-review checklist**: Secrets, input validation, error handling, debug prints, tests
5. **Independent reviewer subagent**: Use `delegate_task` with strict JSON-only verdict
6. **Evaluate results**: All passed → commit. Any failures → auto-fix loop.
7. **Auto-fix loop** (max 2 cycles): Spawn a fix agent for reported issues, re-verify
8. **Commit**: `git add -A && git commit -m "[verified] <description>"`

### Static Scan Patterns

```bash
# Hardcoded secrets
git diff --cached | grep "^+" | grep -iE "(api_key|secret|password|token)\s*=\s*['\"][^'\"]{6,}['\"]"
# Shell injection
git diff --cached | grep "^+" | grep -E "os\.system\(|subprocess.*shell=True"
# SQL injection
git diff --cached | grep "^+" | grep -E "execute\(f\"|\.format\(.*SELECT|\.format\(.*INSERT"
```

---

## Section 6: Node.js Inspect Debugger

Drive Node's built-in V8 inspector programmatically. Real breakpoints, step in/over/out, call stack, eval in frame.

### `node inspect` REPL

```bash
node inspect path/to/script.js
node --inspect-brk $(which tsx) path/to/script.ts  # TypeScript
```

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `cb('file.js', 42)` | clear breakpoint |
| `bt` | backtrace |
| `list(5)` | show 5 lines of source |
| `repl` | eval expressions in current scope |
| `watch('expr')` | watch expression on every pause |

### Attaching to Running Process

```bash
kill -SIGUSR1 <pid>  # enable inspector on existing process
node inspect -p <pid>
# Or by URL
node inspect ws://127.0.0.1:9229/<uuid>
```

### Key Flags

- `--inspect-brk` — pause on first line (for setting breakpoints before code runs)
- `--inspect=0.0.0.0:9230` — custom host:port
- `--inspect=0` — random port

### One-Shot Recipes

```bash
# "Why is this variable undefined at line X?"
node --inspect-brk script.js &
node inspect -p $!
# debug> sb('script.js', X)
# debug> cont
# debug> repl  → inspect variables

# "What's the call path?"
# debug> sb('suspectFn')
# debug> cont
# debug> bt

# "This async chain hangs — where?"
# Start with --inspect (no -brk)
# After hang: debug> pause, debug> bt
```

### Pitfalls
- Breakpoints hit emitted JS, not `.ts` — break in `dist/*.js` or enable sourcemaps
- Port collisions: default 9229, use `--inspect=0` for random port
- `Ctrl+C` while paused = target stays paused. `cont` first or `kill` explicitly
- Security: always bind to `127.0.0.1` (the default)

---

## Section 7: Codebase Inspection (pygount)

Analyze repositories for lines of code, language breakdown, file counts, and code-vs-comment ratios.

### Quick Start

```bash
pip install pygount
pygount --format=summary --folders-to-skip=".git,node_modules,venv,__pycache__,.cache,dist,build" .
```

### Common Variants

```bash
# Filter by language
pygount --suffix=py --format=summary .
pygount --suffix=py,yaml,yml --format=summary .

# JSON output for programmatic use
pygount --format=json .

# Detailed per-file (pipe through sort)
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

### Output Columns
- **Language**, **Files**, **Code**, **Comment**, **%**
- Special pseudo-languages: `__empty__`, `__binary__`, `__duplicate__`, `__unknown__`

### Pitfalls
- Always exclude `.git`, `node_modules`, `venv` — without `--folders-to-skip`, pygount crawls everything
- Markdown shows 0 code lines (classified as comments)
- JSON counted conservatively — use `wc -l` for accurate JSON counts