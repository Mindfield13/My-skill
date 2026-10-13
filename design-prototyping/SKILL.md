---
name: design-prototyping
description: "Web design prototyping — from-scratch designed HTML artifacts (landings, prototypes, decks) and throwaway mockup variants for design exploration"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [design, html, prototype, ux, ui, mockup, variants, exploration, wireframe]
---

# Design Prototyping

Design and prototype web interfaces as HTML artifacts. Two modes: **polished one-off design** (claude-design) and **throwaway sketch variants** (sketch) for design exploration.

---

## Section 1: Polished HTML Design (claude-design)

Use for from-scratch designed artifacts: landing pages, prototypes, decks, component labs, motion studies. Produces one polished HTML file.

### When to Use

- Landing pages, teaser pages, high-fidelity prototypes
- Interactive product mockups, visual option boards
- HTML slide decks, motion studies, component explorations
- Dashboard concepts, onboarding flows, settings pages

### Core Workflow

1. **Understand the brief** — What's being designed? Who's it for? What artifact should exist?
2. **Gather context** — Read supplied docs, screenshots, repo files; identify visual vocabulary
3. **Define the design system for this artifact** — colors, type, spacing, radii, shadows, motion
4. **Choose format** — static HTML canvas for comparison, clickable prototype, slide deck, etc.
5. **Build the artifact** — single self-contained HTML file, embed CSS/JS, avoid remote deps
6. **Verify** — file exists, syntax clean; if browser tools available, check console errors
7. **Report** — file path, what was created, caveats, next steps

### Design Principles

- **Start from context, not vibes** — look for brand docs, screenshots, repo components, tokens
- **Ask questions** — keep them short, skip obvious defaults
- **3-variation default**: Conservative, Strong-fit, Divergent
- **Anti-slop**: No aggressive gradients, glassmorphism defaults, emoji, fake dashboards, stock photos
- **Use modern CSS**: CSS variables, grid, container queries, `text-wrap: pretty`, responsive
- **Use React from CDN only** when meaningful state/interaction complexity warrants it
- **Content discipline**: No fake metrics, decorative stats, or generic feature grids

### Deck Rules

- Fixed 1920×1080 canvas scaled to viewport
- Keyboard navigation, visible slide count, localStorage persistence
- 1-2 background colors max

### Anti-patterns to Avoid

- Generic SaaS cards with icons everywhere
- Rainbow palettes
- Filler content
- Making every section the same card grid
- Aggressive gradient backgrounds by default

### Related Skills

- **`popular-web-designs`** — 54 real design systems (Stripe, Linear, Vercel) as templates
- **`design-md`** — for authoring formal DESIGN.md token spec files

---

## Section 2: Throwaway Mockup Variants (sketch)

Use when the user wants to **see a design direction before committing** — 2-3 disposable HTML variants to compare.

### When to Use

- "sketch this screen", "show me what X could look like"
- "compare layout A vs B", "give me 2-3 takes on this UI"
- "mockup this before I build"

### Core Method

```
intake → variants → head-to-head → pick winner (or iterate)
```

### 1. Intake

Get three things (one at a time):
1. **Feel** — "What should this feel like?"
2. **References** — "What apps/products capture that feel?"
3. **Core action** — "What's the single most important thing a user does?"

### 2. Variants (2-3, never 1, rarely 4+)

Each variant is a complete standalone HTML file with a different **design stance**:

- **Density:** compact / airy / ultra-dense
- **Emphasis:** content-first / action-first / tool-first
- **Aesthetic:** editorial / utilitarian / playful
- **Layout:** single-column / sidebar / split-pane

Name by stance: `001-calm-editorial/`, `002-utilitarian-dense/`

### 3. Make Them Real

- Single HTML file per variant
- Inline `<style>` or Tailwind CDN
- Realistic fake content, not lorem ipsum
- **Interactive**: hovers, clicks, state transitions
- **Verify visually** with `browser_navigate` + `browser_vision`

Default CSS reset + system font stack:
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ...; }
```

### 4. Head-to-Head Comparison

Present a comparison table with opinionation:

| Dimension | Calm editorial | Utilitarian dense |
|-----------|----------------|-------------------|
| Density | Low | High |
| Scan-ability | High | Medium |
| Feel | Calm, trusted | Sharp, tool-like |

**Give your take** — which is strongest and why.

### Interactivity Bar

Minimum: click a primary action → visible state change; one meaningful state transition; hover affordances.

### Structure

```
sketches/
├── 001-calm-editorial/
│   ├── index.html
│   └── README.md
└── 002-utilitarian-dense/
    ├── index.html
    └── README.md
```

### Frontier Mode (what to sketch next)

- Consistency gaps between sketches
- Unsketched screens
- State coverage (empty, loading, error, 1000-items)
- Responsive gaps (mobile, ultrawide)
- Interaction patterns (transitions, drag, scroll)