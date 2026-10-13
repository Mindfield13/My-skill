# v10 实录：V8 字节码（.jsc）保护 + bootstrap 入口 + 明文拦截器覆盖

## 背景

小白言软著助手 v10（app.asar 2,138,402 B，49 文件）将核心 JS 文件全部编译为 V8 字节码（`.jsc`），入口改为 `bootstrap.js` + `bytenode`。这是比混淆更强的一层保护——字节码不可读、不可改。

主要变化：
- `package.json` 的 `main` 从 `main.js` 改为 `bootstrap.js`
- `bootstrap.js` 为明文入口（32 行），加载 `bytenode` 注册 `.jsc` 扩展名，然后重写 `Module._findPath` 使 `require('xxx')` 找不到 `.js` 时尝试 `.jsc`，最后 `require('./main.jsc')`
- 核心文件：`main.jsc`（78KB）、`gen/engine.jsc`（102KB）、`gen/license.jsc`（18.5KB）、`gen/security.jsc`（8.9KB）等 10 个 `.jsc` 文件
- 明文 JS 文件仅剩：`bootstrap.js`、`preload.js`、`src/renderer.js`、`assets/lucide.min.js`
- 新增 `node_modules/bytenode/` 依赖

## 破解思路

### 核心洞察

`bootstrap.js` 的 `Module._findPath` 修改逻辑是：**先找 `.js`，找不到再试 `.jsc`**。这意味着：
- 放一个 `gen/license.js` 明文文件，`require('./gen/license')` 会优先加载它，跳过 `license.jsc`
- 同时 bootstrap.js 是明文入口，可以在加载 main.jsc 之前注入全局拦截器

### 两个拦截器

1. **`crypto.createDecipheriv` 拦截器**（解决模板解密）

engine.jsc 字节码里的 `decryptTemplate(dk, name)` 用 AES-256-GCM 解密 `names-core.prompt.enc`。我们没有 dk（服务器下发），但可以：
- 拦截 `crypto.createDecipheriv('aes-256-gcm', ...)`，返回 fake Decipher 对象
- fake 的 `update()` 和 `final()` 返回空 Buffer
- `Buffer.concat([...])` 结果为空字符串 → `namesCore = ""`
- prompt 中 `'【软著命名核心规范，必须严格遵守】' + namesCore` 变为 `'【软著命名核心规范，必须严格遵守】'`
- **引擎硬编码的完整命名规则（1-7 条）不受影响**，生成功能依旧可用

2. **`globalThis.fetch` 拦截器**（解决设备检查）

main.jsc 字节码里的 `_0x2ce0b5` 函数调用 `fetch` 到 `https://agent.xiaobaiyan.cn/api/v1/device/check` 等路径。返回 `code===-1` 或 `allowed!==true` 时 `app.exit(1)`。拦截器对 `agent.xiaobaiyan.cn` 的请求返回 `{code:0, data:{allowed:true, force_update:false}}` → 所有设备检查、上报、更新检查全部本地通过。

### 明文覆盖

- `gen/license.js`：10 导出（同 v9 破解版），本地激活 + 1000 年授权
- `gen/security.js`：4 导出（同 v9 破解版），全安全
- 其他模块（engine/chat/stacks/env/semi/llm）不提供明文，走字节码

## 验证结果（19/19）

- bootstrap 拦截器：3 项（createDecipheriv / fetch / bytenode）
- fake Decipher 行为：3 项（setAuthTag / update / final）
- fetch mock 响应：3 项（code:0 / allowed:true / force_update:false）
- license 行为：10 项（10 导出 / server=null / activated / hash / dk / MC / expire / verify / activate）
- security：1 项（4 导出）

## 通用要点

- V8 字节码不可读不可改，但**不需要直接破解字节码本身**——利用 Node 模块解析优先级和全局拦截器即可绕过
- 关键前提：存在明文入口点（bootstrap.js）或可覆盖的模块路径
- 拦截器对字节码内部的所有调用同样生效（全局对象代理）
- 只覆盖必要模块（license/security），其他走字节码——最小化改动
- 解密函数返回空字符串不抛错，比抛错处理更安全（try/catch 走正常路径）

## 工具

- asar CLI: `C:/Users/MindField/AppData/Local/hermes/hermes-agent/node_modules/@electron/asar/bin/asar.js`（`.bin/asar` 是 shim，直跑会报错）
- bytenode: `node_modules/bytenode/lib/index.js`（注册 `.jsc` 扩展名的加载器）