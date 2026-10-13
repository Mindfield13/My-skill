# 图标/文字垂直对齐修复（SVG baseline 问题）

设置面板 / 工具栏中图标（SVG）与文字垂直错位是 Electron 应用常见问题。根源：SVG 默认 `display: inline`，按文字基线对齐而非容器居中，导致"图标偏上 1-3px、文字偏下"。

## 修复方案

```css
/* 1. 按钮容器必须用 flex */
.btn-ghost {
  display: inline-flex;    /* ← 关键：缺少这个，图标按 inline 基线对齐 */
  align-items: center;
  gap: 6px;
  line-height: 1;          /* 防止父容器 line-height（如 body 1.5）撑开 */
}

/* 2. SVG 图标块级化，防止基线干扰 */
.btn-ghost svg,
.theme-option svg,
.env-title svg,
.modal-header h2 svg {
  display: block;           /* 覆盖 inline 默认值 */
  flex-shrink: 0;           /* 防止被压缩 */
}

/* 3. 状态圆点（●） */
.env-dot {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: middle;   /* 与文字基线对齐兜底 */
}

/* 4. 全局兜底规则（防遗漏） */
button svg, [class*="icon"] svg, svg.icon {
  display: block;
  flex-shrink: 0;
}
```

## 常见遗漏点

| 症状 | 根因 | 修复 |
|------|------|------|
| 扳手/齿轮图标与文字错位 | `.btn-ghost` 缺 `display: inline-flex` | 补 flex + align-items: center |
| 状态圆点偏上 | `.env-dot` 缺 `vertical-align: middle` | 补 vertical-align + flex-shrink |
| 所有 SVG 普通偏移 1-3px | SVG 默认 `display: inline` 基线对齐 | `display: block` |
| 间距被撑大 | 父容器 line-height 1.5 影响 | 容器 `line-height: 1` 或 `1.2` |

## 排查顺序

1. 先加全局兜底 `button svg { display: block; flex-shrink: 0 }`（一轮修复大部分）
2. 逐个检查带图标的按钮类是否 `display: inline-flex; align-items: center`
3. 检查 flex 容器内联元素（span 圆点、i 图标）的 `vertical-align`
4. 通过截图（vision_analyze）确认视觉结果，而非只看代码