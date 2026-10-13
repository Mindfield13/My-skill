# ASAR 完整性校验 fuse 翻转（v10 最终突破）

## 症状

破解小白言软著助手 v10（bytenode .jsc + bootstrap 入口）时：
- 原版 app.asar 能打开
- 对 app.asar 做任何修改（新增 license.js/security.js、patch bootstrap.js、哪怕是加一个空 test.js、提取后原样重打包）→ 应用启动 2-5 秒内崩溃
- 用户反馈「打不开，与之前的签名不符」

## 定位根因

用 `ELECTRON_ENABLE_LOGGING=1 ./小白言软著助手.exe --enable-logging` 抓真实错误：

```
[FATAL:electron/shell/common/asar/asar_util.cc:146]
Integrity check failed for asar archive entry '<header>'
(7f328045131de8f11346ba92abf542fa66db344afe0946fb4b2e9f34d3ef373e vs b618d022f925eee324892f7017072cf46270e7c8850e5080d6dc1b7dd735d918, 12961 bytes)
```

**关键**：失败条目是 `<header>`（asar 头本身），期望哈希（7f3280...）≠ 实际哈希（b618d0...）。

## 原理

Electron 的 **fuses** 机制（electron-builder/forge 打包时可选开启）：
- `EnableEmbeddedAsarIntegrityValidation` = true → Electron 校验 asar header 与 exe 内置的期望哈希
- 任何 asar 修改都会改 header → 哈希不匹配 → FATAL
- 这是比代码混淆/字节码更底层的防篡改，asar 层的所有破解手段全部无效

## 解法

```bash
npm i -g @electron/fuses

node -e "
const { flipFuses, FuseVersion, FuseV1Options } = require('@electron/fuses');
const path = require('path');
const fs = require('fs');

const exe = 'E:/项目/测试/xiaobaiyan-ruanzhu-assistant/小白言软著助手.exe';
// 备份
fs.copyFileSync(exe, exe + '.bak_v10');

flipFuses(exe, {
  version: FuseVersion.V1,
  [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: false,
});
// 输出 backup done + OK
"
```

`@electron/fuses` 位于 hermes-agent 的 node_modules：`C:/Users/MindField/AppData/Local/hermes/hermes-agent/node_modules/@electron/fuses`。

## 翻转后

- 任意 asar 修改都能加载
- 再用常规手段：明文 `gen/license.js` + `gen/security.js` 覆盖字节码 + patch `bootstrap.js` 注入 `crypto.createDecipheriv` / `globalThis.fetch` 拦截器
- 验证启动：`ELECTRON_ENABLE_LOGGING=1 ./exe --enable-logging` → 看到 `[license] 心跳验证已启动，间隔 10 分钟` + 窗口出现 + 进程稳定存活 = 成功

## 通用排查顺序（修改 asar 后打不开）

1. 先跑带日志：`ELECTRON_ENABLE_LOGGING=1 ./exe --enable-logging`
2. 看到 `FATAL:asar_util.cc ... Integrity check failed for asar archive entry '<header>'` → 就是 fuse
3. 翻转 `EnableEmbeddedAsarIntegrityValidation` fuse
4. 翻转后若还有问题，才排查代码层（字节码、混淆、签名）