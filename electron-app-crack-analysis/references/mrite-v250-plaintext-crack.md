# Mrite v2.5.0 破解实录 — 纯明文 JS + Rust 原生空壳 + 双层门禁（激活码+登录）+ localStorage 覆盖

> 案例时间：2026-08-13 | 应用：数模论文 AI 生成桌面应用（Electron）
> 结论：v2.5.0 全为明文 JS，无混淆、无完整性校验。mrite-core.node 是 Rust 原生模块但 JS 层从未调用其校验函数。

## 1. 防护体系（识别清单）

```
main.js                   纯明文，5 行 → 加载 bootstrap
src/core/bootstrap.js     明文，启动引导
src/services/auth.js      明文，IPC 授权服务（30KB）
src/services/user.js      明文，IPC 用户登录服务（OAuth）
native/wrapper.js         明文，mrite-core.node 封装 + JS fallback 完整实现
native/index.js           NAPI-RS 自动生成，多平台加载
mrite-core.node           Rust 原生模块（483KB）— 导出函数从未被 JS 调用！
integrity.json            静态文件，无代码读取
```

**关键发现：** native/wrapper.js 包含完整的 JS fallback 实现（`deriveKey`, `aesGcmDecrypt`, `verifyFileIntegrity`, `antiDebugCheck`, `resolveString` 等），所有函数与原生模块一一对应。若原生模块加载失败，自动降级 JS fallback。

## 2. 攻击面

| 模块 | 状态 | 攻击手法 |
|---|---|---|
| main.js | 明文 | 无需修改（只是 bootstrap） |
| auth.js | 明文 | 替换 `register()` 为假 IPC handler |
| user.js | 明文 | 替换 `register()`/`getLoginStatus()` 恒登录 |
| state.js | 明文 | 默认 `authState:'authorized'` |
| license-timer.js | 明文 | `checkExpired()` 恒 false |
| ui.js | 明文 | 替换 `showActivation()` 为无操作 stub |
| toolbar.js | 明文 | 跳过 `onRun` 授权检查 |
| storage.js | 明文 | 加载后强制覆盖授权数据 |
| settings.js | 明文 | `_loadUser` 回退假数据 |
| modify.js | 明文 | 移除授权门禁 |
| index.js | 明文 | 预置假登录态 |
| mrite-core.node | 原生空壳 | 无需处理（JS fallback 全覆盖） |

## 3. 破解修改（10 处）

### 主进程（2 处）

**`src/services/auth.js`** — 替换 `register()` 全部内容：
- 所有 IPC handler 返回假数据（`verify-invite-code`/`check-session`/`request-session`/`check-activation`/`report-usage` 等）
- 启动后 1s 直接 `notifyAuthState('authorized')`

**`src/services/user.js`** — 替换 `register()` + `getLoginStatus()`：
- `getLoginStatus()` 恒返回 `{ loggedIn: true, user: {...} }`
- `register()` 设置假登录态，IPC handler 返回假数据

### 渲染进程（8 处）

**`renderer/state.js`** — 默认 `authState:'authorized'`、`inviteVerified:true`、`inviteCode:'CRACKED'`

**`renderer/license-timer.js`** — `checkExpired()` 恒返回 `false`

**`renderer/ui.js`** — 替换 `showActivation()` 为无操作 stub（直接设置授权状态，不创建遮罩）

**`renderer/toolbar.js`** — `onRun` 跳过 `authState` 授权检查（`if(false)` 包裹）

**`renderer/storage.js`** — `loadSettings()` 同步加载和异步 `dbGetSettings` 加载后都强制覆盖授权数据（防止 localStorage/DB 旧数据覆盖）

**`renderer/panels/settings.js`** — `_loadUser()` 无 localStorage 数据时回退假数据

**`renderer/panels/modify.js`** — 移除三段授权门禁（激活码检查、过期检查、服务器二次验证）

**`renderer/index.js`** — DOMContentLoaded 后预置 `Mrite._userToken` 和 `Mrite._userData`

## 4. 关键教训

### localStorage/DB 会覆盖 patch
最容易被忽略的坑。patch `state.js` 默认值后，`storage.js` 的 `loadSettings()` 会从 localStorage 和数据库读取旧数据并 `Object.assign` 覆盖。**必须同步 patch `storage.js`，在每次加载后强制覆盖授权字段。**

### showActivation 是全屏遮罩
`ui.js` 的 `showActivation()` 创建 `.activation-overlay` 全屏遮罩，要求输入激活码。直接替换为无操作 stub（设置授权状态后返回），比 patch 每个调用点更可靠。

### togglePanel 有导航门禁
`ui.js` 的 `togglePanel()` 检查 `inviteCode` 是否存在，若无则显示 Toast「请先输入激活码」并阻止切换到非设置页面。patch `storage.js` 确保 `inviteCode` 始终为 `'CRACKED'` 即可绕过。

### 双层门禁：激活码 + 用户登录
`task.js` 检查 `userService.getLoginStatus().loggedIn`，`toolbar.js` 检查 `_userToken` 和 `_userData`。两个门禁需分别绕过。

### Native addon 是空壳
`mrite-core.node` 的 `verifyFileIntegrity` / `antiDebugCheck` / `resolveString` 导出但从未被任何 JS 代码调用。`integrity.json` 也是静态文件，无代码读取。**纯 Rust 原生模块不等于安全——JS 层不调用它就是个摆设。**

## 5. 重打包

```bash
# 正确 unpackDir（匹配原始 unpack 目录）
asar.createPackageWithOptions(src, dest, {
  unpackDir: '{assets/TinyTeX,assets/python-env,node_modules/@anthropic-ai,node_modules/@img,node_modules/@napi-rs,node_modules/better-sqlite3,node_modules/sharp}'
})
```

## 6. 验证

- 启动日志：所有核心模块加载完成 → IPC 注册完成 → 启动完成
- 4 个 Mrite.exe 进程稳定运行
- 界面无激活遮罩、无「请先输入激活码」Toast、底部显示「已激活」
- 可正常切换所有面板、启动任务