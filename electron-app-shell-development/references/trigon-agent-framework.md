# Trigon Agent 框架 — 工程档案 (E:\Project\Framework)

个人 Agent 框架, Electron 43.4.0 (npm devDep `electron`), Node 24, package.json main = `src/main/index.js`。
npm registry 已为 npmmirror; 二进制下载失败时:
`ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ node node_modules/electron/install.js`

## 目录结构
```
E:\Project\Framework\
├── package.json            scripts: start / smoke (electron . --smoke) / assets (python)
├── logo.svg                ← 唯一标识 (三角体: 顶绿#2A9D8F→#4CAF50, 左#1D3557, 右#E63946)
├── 背景.png (原始 4320x2424, 15MB) → background.png (2560x1436, 5.2MB, PIL 压)
├── assets/                 make-assets.py 生成: logo.png / logo-256 / logo-128 / logo.ico
├── scripts/make-assets.py  PIL 重绘三角体(与 SVG 同几何) + 背景压缩
├── src/main/
│   ├── index.js            入口: 无边框窗口(1280x800, frame:false), 单例锁, ipcMain 'host:invoke' 路由, Menu.setApplicationMenu(null)
│   ├── appManager.js       scan src/apps/*/manifest.json; WebContentsView 容器; 布局 {x:74,y:31,w-74,h-31}; injectThemeCss; scopedApis
│   ├── theme.js            nativeTheme.themeSource; 广播 'trigon:theme' {mode,effective}; 系统模式监听 updated
│   ├── providers.js        9 预置 + 自定义; chatComplete / chatStream(SSE) / test
│   ├── settingsStore.js    userData/trigon-settings.json: theme, defaultApp, activeProvider, activeModel, providers[], appData{}
│   └── smoke.js            --smoke 冒烟 (见下)
├── src/preload/shell.js    暴露 window.trigon (contextIsolation:true, sandbox:false)
├── src/shell/              index.html + css/tokens.css(三主题) + css/glass-app.css + css/shell.css + js/shell.js
└── src/apps/{chat,settings,hello}/
```
壳 UI: 31px 顶栏(左侧苹果红绿灯自绘 + 拖拽区 -webkit-app-region) + 74px 左侧图标导航(logo 顶部, 应用按钮 48px, 设置齿轮底部固定)。
Apple 风格约束(用户偏好): 液态玻璃 blur(28px) saturate(190%), Apple 蓝 #0A84FF, 大圆角, 负字距, 分段控制器(背景轨道+选中浮起), prefers-reduced-motion/transparency 兜底。

## window.trigon API (preload 暴露, 页面用 `const host = window.trigon` — 禁止再声明同名 const!)
- `theme.get()/set(mode)/onChange(cb)`; `apps.list()/switchTo(id)/current()`; `onAppChanged(cb)`
- `settings.get()/set(patch)`; `data.get(k)/set(k,v)` (按 appId 隔离)
- `providers.list()/save(cfg)/remove(id)/test(cfg)` (test 拉 /models + 1 轮短对话, 返回 {ok,latency,models,...})
- `chat.complete(req)`; `chat.stream(req, onChunk)` (onChunk 收 {done,delta|text|error}); `chat.models(providerId)`
- `window.minimize/toggleMax/close/isMaximized`; `assets()`; `host()`; `invoke(method, ...flatArgs)` (应用自注册 API, 参数必须是平铺、不要包数组)

## 应用 manifest schema (porting)
```json
{ "id": "hello", "name": "示例", "nameEn": "Porting Demo", "icon": "🧪",
  "entry": "index.html", "main": "main.js", "order": 2, "wallpaper": true }
```
`main.js` 约定: `module.exports = ({app, api}) => { api('ping', async ({appId,args,sender}) => ...) }`, 渲染端 `host.invoke('ping','x')` → args=['x']。
宿主自动注入 tokens.css + glass-app.css + 壁纸到每个应用 dom-ready (manifest.wallpaper=false 可关壁纸)。

## 模型提供商预置 (providers.js PRESETS)
| id | 名称 | type | baseURL | 默认模型 |
|---|---|---|---|---|
| deepseek | DeepSeek 深度求索 | openai | https://api.deepseek.com | deepseek-chat |
| qwen | 通义千问 Qwen | openai | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-max |
| glm | 智谱 GLM | openai | https://open.bigmodel.cn/api/paas/v4 | glm-4.6 |
| kimi | Kimi 月之暗面 | openai | https://api.moonshot.cn/v1 | kimi-k2-0905-preview |
| mimo | 小米 MiMo | openai | https://api.mimo.ai/v1 | mimo-v1.5 |
| sensenova | 商汤 日日新 | openai | https://api.sensenova.cn/compatible-mode/v1 | SenseChat-5.6 |
| openai | OpenAI | openai | https://api.openai.com/v1 | gpt-4o |
| anthropic | Claude | anthropic | https://api.anthropic.com/v1 | claude-sonnet-4-20250514 |
| grok | xAI Grok | openai | https://api.x.ai/v1 | grok-4 |

已踩坑: `merged()` 里 `if (s.custom && !savedMap.get(s.id))` 会把所有 custom 滤掉 → 改 `if (s.custom)` 无条件 push。

## --smoke 冒烟 (src/main/smoke.js, 15 项)
证据落盘 `.smoke/`: progress.log / results.json / 4 张全窗口截图 (1-light-chat, 2-dark-chat, 3-dark-settings, 4-dark-hello)。
运行前必须: `MSYS_NO_PATHCONV=1 taskkill /F /T /IM electron.exe` + `rm -f .smoke/*`, 再
`ELECTRON_ENABLE_LOGGING=1 ./node_modules/.bin/electron . --smoke`。
测链: 本地 mock OpenAI 兼容服务 (127.0.0.1:18765, /v1/models + /v1/chat/completions 非流式+SSE) → 主进程直调 → 渲染桥 → 流式分帧 → 应用切换 → 主题切换 → 截图。

**上次会话状态 (2026-08-19)**: 15 项里 10 项真 PASS(模型链路/app注册/自注册API等);
4 张截图曾"假通过"(desktopCapturer 源匹配 bug + 无回读校验) — 已改用 标题匹配 + 写入后 `fs.existsSync && size>0` 校验 + 弃用 Electron 43.4.0 损坏的 `getMediaSourceId()`。
**重启后第一件事**: 重跑 smoke 拿真实截图 → vision_analyze 视觉验证(液态玻璃/三主题/布局) → 再写 README 移植指南。

## 待办 (next session)
1. 重跑 smoke (命令见上), 若 shot-* 仍 FAIL 读 .smoke/progress.log + console.log 定位
2. `移植指南.md`: manifest schema + window.trigon API 表 + 主题/CSS 变量规则 + 常见坑(contextBridge 命名、invoke 平铺参数、壁纸 pathToFileURL)
3. 可选: electron-builder 打包 (icon 已备 assets/logo.ico; 注意国内镜像 electron-builder 下载)