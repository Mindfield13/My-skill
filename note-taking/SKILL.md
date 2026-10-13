---
name: note-taking
description: "Read, create, edit, and search notes in Notion (via API + ntn CLI) and Obsidian vaults (filesystem-first)"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [notes, notion, obsidian, markdown, productivity, writing]
---

# Note-Taking

Manage notes across two systems: **Notion** (online, API-based) and **Obsidian** (local filesystem vault).

---

## Section 1: Notion

Talk to Notion two ways. Same integration token works for both.

### Setup

1. Create integration at https://notion.so/my-integrations
2. Copy API key (`ntn_` or `secret_`)
3. Store in `~/.hermes/.env`: `NOTION_API_KEY=ntn_your_key_here`
4. Share target pages/databases with the integration

### Path A: `ntn` CLI (preferred, macOS/Linux)

```bash
curl -fsSL https://ntn.dev | bash
export NOTION_API_TOKEN=$NOTION_API_KEY
export NOTION_KEYRING=0

# Read page as Markdown
ntn api v1/pages/{page_id}/markdown

# Search
ntn api v1/search query="page title"

# Create page from Markdown
ntn api v1/pages parent[page_id]=xxx properties[title][0][text][content]="Notes" markdown="# Agenda\n\n- Item"

# Patch with Markdown
ntn api v1/pages/{page_id}/markdown -X PATCH markdown="## Update\n\nShipped."

# Query database
ntn api v1/data_sources/{id}/query -X POST filter[property]=Status filter[select][equals]=Active

# File upload (one-liner)
ntn files create < photo.png
```

### Path B: HTTP + curl (cross-platform, default on Windows)

```bash
# Read page as Markdown
curl -s "https://api.notion.com/v1/pages/{id}/markdown" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"

# Create page
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"parent": {"page_id": "xxx"}, "properties": {"title": [{"text": {"content": "Title"}}]}, "markdown": "# Content"}'

# Query database
curl -s -X POST "https://api.notion.com/v1/data_sources/{id}/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"property": "Status", "select": {"equals": "Active"}}}'
```

### Property Types

| Type | JSON |
|------|------|
| Title | `{"title": [{"text": {"content": "..."}}]}` |
| Rich text | `{"rich_text": [{"text": {"content": "..."}}]}` |
| Select | `{"select": {"name": "Option"}}` |
| Multi-select | `{"multi_select": [{"name": "A"}]}` |
| Date | `{"date": {"start": "2026-01-15"}}` |
| Checkbox | `{"checkbox": true}` |

### Notion Workers (advanced, macOS/Linux only)

```bash
ntn workers new my-worker    # scaffold
cd my-worker && ntn workers deploy --name my-worker
```

---

## Section 2: Obsidian Vault (Filesystem-First)

Use file tools to read, search, create, and edit notes in an Obsidian vault.

### Vault Path

Resolve via `OBSIDIAN_VAULT_PATH` env var, or fall back to `~/Documents/Obsidian Vault`.

**Important:** Always resolve the vault path to an absolute path before using file tools. Do not pass `$OBSIDIAN_VAULT_PATH` variables to file tool commands.

### Read a Note

```bash
read_file(path="~/Documents/Obsidian Vault/My Note.md")
```

### List Notes

```bash
search_files(pattern="*.md", target="files", path="/path/to/vault")
```

### Search Notes Content

```bash
search_files(pattern="keyword", target="content", path="/path/to/vault", file_glob="*.md")
```

### Create a Note

```bash
write_file(path="/path/to/vault/New Note.md", content="# Title\n\nContent...")
```

### Append to a Note

Use `read_file` + `patch` (anchored append) or `write_file` (full rewrite).

### Targeted Edits

Use `patch` with stable context surrounding the change.

### Wikilinks

Obsidian links: `[[Note Name]]` syntax. Use these when creating notes to link related content.