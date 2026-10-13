---
name: js-obfuscation-reversing
description: >-
  Reverse obfuscated JS: strings, XOR, codeHash.
version: 1.0.0
author: Hermes Agent
---

# JS 混淆 / 加密代码逆向

当目标 JS 是 javascript-obfuscator 等工具混淆后的单行代码（`_0x` 变量 + 加密字符串表），或带客户端自校验（codeHash）、XOR 加密配置时使用。典型场景：Electron 应用升级防护后的二次破解、任何混淆 JS 的行为还原。

> 关联：`electron-app-crack-analysis`（用户所有，覆盖明文版 Electron 破解；本技能覆盖混淆/加密版）。

## 触发条件

- 文件单行且大量 `_0x\w+` 变量、字符串表 `function _0x9adc(){const...=['...']}`
- 配置文件出现加密字段（如 `k`/`s`/`ch`，base64 密文）
- 导出含 `getCodeHash`/`getExpectedHash` 或存在 `update-hashes.js`（自完整性校验）
- 修改后程序闪退 `app.exit(1)`，疑似代码哈希比对

## 工作流

### 1. 识别混淆器与字符串表

javascript-obfuscator 特征：单行 + `_0x` 命名 + 字符串表 base64 解码器（`~indexOf && ...` 跳过非法字符，percent-encode 后 `decodeURIComponent`）。用 `scripts/deobfuscate-string-table.js` 一键解码整份文件的字符串表，按关键词过滤（license/security/hash/api/process 等）。解码结果常是**截断片段**（混淆器把长字符串拆段拼接），如 `'getCodeH'+'ash'`。

**两种字符串表变体（务必先区分，解码器完全不同）：**

| 变体 | 调用形式 | 解码方式 |
|------|---------|---------|
| 普通 stringArray | 单参 `_0x4848(0x320)` | 数组元素自定义 base64 直解（轮换后） |
| **RC4 变体** (stringArrayEncoding:['rc4']) | **双参 `_0x1c49c3(0x1bd,'vsPE')`** | 数组元素为 RC4 密文，**每个调用点有独立 key**；先 base64 再按 key RC4 |

RC4 变体特征：解码函数形如 `_0x6df9(offset,key)`，且**轮换 IIFE 的 checksum 本身也用双参调用**（如 `_0x2c5270(0x2ca,'W2[w')`）——轮换和 RC4 互相依赖，单独模拟很容易死循环不收敛。此时最优策略是**让原模块自己解码**（见第 2 节的 vm 技巧）而不是手写 RC4 复刻；手写复刻必须注意 JS 的 `charCodeAt` 返回 UTF-16 码元（非 ASCII key 会取错），且 base64 字母表是小写在前的自定义表。

### 2. 拿模块导出接口（不逆向实现）

混淆只是隐藏实现，`require()` 的模块契约仍然开放：

```bash
node -e "console.log(Object.keys(require('./gen/license.js')))"
# → ['getConfig','getMachineCode','getState','activate','verify','clearLicense','errHint','getCodeHash','getExpectedHash']
```

Electron 模块的 `require('electron')` 通常被 try/catch 包裹，纯 Node 可加载。逐个调用导出函数直接实测行为（这是最快的"已知明文"来源）。**不要**在文件末尾追加 `console.log(_0x变量)` 注入——顶层 `_0x` 常量不在模块作用域，`is not defined`。

### 3. 主流程追踪（验证启动不闪退 / 发现调用点）

用 `Module._compile` 编译混淆的 main.js，伪造 electron stub（app.getPath/whenReady/quit/**exit 拦截打印**/BrowserWindow/shell/ipcMain/safeStorage/session.defaultSession.setCertificateVerifyProc），require 指向真实 gen 模块：

- **必须拦截 `global.setInterval = () => 0`**：main.js 有心跳定时器，不拦会挂起；用 `setTimeout(...dump; process.exit(0), 500)` 收尾
- 启动流程里 main.js 调用的接口（如 `security.runFastCheck()`、`license.getExpectedHash()`）会真实执行并受邀去处理
- 输出出现 `[security] 检测到可疑环境...` 或自定义 exit 拦截即闪退路径

### 4. codeHash / 自完整性校验绕过

`codeHash = sha256(security.js).hex.slice(0,16) + sha256(license.js).hex.slice(0,16)`，本地 `getCodeHash()` vs `getExpectedHash()`（从配置 `ch` 字段解密）比对，不等 → 闪退；同时激活/验证时发给服务器比对 `EXPECTED_CODE_HASH`（服务器钉死原版哈希）。

**破解法**：整体重写该模块，`getCodeHash()` 与 `getExpectedHash()` 返回**同一个固定常量**（直接沿用原版哈希值即可）——本地比对恒成立。**服务器端无法伪造**（记录的是原版代码哈希），所以 `verify()`/`activate()` 必须完全本地化（不调用 fetch），不能依赖服务器。修改后**不要**运行 update-hashes.js 期望更新哈希——服务器端锚点不变。

### 5. XOR + base64 配置解密（已知明文攻击）

格式：`XBY1` 前缀 + 逐字符 XOR(SECRET_KEY) + base64：

```javascript
function xorDecode(enc, key) {
  const b = Buffer.from(enc, 'base64');
  let out = '';
  for (let i = 0; i < b.length; i++) out += String.fromCharCode(b[i] ^ key.charCodeAt(i % key.length));
  return out; // 应得到 'XBY1' + 明文
}
```

已知明文攻击：若某字段明文可运行时获取（如 getConfig() 返回 appKey），则 `key[i % L] = C[i] ^ P[i]` 反推密钥流片段；用片段解其他字段交叉验证。**核心结论写文档**：解密逻辑与密钥都必须在客户端 → 加密配置在运行时必然可还原，这是客户端加密的根本缺陷。

### 6. 重打包与验证

```bash
cd resources && rm -f app.asar && npx --yes asar pack app_content app.asar
```

验证：`Object.keys()` 与混淆版逐一比对；`getCodeHash()===getExpectedHash()`；`verify()`/`activate()` 返回 code 0；Module._compile 启动模拟无闪退；asar 提取后 grep 确认改动已入包。

## 交付文档（用户偏好）

用户明确要求：**文档只写本次改版的改动**（改了哪些文件、改后代码、验证结果），**不要混入既往会话的通用分析、加固建议、多版本对比**。上一轮把"上次的经验写进去"被纠正。除非用户点名要全量分析，否则交付物 = 本次 diff + 验证证据 + 使用方式。

## 常见陷阱

0. **混淆模块"静默退出"= 反调试，不是崩溃** — `require()` 带 debugProtection 的模块（尤其 `decryptor.js` 这类启动即跑 IIFE 的）在纯 Node 里可能 exit 0、无任何报错；`vm.runInContext` 也会被连带杀死。对策：vm sandbox 里塞**假 `process` 对象**（`exit:()=>{}, on:()=>{}, stdout.write, stderr.write`）、假 `require('electron')`（app.isPackaged+getPath 等），并把文件中的反调试 IIFE 段替换成 `;`。逐段截取（解码器+数组+轮换结束处 `0xXXXX))`）比整文件 require 更可控。若仍卡住，用 `node --check`（语法）+ 二分截断定位第二个反调试 IIFE。
1. **嵌套三引号**：execute_code 里用 `r'''...'''` 外再嵌 `r'''...'''`（Node 片段）会提前终止——外层用占位符替换（如 `@@NODE@@`）或单独写临时文件再拼
2. **字符串里含单引号/正则**：`console.log('  /const SECRET_KEY\\s*=\\s*([^']+)/')` 会在 JS 里爆 `missing )`——避免在 console.log 里放含 `'` 的正则，或用双引号包裹
3. **`setInterval` 挂起**：Module._compile 加载 main.js 必须提前替换 `global.setInterval`，否则进程不退出
4. **`%` 格式化冲突**：Python `sc = '''...''' % (...)` 里若内容含 `%d`/`%%` 会报 not enough arguments——改用 `.replace('@@TOKEN@@', value)`
5. **repr() 带引号污染路径**：Python 写路径进脚本用 `repr` 会把引号带进去导致 `Invalid argument`——用 `r"@@PATH@@"` 占位替换，不用 repr
6. **模块作用域注毒**：混淆顶层 `const _0x...` 不在 module scope，文件末尾追加代码访问不到
7. **中文路径**：Node 直接跑 `require('E:/项目/.../license.js')` OK；bash 传中文路径小心 `$` 展开；`read_file` 对单行大 JS 会报 binary，用 execute_code/Node 读

## 支撑文件

- `scripts/deobfuscate-string-table.js` — javascript-obfuscator 字符串表解码器（文件路径 + 关键词过滤）
- `references/xiaobaiyan-v2-obfuscated-crack.md` — 小白言软著助手 v2 实战（接口表、codeHash 值、XOR 密钥流、验证证据）