# Segmented Control CSS Pattern (Apple Style)

When a three-way option group (浅色/深色/跟随系统, or any group with different text lengths) uses `flex: 1` pill buttons with `gap`, the visual spacing becomes uneven — short items look cramped, long items dominate. The fix is Apple's **segmented control** pattern.

## Pattern

```css
/* Track (shared container) */
.theme-options {
  display: flex;
  gap: 0;                              /* ← NO gap between segments */
  padding: 3px;
  background: var(--input-bg);         /* track background */
  border: 1px solid var(--border);
  border-radius: 10px;                 /* single rounded container */
}

/* Segment (each button) */
.theme-option {
  flex: 1;                             /* equal width regardless of text length */
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;                            /* icon-text gap — 5px was too tight, user complained */
  padding: 6px 8px;                    /* 6px top/bottom, 8px left/right */
  border: none;
  border-radius: 7px;
  font-size: 12px;
  color: var(--text-sub);
  background: transparent;             /* transparent when not selected */
  transition: background 0.15s, color 0.15s, transform 0.1s;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}

.theme-option:hover { color: var(--accent); }
.theme-option:active { transform: scale(0.97); }
.theme-option svg { width: 14px; height: 14px; flex-shrink: 0; }

/* Selected segment "floats" above the track */
.theme-option:has(input:checked) {
  background: var(--bg);
  color: var(--accent);
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.theme-option input { display: none; }

/* Dark mode: deeper shadow on selected segment */
html.theme-dark .theme-option:has(input:checked) {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}
```

## Why it works

| Problem | Cause | Fix |
|---------|-------|-----|
| Uneven spacing | Different text lengths + `gap` + individual borders → gaps look uneven | `gap: 0` track + transparent segments |
| Cramped icon-text | `gap: 5px` or less makes icon touch text | `gap: 6px` minimum |
| No breathing room | `padding: 6px 4px` is too tight for label buttons | `padding: 6px 8px` |
| No hierarchy | Each button looks like a separate element | Shared track background + floating selected state |

## When to use

- Any equal-width option group (3-4 options)
- Options with different text lengths
- Icon+label buttons where the icon and label should feel like one unit

## When NOT to use

- 2-option toggles (use a switch instead)
- Dropdown menus or action sheets
- Options that need individual visual weight (danger/primary distinction)