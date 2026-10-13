# CSS 布局调试：inline-style 覆盖模式

## 问题场景

修改页/文件页的右侧面板中，预览区被固定高度挤压，底部大片空白浪费。

### 根因链

1. **JS 中设置了 inline style**: `#md-preview` 的 `max-height:300px`、`#md-filetree` 的 `max-height:200px`
2. **CSS class 也有限制**: `.log-box` 类自带 `max-height: 320px`
3. **CSS 规则无法覆盖 inline style**: 普通 CSS 选择器（如 `.md-right #md-preview`）的优先级低于 inline style → 写 `max-height: 35%` 无效
4. **flex 布局中的百分比失效**: `max-height: 35%` 在 flex column 中可能不按预期生效（flex item 的百分比高度取决于父容器的高度上下文）

### 修复步骤

```
1. 识别所有限制源：JS inline style → CSS class → CSS ID
2. 用 `!important` 覆盖 inline style：`max-height: none !important`
3. 用固定值替代百分比：`max-height: 150px !important` 而非 `max-height: 35%`
4. 确保 flex 父容器有明确高度：`.md-right { height: 100%; }`
```

### 检查清单

| 源 | 问题 | 修复 |
|----|------|------|
| JS inline `#md-filetree` | `max-height:200px` | CSS `max-height:150px !important` |
| JS inline `#md-preview` | `max-height:300px` | CSS `max-height:none !important; flex:1` |
| CSS class `.log-box` | `max-height:320px` | CSS `#md-preview` 选择器凭借 `!important` 覆盖 |
| flex 父容器 `.md-right` | 无明确高度 | CSS `height:100%` |

### 避免模式

- 不要在 JS 中写 layout 相关的 inline style（`max-height`、`height`、`width`）
- 如果必须 inline，在 CSS 中用 `!important` 标记预期值
- flex 布局中，百分比 `max-height` 不可靠 → 用固定像素值或 `flex: 1`