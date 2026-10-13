# CSS Override: Porting a Tailwind CSS SPA into a WebContentsView Shell

When a third-party SPA (React/Vue, built with Tailwind CSS, served by a Python/FastAPI backend) is embedded via WebContentsView, its visual design must be overridden to match the host Shell's Apple design language — without modifying the SPA's source code.

The host Shell (Trigon Agent) injects CSS via `webContents.insertCSS()` on `dom-ready`, and the preload script applies `data-theme="light"|"dark"` on `<html>` based on the user's theme setting.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  BrowserWindow (shell chrome)                   │
│  ┌─ 31px titlebar ───────────────────────────┐  │
│  │  🟡🟡🟡  Trigon Agent  │  Modex-MH-Agent  │  │
│  ├─ 74px icon nav ──┬─ WebContentsView ──────┤  │
│  │  📐  📄  ⚙️      │   SPA (React/Tailwind)  │  │
│  │                   │   served by FastAPI     │  │
│  │                   │   on localhost:18088    │  │
│  └───────────────────┴─────────────────────────┘  │
│  Inject: tokens.css + glass-app.css + modex-theme.css  │
│  (via wc.insertCSS() on dom-ready)               │
└─────────────────────────────────────────────────┘
```

## Override Strategy

### 1. CSS Custom Properties (highest leverage)

The SPA uses CSS variables like `--text-primary`, `--bg-card`, `--accent`, `--border`. Override them per theme:

```css
html[data-theme="light"] {
  --text-primary: #1D1D1F !important;
  --text-secondary: #6E6E73 !important;
  --bg-card: rgba(255, 255, 255, 0.62) !important;
  --border: rgba(0, 0, 0, 0.08) !important;
  --accent: #0A84FF !important;
}
html[data-theme="dark"] {
  --text-primary: #F5F5F7 !important;
  --text-secondary: #A1A1A6 !important;
  --bg-card: rgba(40, 40, 43, 0.66) !important;
  --border: rgba(255, 255, 255, 0.10) !important;
  --accent: #0A84FF !important;
}
```

**Key**: Trigon's preload applies `data-theme="light"` or `data-theme="dark"` on `<html>`. The override CSS targets `html[data-theme="light"]` and `html[data-theme="dark"]` to swap all tokens per theme.

### 2. Override Tailwind Utility Classes

Tailwind CSS v4 generates utility classes like `bg-indigo-500`, `text-indigo-400`, `border-indigo-500/20`. Override them to use the host accent color:

```css
.bg-indigo-500,
[class*="bg-indigo-500"] {
  background-color: var(--accent) !important;
}
.text-indigo-400,
[class*="text-indigo-400"] {
  color: var(--accent) !important;
}
.hover\:border-indigo-500\/40:hover {
  border-color: var(--accent-light) !important;
}
```

**Pattern**: Use `[class*="..."]` attribute selectors to catch Tailwind's arbitrary-value variants (`bg-indigo-500/[0.04]`, `hover:border-indigo-500/40`).

### 3. Glass Effect on Cards

The SPA uses `.card` class for panels. Override with the host's glass effect:

```css
.card, .glass-card {
  background: var(--glass, var(--bg-card)) !important;
  -webkit-backdrop-filter: blur(34px) saturate(210%) !important;
  backdrop-filter: blur(34px) saturate(210%) !important;
  border: 1px solid var(--border) !important;
  border-top-color: var(--highlight, rgba(255,255,255,0.12)) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow) !important;
}
```

### 4. Component Overrides

| SPA Element | Override |
|---|---|
| Buttons | `button:active { transform: scale(0.97) }` — Apple spring animation |
| Primary buttons (`bg-indigo-500`) | Transparent border, white text, `--accent` background |
| Ghost buttons (`btn-ghost`, `border-dashed`) | Transparent bg, `--border` color, `--hover` on hover |
| Inputs (`.input`, textarea, select) | `appearance: none`, `--glass-weak` bg, `--accent` focus ring |
| Scrollbar | Thin (10px), `--text-muted` thumb, `--border-radius: 5px`, transparent track |
| Toggle switches | Override `bg-indigo-500` → `--accent` |
| Dividers (`border-t`, `border-b`) | `--border` color |
| Upload zones (`border-dashed`) | `--border` normal, `--accent` on hover |
| Code blocks | Monospace font family override |
| Log streams | Monospace, 12px, transparent bg |

### 5. Segmented Control (Apple Style)

```css
.segmented-control, [role="tablist"] {
  display: inline-flex;
  background: var(--glass-weak);
  border: 1px solid var(--border);
  border-radius: 980px;
  padding: 3px;
  gap: 2px;
}
.segmented-control button.active,
[role="tab"][aria-selected="true"] {
  background: var(--glass-strong);
  box-shadow: 0 1px 6px rgba(0,0,0,0.16);
}
```

### 6. Font Family Override

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
    "PingFang SC", "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased !important;
  letter-spacing: -0.011em !important;
}
```

## Tailwind CSS Arbitrary Value Selectors

Tailwind v4 generates class names with escaped characters. Override them with:

```css
/* Match `bg-indigo-500/[0.04]` */
.bg-indigo-500\/\[0\.04\],
[class*="bg-indigo-500"] {
  background-color: var(--accent-light) !important;
}

/* Match `hover:border-indigo-500/40` */
.hover\:border-indigo-500\/40:hover {
  border-color: var(--accent-light) !important;
}

/* Match `hover:text-[#f87171]` (danger hover) */
.hover\:text-\[\#f87171\]:hover {
  color: var(--danger) !important;
}
```

## Loading Screen (Pre-Navigation)

The SPA loads from a backend URL, so there's a loading screen shown first. Style it with the host's design tokens inline:

```css
body {
  display: flex; align-items: center; justify-content: center;
  background: var(--scrim);
  font-family: var(--font);
}
#loading {
  background: var(--glass);
  backdrop-filter: blur(34px) saturate(210%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  padding: 48px 56px;
}
```

## Injection Points

1. **`appManager.js`** — `wc.on('dom-ready', () => { injectThemeCss(wc, app); })` which calls `wc.insertCSS(tokens.css)`, `wc.insertCSS(glass-app.css)`, and for modex specifically `wc.insertCSS(modex-theme.css)`.
2. **Preload script** — `injectBase()` adds `trigon-app` and `trigon-wall` classes to `<body>`, and `applyThemeAttrs()` sets `data-theme` on `<html>`.
3. **Theme broadcast** — On theme change, ipcRenderer sends `trigon:theme` event → preload updates `data-theme` attribute → CSS overrides apply immediately.

## Verification

After changes, verify by:
1. Switching the host app's theme (light ↔ dark) — the embedded SPA should follow
2. Checking glass effect on cards (backdrop-filter blur on transparent backgrounds)
3. Checking accent color (#0A84FF) replaces all indigo/purple elements
4. Checking scrollbar style, font family, input focus ring
5. Checking reduce-motion: `prefers-reduced-motion: reduce` media query