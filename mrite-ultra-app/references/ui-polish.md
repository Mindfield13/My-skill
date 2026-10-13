# M Ultra UI 打磨记录（2026-08-17）

## 1. 设置页协议分段控制器不可点击

### 症状
点击 Anthropic / OpenAI 兼容 按钮无反应，无法切换协议。

### 根因
分段控制器按钮只有静态 `active` 类渲染，没有绑定 click 事件来切换。

### 修复
```js
// 在 settings.js 渲染后添加
content.querySelectorAll('#set-protocol .seg-item').forEach((btn) => {
  btn.addEventListener('click', () => {
    content.querySelectorAll('#set-protocol .seg-item').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
  });
});
```

## 2. 写作/任务面板缩放不一致

### 症状
写作面板和任务详情面板的缩放比例不同，切换时视觉跳跃。

### 根因
两个面板的 `panel-inner` 都有不同的内联 `max-width`：
- 任务面板：`style="max-width:1100px"` 
- 写作面板：`style="max-width:1100px"`
- 而普通面板用 CSS 的 `max-width: 1180px`

### 修复
去除所有内联 `max-width`，统一用 CSS：
```css
.panel-inner { max-width: 1200px; margin: 0 auto; min-width: 0; }
```

## 3. 响应式布局（窗口缩放适配）

### 方案
在 CSS 中添加媒体查询断点，处理窄窗口场景：

```css
@media (max-width: 1000px) {
  .panel { padding: 16px; }
  .panel-inner { max-width: 100%; }
  .detail-grid { grid-template-columns: 1fr !important; }  /* 左右分栏变单栏 */
  .grid-2 { grid-template-columns: 1fr !important; }
  .form-row { flex-direction: column; }
}
@media (max-width: 700px) {
  .app-main { padding: 12px; }
  .panel { padding: 12px; }
}
```

## 4. 步骤时间线 CSS 美化

### 结构
```html
<div class="step-list">
  <div class="step-row">
    <div class="step-circle done">✓</div>
    <div class="step-body">
      <div class="step-name">...</div>
      <div class="step-desc">...</div>
    </div>
  </div>
</div>
```

### 连接线
`.step-row:not(:last-child)::before` 伪元素画竖线连接各步骤。

### 呼吸动画
```css
@keyframes stepPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(0,122,255,0.3); transform: scale(1); }
  50% { box-shadow: 0 0 18px rgba(0,122,255,0.6); transform: scale(1.05); }
}
```

## 5. 写作面板编译反馈

### 状态流转
1. 点击编译 → 按钮变 `⏳ 编译中…`，日志框显示"正在编译，请稍候…"
2. 成功 → 按钮变 `✅ 编译成功`，启用 PDF 按钮
3. 失败 → 按钮变 `❌ 重试编译`（3 秒后恢复为"编译论文"）
4. 异常 → 按钮变 `❌ 编译出错`