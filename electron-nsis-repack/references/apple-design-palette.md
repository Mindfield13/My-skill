# Apple Design 配色整体替换到 Electron 应用

把 Electron 应用里的 Qwen/Material 浅色主题整体替换成 Apple Design 体系（Apple Blue 主色、System Gray 背景、iOS 阴影、跟随系统深色模式）的一次性会话方案。

## 核心原则

1. **不改变量名，只改值** — 保留所有 `:root` CSS 变量名（`--accent`、`--sidebar-bg`、`--text`、`--border`、`--shadow-*` 等），只把色值换成 Apple 语义等价的。JS/HTML 用 `var(--xxx)` 引用的地方零改动。
2. **同时扫 JS + CSS** — 旧色号的硬编码经常散在 `main.js`、`renderer.js` 里（`setTitleBarOverlay`、`QColor`、DOM 直赋色）。必须 grep 全树，全部清零，不然浅/深切换时会闪回旧色。
3. **必须加 `@media (prefers-color-scheme: dark)` 块** — 原始 Material 主题通常只定义浅色。Apple Design 要求跟随系统深色模式，需在 `:root` 之后紧跟一个完整的 dark 块，把全部变量再覆盖一遍。
4. **用 `execute_code` 的 Python 批量 `str.replace`** — `patch` 在中文路径 + CRLF + 引号嵌套的 CSS 里反复失败（会误删字符或插入真换行）。Python `d.replace(old, new)` 在 `utf-8-sig` 编码下最稳定。
5. **`node --check` 每个 JS 文件** — 替换完成后对 `main.js`、`preload.js`、`renderer.js`、`engine.js` 等逐个跑语法检查，确认没破坏 JS 语法。

## Apple 语义映射速查

| 语义 | Material/Tailwind 旧值 | Apple Design 新值 |
|------|----------------------|------------------|
| 主色 | `#3369E8` / `#1E40AF` | `#007AFF` (Apple Blue) |
| 主色 hover | `#2453C9` | `#0066D6` |
| 成功 | `#059669` / `#22C55E` | `#34C759` (Apple Green) |
| 错误 | `#DC2626` / `#EF4444` | `#FF3B30` (Apple Red) |
| 警告 | `#D97706` / `#F59E0B` | `#FF9500` (Apple Orange) |
| 侧栏背景 | `#F5F7FA` / `#F3F4F6` | `#F2F2F7` (System Gray 6) |
| 主文字 | `#1F2937` | `#1C1C1E` |
| 副文字 | `#8A94A6` / `#6B7280` | `#6E6E73` |
| 极浅 | `#B9C2CE` / `#E5E7EB` | `#8E8E93` |
| 模态阴影 | 单层 | `0 20px 60px rgba(0,0,0,0.18), 0 8px 20px rgba(0,0,0,0.10)` |
| 大圆角 | `8px` | `16px` |
| 动画曲线 | 无/默认 | `cubic-bezier(0.34,1.56,0.64,1)` (spring) |

## 深色模式变量覆盖（`@media (prefers-color-scheme: dark)`）

```css
@media (prefers-color-scheme: dark) {
  :root {
    --sidebar-bg: #1C1C1E;
    --bg: #141416;
    --input-bg: rgba(255,255,255,0.06);
    --accent: #0A84FF;
    --accent-dark: #409CFF;
    --text: #F5F5F7;
    --text-sub: #A1A1A6;
    --border: rgba(255,255,255,0.10);
    --success: #30D158;
    --danger: #FF453A;
    --warning: #FF9F0A;
    --shadow-modal: 0 24px 70px rgba(0,0,0,0.55), 0 8px 22px rgba(0,0,0,0.35);
  }
}
```

## 全树扫描命令（Python，避开中文路径/编码坑）

```python
import os, re
base = os.path.abspath(r"E:\项目\小白言\提取\app\resources\app_content")
old_tokens = ["#1F2937","#3369E8","#B9C2CE","#D6DCE4","#2453C9",
              "#F5F7FA","#F8F9FB","#E5E7EB","#D97706","#DC2626","#059669"]
hits = 0
for root,_,files in os.walk(base):
    for f in files:
        p = os.path.join(root,f)
        try: txt = open(p, encoding="utf-8").read()
        except: continue
        for t in old_tokens:
            if t in txt:
                hits += 1
                print(f"HIT {t} @ {os.path.relpath(p,base)}")
print("total hits:", hits)
```

## 常见坑

- **`patch` 工具在 CSS 引号/中文路径下会吞字符或插入真换行** — 用 Python `str.replace` 代替。
- **JS 里的 `setTitleBarOverlay`** 硬编码色号（`#1F2937`、`#E5E7EB`）必须改，否则标题栏在深色模式下仍然浅/深颠倒。
- **`QColor(str, int)` 风格** 的硬编码（`#3369E8`）如果在 JS 里也出现，同样改。
- **`@media (prefers-color-scheme: dark)` 放错位置** — 必须紧接浅色 `:root` 块之后，放在文件末尾会被后续规则覆盖。
- **变量名被误删** — 替换时用**只改值不改名**的方式：把 `--accent: #3369E8;` 换成 `--accent: #007AFF;`，而不是新建 `--apple-accent`。

## 与 repack 步骤的衔接

配色替换完成后，按 `electron-nsis-repack` 的 Repack 关键路径（app.asar → 7z → NSIS）重新打包。7z 载荷务必从干净的 `_app/` 树重建，避免上一次 `app_content/` 残留被当成"幽灵文件"混进新载荷。