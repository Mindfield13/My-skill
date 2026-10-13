# Electron 暗色模式 / 主题切换完整方案

在 Electron 应用中实现三档主题切换（浅色/深色/跟随系统），包括标题栏适配。

## 主进程（main.js）

### 1. 导入 nativeTheme
```js
const { app, BrowserWindow, shell, ipcMain, nativeTheme } = require('electron');
```

### 2. 主题持久化 + 应用
```js
function loadSettings() {
  // ... 从 config.json 读取 apiKey, baseUrl, model, theme
  // theme: 'light' | 'dark' | 'system' (默认 'system')
}

function saveSettings(s) {
  // 保存时 theme 字段
  // theme: (s.theme === 'light' || s.theme === 'dark') ? s.theme : 'system'
}

function applyTheme(theme) {
  nativeTheme.themeSource = (theme === 'light' || theme === 'dark') ? theme : 'system';
  // 同步标题栏颜色
  if (win && !win.isDestroyed()) {
    const dark = nativeTheme.shouldUseDarkColors;
    try {
      win.setTitleBarOverlay({
        color: dark ? '#1A1D23' : '#F5F7FA',
        symbolColor: dark ? '#E6E8EB' : '#1F2937',
        height: 44
      });
    } catch (e) { /* 旧版 Electron 不支持时忽略 */ }
  }
}

function titleBarColors() {
  const dark = nativeTheme.shouldUseDarkColors;
  return { color: dark ? '#1A1D23' : '#F5F7FA', symbolColor: dark ? '#E6E8EB' : '#1F2937' };
}
```

### 3. IPC 处理
```js
ipcMain.handle('settings:save', (_e, s) => {
  const data = saveSettings(s);
  applyTheme(data.theme);  // ← 保存后立即应用
  return data;
});
```

### 4. 应用启动 + 系统主题监听
```js
app.whenReady().then(() => {
  const settings = loadSettings();
  applyTheme(settings.theme);   // 恢复用户主题
  createWindow();

  nativeTheme.on('updated', () => {
    const cur = loadSettings();
    if (cur.theme === 'system') {
      // 同步标题栏
      const dark = nativeTheme.shouldUseDarkColors;
      win.setTitleBarOverlay({ color: dark ? '#1A1D23' : '#F5F7FA', ... });
      // 通知渲染进程
      win.webContents.send('theme:changed', dark ? 'dark' : 'light');
    }
  });
});
```

### 5. 创建窗口时使用动态标题栏色
```js
function createWindow() {
  const tb = titleBarColors();
  win = new BrowserWindow({
    titleBarStyle: 'hidden',
    titleBarOverlay: { color: tb.color, symbolColor: tb.symbolColor, height: 44 },
    ...
  });
}
```

## 预加载脚本（preload.js）

暴露 `onThemeChanged` 给渲染进程：
```js
contextBridge.exposeInMainWorld('api', {
  onThemeChanged: (cb) => {
    const handler = (_e, theme) => cb(theme);
    ipcRenderer.on('theme:changed', handler);
    return () => ipcRenderer.removeListener('theme:changed', handler);
  },
  ...
});
```

## 渲染进程（renderer.js）

### 1. 应用主题类
```js
function applyTheme(theme) {
  const html = document.documentElement;
  html.classList.remove('theme-light', 'theme-dark');
  if (theme === 'light') html.classList.add('theme-light');
  else if (theme === 'dark') html.classList.add('theme-dark');
  // 'system' — 不设 class，由 CSS 的 prefers-color-scheme 控制
}
```

### 2. 加载时恢复
```js
async function loadSettings() {
  const s = await window.api.loadSettings();
  // ... 填充输入框
  const theme = s.theme || 'system';
  applyTheme(theme);
  // 选中对应 radio
  const radio = document.querySelector(`input[name="appTheme"][value="${theme}"]`);
  if (radio) radio.checked = true;
}
```

### 3. 保存时应用
```js
$('#saveSettings').addEventListener('click', async () => {
  const themeRadio = document.querySelector('input[name="appTheme"]:checked');
  const s = { ..., theme: themeRadio ? themeRadio.value : 'system' };
  applyTheme(s.theme);
  await window.api.saveSettings(s);
});
```

### 4. 监听系统主题变化
```js
if (window.api && window.api.onThemeChanged) {
  window.api.onThemeChanged((theme) => {
    const currentRadio = document.querySelector('input[name="appTheme"]:checked');
    if (currentRadio && currentRadio.value === 'system') {
      applyTheme(theme);  // 只在 system 模式时跟随
    }
  });
}
```

## CSS 方案

### CSS 变量分层
```css
:root {
  /* 浅色变量（默认） */
  --bg: #FFFFFF;
  --text: #1F2937;
  --border: #E5E7EB;
  /* ... */
}

/* 深色 — 跟随系统 */
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14161A;
    --text: #E6E8EB;
    --border: #2A2F38;
  }
}

/* 深色 — 用户强制 */
html.theme-dark {
  --bg: #14161A;
  --text: #E6E8EB;
  --border: #2A2F38;
}
html.theme-dark body { color: var(--text); background: var(--bg); }
html.theme-dark .sidebar { background: rgba(26, 29, 35, 0.75); }

/* 浅色 — 用户强制（覆盖系统深色） */
html.theme-light {
  --bg: #FFFFFF;
  --text: #1F2937;
  --border: #E5E7EB;
}
html.theme-light body { color: var(--text); background: var(--bg); }
```

### 常见暗色模式遗漏
- **输入框选择器遗漏**：`#batchCount` 有样式但 `#batchParallel` 没有 → 白色输入框。修复：选择器改为 `#batchCount, #batchParallel`。
- **硬编码边框**：`.task-open`、`.bound-bar`、`.compat-note` 用 `#DBE6FE` 硬编码。修复：`var(--accent-border, #DBE6FE)`，暗色模式中定义 `--accent-border: rgba(91, 141, 239, 0.4)`。
- **hover 色硬编码**：`.task-open:hover` 用 `#DCE7FF`。修复：`var(--accent-border-hover, #DCE7FF)`，暗色模式定义为 `rgba(91, 141, 239, 0.22)`。
- **提示文字对比度不足**：暗色模式下 `--text-faint` 从 `#6B7580` 改为 `#8892A0` 以保证可读性。