---
name: autonomous-coding-agents
description: "Orchestrate AI coding agent CLIs — Claude Code, OpenAI Codex, and OpenCode — for features, refactoring, PR review, and batch issue fixing"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Claude, Codex, OpenCode, Autonomous, Refactoring, Code-Review, Automation]
---

# Autonomous Coding Agents

Orchestrate AI coding assistants through Hermes terminal. Three supported agents: **Claude Code** (Anthropic), **Codex** (OpenAI), and **OpenCode** (open-source, provider-agnostic). Each runs via PTY for interactive use or via a non-interactive command for one-shot tasks.

## When to Use

- User explicitly names an agent ("use Claude Code", "run Codex", "try OpenCode")
- You need an external AI to implement, refactor, or review code
- You want parallel task execution in isolated worktrees
- Long-running coding sessions with progress checks

## Shared Patterns (All Agents)

### Git Repository Required

All three agents refuse to run outside a git repo. For scratch work:

```bash
cd $(mktemp -d) && git init
```

### PTY for Interactive Mode

All interactive coding agent TUIs require `pty=true`:

```bash
terminal(command="<agent>", background=true, pty=true)
```

### One-Shot (Non-Interactive) Mode

All three support a one-shot command for bounded tasks:

```bash
terminal(command="<agent> <command> '<task description>'", timeout=120)
```

### Background for Long Tasks

Start in background, monitor with `process`:

```bash
terminal(command="<agent> ...", background=true, pty=true, notify_on_complete=true)
process(action="poll", session_id="<id>")
```

### Parallel Issue Fixing with Worktrees

```bash
git worktree add -b fix/issue-78 /tmp/issue-78 main
terminal(command="<agent> ...", workdir="/tmp/issue-78", background=true, pty=true)
```

---

## Section 1: Claude Code (Anthropic)

### Prerequisites

```bash
npm install -g @anthropic-ai/claude-code
claude auth login              # browser OAuth
# or: claude auth login --console  # API key billing
# or: claude auth login --sso      # Enterprise
claude --version               # needs v2.x+
```

### Print Mode (Preferred — Simple Tasks)

Non-interactive, exits when done. No PTY needed.

```bash
claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10
```

**Key flags:**
- `-p "query"` — one-shot, non-interactive
- `--max-turns <N>` — cap agentic loops
- `--allowedTools 'Read,Edit'` — restrict capabilities
- `--output-format json` — structured output
- `--model haiku` — cheaper model
- `--max-budget-usd <N>` — cost cap
- `--fallback-model haiku` — auto-fallback on overload

**Piped input:**
```bash
cat src/auth.py | claude -p 'Review this code for bugs' --max-turns 1
git diff main...HEAD | claude -p 'Summarize these changes' --max-turns 1
```

### Interactive Mode (Multi-Turn)

Requires tmux orchestration:

```bash
tmux new-session -d -s claude-work -x 140 -y 40
tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter

# Handle workspace trust dialog
sleep 5 && tmux send-keys -t claude-work Enter
# Handle permissions dialog (if --dangerously-skip-permissions)
sleep 3 && tmux send-keys -t claude-work Down && sleep 0.3 && tmux send-keys -t claude-work Enter

# Send task
tmux send-keys -t claude-work 'Refactor the auth module to use JWT tokens' Enter

# Monitor
sleep 15 && tmux capture-pane -t claude-work -p -S -50

# Exit
tmux send-keys -t claude-work '/exit' Enter
```

### PR Review

```bash
# Quick (print mode)
git diff main...feature | claude -p 'Review this diff for bugs and security issues.' --max-turns 1

# Deep (interactive + worktree)
claude -w pr-review --tmux  # creates isolated worktree
```

### Parallel Claude Instances

```bash
tmux new-session -d -s task1 -x 140 -y 40
tmux send-keys -t task1 'cd ~/project && claude -p "Fix the auth bug" --allowedTools "Read,Edit" --max-turns 10' Enter
tmux new-session -d -s task2 -x 140 -y 40
tmux send-keys -t task2 'cd ~/project && claude -p "Write API integration tests" --allowedTools "Read,Write,Bash" --max-turns 15' Enter
```

### Useful Slash Commands (Interactive Mode)

| Command | Purpose |
|---------|---------|
| `/compact` | Compress context to save tokens |
| `/review` | Request code review |
| `/plan` | Enter plan mode |
| `/model` | Switch models mid-session |
| `/effort` | Set reasoning effort |
| `/init` | Create CLAUDE.md |
| `/exit` | End session |

### Settings & Memory

Hierarchy: CLI flags > `.claude/settings.local.json` (personal) > `.claude/settings.json` (project-shared) > `~/.claude/settings.json` (global).

Memory: `CLAUDE.md` (git-tracked) or `.claude/rules/*.md` (modular rules directory).

### Pitfalls

- Print mode (`-p`) skips all dialogs — best for automation
- `--dangerously-skip-permissions` dialog defaults to "No, exit" — must send Down then Enter
- Interactive mode REQUIRES tmux for Hermes orchestration
- Context degradation above 70% — use `/compact` proactively
- `--bare` skips OAuth — requires `ANTHROPIC_API_KEY`

---

## Section 2: Codex (OpenAI)

### Prerequisites

```bash
npm install -g @openai/codex
# Auth: either OPENAI_API_KEY or Codex CLI OAuth session
```

### One-Shot Tasks

```bash
codex exec 'Add dark mode toggle to settings'
codex exec --full-auto 'Refactor the auth module'
```

### Background Mode

```bash
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
process(action="poll", session_id="<id>")
process(action="submit", session_id="<id>", data="yes")
```

### Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--full-auto` | Sandboxed, auto-approves file changes |
| `--yolo` | No sandbox, no approvals (fastest) |
| `--sandbox danger-full-access` | Bypasses bubblewrap for gateway contexts |

### Hermes Gateway Caveat

Codex `workspace-write` sandboxing may fail in gateway contexts. When it does:

```bash
codex exec --sandbox danger-full-access "<task>"
```

Use process boundaries as the safety layer instead.

### PR Reviews

```bash
REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main
```

### Parallel Issue Fixing

```bash
git worktree add -b fix/issue-78 /tmp/issue-78 main
codex --yolo exec 'Fix issue #78: ...' &  # in separate terminal calls
```

### Pitfalls

- **Must run in a git repo** — Codex refuses otherwise
- **Always use `pty=true`** — hangs without PTY
- Path mismatch can select the wrong binary: `which -a codex`
- Codex sandbox uses bubblewrap which may fail in some environments

---

## Section 3: OpenCode (Open-Source, Provider-Agnostic)

### Prerequisites

```bash
npm install -g opencode-ai@latest
# or: brew install anomalyco/tap/opencode
opencode auth login
opencode auth list   # should show >= 1 provider
```

### One-Shot Tasks

```bash
opencode run 'Add retry logic to API calls and update tests'
opencode run 'Review this config for security issues' -f config.yaml -f .env.example
opencode run 'Refactor auth module' --model openrouter/anthropic/claude-sonnet-4
opencode run 'Debug why tests fail in CI' --thinking
```

### Interactive Mode

```bash
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow")
process(action="poll", session_id="<id>")
```

**IMPORTANT:** Do NOT use `/exit` — it opens an agent selector. Use `Ctrl+C` (`\x03`) or `process(action="kill")`.

### TUI Keybindings

| Key | Action |
|-----|--------|
| Enter | Submit message (press twice if needed) |
| Tab | Switch between agents |
| Ctrl+P | Open command palette |
| Ctrl+C | Exit OpenCode |

### PR Review

```bash
opencode pr 42
```

### Session Management

```bash
opencode session list
opencode stats --days 7 --models anthropic/claude-sonnet-4
opencode -c                    # continue last session
opencode -s ses_abc123         # specific session resume
```

### Common Flags

| Flag | Use |
|------|-----|
| `run 'prompt'` | One-shot execution and exit |
| `-c` / `--continue` | Continue last session |
| `-s <id>` | Continue a specific session |
| `--model provider/model` | Force specific model |
| `-f <path>` | Attach file(s) to message |
| `--thinking` | Show model thinking blocks |
| `--variant <level>` | Reasoning effort (high, max, minimal) |

### Pitfalls

- `opencode run` does NOT need pty — only interactive TUI does
- `/exit` is NOT a valid command — use Ctrl+C
- PATH mismatch can select wrong binary
- Enter may need to be pressed twice in TUI

---

## Quick Decision Table

| Task type | Best agent | Mode | Why |
|-----------|-----------|------|-----|
| One-shot code fix | Claude Code | `-p` | Clean output, no dialog handling |
| Multi-turn refactor | Claude Code | Interactive + tmux | Rich slash commands, context management |
| Batch issue fixing | Codex + worktrees | `--yolo` exec | Fast sandboxed execution |
| PR review | OpenCode | `pr <N>` | Built-in PR command |
| Provider-agnostic task | OpenCode | `run` | Works with any provider |
| Simple code generation | Any | One-shot | Fastest path |
| Security audit | Claude Code | `--allowedTools Read` | Read-only by default |

## Verification

Smoke test agent readiness:

```bash
# Claude Code
claude -p "Respond with: CLAUDE_OK" --max-turns 1

# Codex
codex exec "echo CODEX_OK"

# OpenCode
opencode run "Respond with exactly: OPENCODE_OK"
```