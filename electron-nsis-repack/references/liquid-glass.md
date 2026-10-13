# Apple Liquid Glass — macOS Sequoia 风格液态玻璃

升级普通 `backdrop-filter: blur()` 毛玻璃为 Apple 风格"液态玻璃"——使用 `blur(20px) saturate(180%)` 配合多层阴影、高光边缘和细腻过渡，模拟透过一块打磨光滑的水晶看后面的效果。

## 核心——纯 backdrop-filter（推荐方案）

**最终方案：** 纯 `backdrop-filter: blur(20px) saturate(180%)`，**不依赖 SVG 滤镜**。Electron Chromium 对 `url(#filter)` 在 `backdrop-filter` 中的支持不稳定，折射效果不可见，最终统一使用标准 blur+saturate。SVG 滤镜定义可以保留在 HTML 中无害，但 CSS 中不要引用它。

## 推荐 CSS 值

```css
.liquid-glass {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow:
    0 8px 32px 0 rgba(0, 0, 0, 0.3),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
```

## 各组件细化值

| 组件 | blur | background (light) | 特殊 |
|------|------|-------------------|------|
| 侧边栏 | 20px | rgba(255,255,255,0.65) | `border-right: none`，`box-shadow: 4px 0 24px rgba(0,0,0,0.06)` 阴影分隔 |
| 弹窗 | 40px | rgba(255,255,255,0.65) | `0 24px 64px 0 rgba(0,0,0,0.4)` 强阴影 |
| 卡片 | 20px | rgba(255,255,255,0.65) | 圆角 14px |
| 按钮 | 8px | rgba(255,255,255,0.80) | `active: scale(0.98)` |
| 输入框 | 8px | rgba(255,255,255,0.50) | focus: `rgba(255,255,255,0.4)` 边框 + `0 0 0 4px rgba(255,255,255,0.1)` |
| 遮罩层 | 5px | rgba(0,0,0,0.4) | |
| Toast | 16px | rgba(20,20,30,0.65) | `z-index: 9999`, `pointer-events: none` |

## 过渡与动画

全部使用 Apple 标准曲线：
```css
--ease-smooth: cubic-bezier(0.25, 0.8, 0.25, 1);
```
- 按钮 hover: `0.3s ease-smooth`
- 按钮 active: `scale(0.98)` — 细腻回弹
- 面板 hover: `translateY(-1px)` + 增强阴影
- 弹窗入场: 0.35s spring curve

## 顶部栏光泽线

使用 `::after` 伪元素替代 `border-bottom`：
```css
.view-header::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent);
}
```

## 侧边栏分隔

使用阴影替代硬边框：
```css
.sidebar {
  border-right: none;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.06);
}
```

## Tab 选中态

使用 `rgba(255,255,255,0.15)` + 内发光，而非纯白填充：
```css
.mode-tab.active {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px) saturate(180%);
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.4);
}
```

## 暗色模式

```css
html.theme-dark .liquid-glass {
  background: rgba(30, 30, 30, 0.65);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.15);
}
```

## 背景要求

必须给 body 加渐变背景 + 装饰性浮动光斑（让毛玻璃\有内容可透）：

```css
body {
  background: linear-gradient(135deg, #e8edf5 0%, #dce3f0 30%, #e6ddf0 60%, #dde8f2 100%);
}
body::before {
  content: '';
  position: fixed; top: -15%; right: -8%;
  width: 550px; height: 550px;
  background: radial-gradient(circle, rgba(120,140,255,0.18), transparent 70%);
  border-radius: 50%; z-index: -1;
  animation: float 12s ease-in-out infinite;
}
body::after {
  content: '';
  position: fixed; bottom: -10%; left: -5%;
  width: 450px; height: 450px;
  background: radial-gradient(circle, rgba(220,160,255,0.14), transparent 70%);
  border-radius: 50%; z-index: -1;
  animation: float 15s ease-in-out infinite reverse;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -20px); }
}
```

## 技术支持

- `backdrop-filter` 需要 `-webkit-` 前缀：Electron 使用 Chromium 内核，兼容性良好
- 避免超过 3 层嵌套 `backdrop-filter`（性能）
- 浮动光斑动画使用 `transform` 而非 `top/left`（触发合成层）

## 原理

```svg
<filter id="liquid-glass" x="-20%" y="-20%" width="140%" height="140%">
  <!-- 1. 微模糊源图 -->
  <feGaussianBlur in="SourceGraphic" stdDeviation="0.5" result="blur"/>
  <!-- 2. 从 Alpha 通道生成位移图（边缘强、中心弱） -->
  <feComponentTransfer in="SourceAlpha" result="alpha">
    <feFuncA type="table" tableValues="0 0 0.3 0.8 1"/>
  </feComponentTransfer>
  <!-- 3. 用位移图扭曲背景 -->
  <feDisplacementMap in="blur" in2="alpha" scale="18" xChannelSelector="R" yChannelSelector="G" result="displaced"/>
  <!-- 4. 叠加回原图 -->
  <feMerge>
    <feMergeNode in="displaced"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

## 注入方式

在 HTML `<body>` 顶部注入一次（全局共享）：

```html
<svg style="position:absolute;width:0;height:0" aria-hidden="true">
  <defs>
    <filter id="liquid-glass">...</filter>
    <filter id="glass-highlight">
      <feSpecularLighting surfaceScale="3" specularConstant="0.6" specularExponent="25" result="specular">
        <fePointLight x="150" y="-80" z="200"/>
      </feSpecularLighting>
      <feComposite in="specular" in2="SourceAlpha" operator="in" result="highlight"/>
      <feMerge>
        <feMergeNode in="SourceGraphic"/>
        <feMergeNode in="highlight"/>
      </feMerge>
    </filter>
  </defs>
</svg>
```

## CSS 使用

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter:
    url(#liquid-glass)        /* SVG 折射 */
    blur(12px)               /* 基础模糊 */
    contrast(1.05)           /* 微对比度增强 */
    brightness(1.08)         /* 微亮度提升 */
    saturate(1.2);           /* 增加色彩饱和度 */
  -webkit-backdrop-filter:   /* Electron 需要 -webkit- 前缀 */
    url(#liquid-glass)
    blur(12px)
    contrast(1.05)
    brightness(1.08)
    saturate(1.2);

  /* 边缘高光：模拟光线在玻璃边缘的反射 */
  border: 1px solid rgba(255, 255, 255, 0.50);
  border-top-color: rgba(255, 255, 255, 0.70);   /* 上缘更亮 = 光源从上方来 */
  border-left-color: rgba(255, 255, 255, 0.60);

  /* 浮起阴影 + 内发光 */
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.55),    /* 上缘内发光 */
    inset 0 -1px 0 rgba(255, 255, 255, 0.10);   /* 下缘微反光 */

  border-radius: 16px;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
```

## Hover 时增强折射

```css
.glass-panel:hover {
  backdrop-filter: url(#liquid-glass) blur(14px) contrast(1.08) brightness(1.12) saturate(1.3);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.65), inset 0 -1px 0 rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);  /* 轻微上浮 */
}
```

## 各组件 scale 参考

| 组件 | feDisplacementMap scale | blur |
|------|------------------------|------|
| 小按钮/标签 | 12~18 | 8px |
| 卡片/面板 | 18~20 | 12~14px |
| 弹窗/大面板 | 20~24 | 24px |
| 侧边栏 | 18~20 | 20px |
| Toast | 16~18 | 16px |

> scale 太大（>30）会产生撕裂感，太小（<10）效果不明显。

## 降级方案

不支持 SVG filter 的环境（旧版 Chromium、部分 WebView2）回退到普通毛玻璃：

```css
@supports not (backdrop-filter: url(#liquid-glass)) {
  .glass-panel {
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
  }
  .glass-panel:hover {
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
  }
}
```

## 背景要求

backdrop-filter 需要**背后有内容可折射**。必须给 body 加渐变背景 + 装饰性光斑：

```css
body {
  background: linear-gradient(135deg, #e8edf5 0%, #dce3f0 30%, #e6ddf0 60%, #dde8f2 100%);
}
/* 浮动光斑 */
body::before {
  content: '';
  position: fixed; top: -15%; right: -8%;
  width: 550px; height: 550px;
  background: radial-gradient(circle, rgba(120,140,255,0.18), transparent 70%);
  border-radius: 50%; z-index: -1;
  animation: float 12s ease-in-out infinite;
}
body::after {
  content: '';
  position: fixed; bottom: -10%; left: -5%;
  width: 450px; height: 450px;
  background: radial-gradient(circle, rgba(220,160,255,0.14), transparent 70%);
  border-radius: 50%; z-index: -1;
  animation: float 15s ease-in-out infinite reverse;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -20px); }
}
```

## 暗色模式

```css
[data-theme="dark"] .glass-panel {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  border-top-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.10);
}
body.dark { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16162a 100%); }
body.dark::before { background: radial-gradient(circle, rgba(60,80,180,0.25), transparent 70%); }
body.dark::after { background: radial-gradient(circle, rgba(100,60,160,0.18), transparent 70%); }
```

## 性能注意事项

- 避免超过 3 层嵌套 `backdrop-filter`
- 浮动光斑动画使用 `transform` 而非 `top/left`（触发合成层而非重排）
- 添加 `@supports` 降级确保旧环境可用
- SVG filter 中 `feDisplacementMap` 的 `scale` 值越大性能开销越大，推荐控制在 12~30