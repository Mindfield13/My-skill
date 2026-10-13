---
name: content-monitoring
description: "Monitor and extract content from blogs (RSS/Atom feeds) and YouTube (transcripts, summaries, threads)"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [RSS, blogs, youtube, transcripts, monitoring, feeds, content, summary]
---

# Content Monitoring & Extraction

Track and transform online content. Two integrations: **blog/RSS feed monitoring** and **YouTube transcript extraction**.

---

## Section 1: Blog & RSS Feed Monitoring (blogwatcher-cli)

Track blog and RSS/Atom feed updates. Supports automatic feed discovery, HTML scraping fallback, OPML import, and read/unread management.

### Installation

```bash
# Go
go install github.com/JulienTant/blogwatcher-cli/cmd/blogwatcher-cli@latest
# Binary
curl -sL https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_linux_amd64.tar.gz | tar xz -C /usr/local/bin blogwatcher-cli
```

### Managing Blogs

```bash
blogwatcher-cli add "My Blog" https://example.com
blogwatcher-cli add "Blog" https://example.com --feed-url https://example.com/feed.xml
blogwatcher-cli import subscriptions.opml
blogwatcher-cli blogs
blogwatcher-cli remove "My Blog" --yes
```

### Scanning & Reading

```bash
blogwatcher-cli scan                 # scan all
blogwatcher-cli articles             # list unread
blogwatcher-cli read 1               # mark read
blogwatcher-cli read-all             # mark all read
blogwatcher-cli articles --blog "My Blog" --all
```

### Environment Variables

`BLOGWATCHER_DB` (path to SQLite db), `BLOGWATCHER_WORKERS` (default 8), `BLOGWATCHER_SILENT`, `BLOGWATCHER_YES`

---

## Section 2: YouTube Content (Transcript Extraction)

Extract transcripts from YouTube videos and convert into structured formats.

### Setup

```bash
pip install youtube-transcript-api
```

### Fetch Transcript

```bash
python3 scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"
python3 scripts/fetch_transcript.py "URL" --text-only
python3 scripts/fetch_transcript.py "URL" --timestamps
python3 scripts/fetch_transcript.py "URL" --language tr,en
```

### Output Formats

- **Chapters**: Group by topic shifts, timestamped chapter list
- **Summary**: 5-10 sentence overview
- **Chapter summaries**: Chapters with paragraph summaries
- **Thread**: Twitter/X thread format
- **Blog post**: Full article with sections
- **Quotes**: Notable quotes with timestamps

### Chunking

If transcript exceeds ~50K characters, split into overlapping ~40K chunks with 2K overlap, summarize each, then merge.

### Error Handling

- Transcript disabled → tell user
- Private video → relay error
- No matching language → retry without `--language` to find any available
- Missing dep → `pip install youtube-transcript-api`