# Mrite v2.3.0 破解实录 — MRITE 加密 + javascript-obfuscator + 完整性校验

> 案例时间：2026-08-13 | 应用：数模论文 AI 生成桌面应用（Electron）
> 结论：纯客户端授权可完整绕过；不需要破 RC4；重打包时 unpack 参数是最大坑。

## 1. 防护体系（识别清单）

```
main.js            javascript-obfuscator（字符串数组505条 + 轮换194次 + RC4字符串 key）
src/decryptor.js   同上 + 反格式化 + 反调试（process.exit 静默退出）
src/integrity-check.js   MRITE v1 加密（RC4 文件加密）
src/services/auth-service.js  MRITE v1 加密
preload.js         明文 — 全部 IPC 通道一览（最大情报源）
renderer/*.js      明文 — 授权状态机全在渲染层
.mrite-hash        完整性校验清单（autorun 时校验）
```

MRITE v1 文件格式：
```
//MRITE:v1:4LIx8dsJ3q5bbhLg:GasoonuZXTAeJtM4BpQ3SQ==
<base64 密文体>
头部 //MRITE:v1:<KEY_B64>:<IV_B64>，算法 RC4 流加密
```

## 2. 破解核心（v3 思路 = 绕过加载）

main.js 中两处 require 路径**是明文**（混淆只保护函数体不保护路径字符串）：

| 原代码 | 替换为 |
|---|---|
| `require('./src/integrity-check')` | `{verifyIntegrity:()=>true}` |
| `require('./src/services/auth-service')` | 内联 stub（注册假 IPC handler，见 SKILL.md） |

渲染层 5 个文件：

| 文件 | 修改 |
|---|---|
| `renderer/state.js` | `authState:'authorized'`、`inviteVerified:true`、`_onAuthStateChanged` 强制 authorized |
| `renderer/toolbar.js` | `_isExpired()` → `return false` |
| `renderer/ui.js` | 删除导航面板授权门禁 |
| `renderer/license-timer.js` | `checkExpired()`/`isExpired()` → `false` |
| `renderer/panels/modify.js` | 移除激活码+过期+`checkActivation()` 三段门禁 |

验证语法：`node --check` 每个改过的文件。

## 3. 重打包（坑最多）

```javascript
const asar = require('asar');
asar.createPackageWithOptions(
  'app-asar-extracted',                        // 解包目录
  'resources/app.asar.new',
  { unpackDir: '{assets,node_modules/@anthropic-ai,node_modules/@img,node_modules/@napi-rs,node_modules/better-sqlite3}' }
);
// asar 90MB + app.asar.new.unpacked 2.6GB → mv 覆盖
```

- 备份：`app.asar.bak` + `app.asar.unpacked.bak` 再替换
- `unpack` 参数只接受**单个** glob 字符串（传数组 → `invalid pattern`）
- `unpackDir` 支持 brace glob，内部是 `dirPath.startsWith(pattern) || minimatch(dirPath, pattern)`，相对路径可行
- 包完验证：`npx asar list --is-pack` 对比 pack/unpack 计数，`du -sh` 确认 asar ≈ 原始大小

## 4. main.js 混淆解码（成功，供参考）

1. 提取字符串数组：`function _0x314f(){const _0x43bf4b=[...]` → eval
2. 模拟轮换：`while(!![])` 直到 checksum 匹配 `0xc6791`（194 次）
3. 自定义 base64（小写字母在前）解码
4. 查表 `_0x4848(0x320)` → `verifyIntegrity` 等字符串

## 5. decryptor.js 反调试对策（未完全成功，留档）

尝试过：假 electron 注入、vm.runInContext、剥离反调试 IIFE、假 process —— 最终 require 仍静默退出（反调试 IIFE `_0x40c54a` 区域 + `_0x2fe3d9` 递归）。
教训：**遇到 process.exit 静默退出的混淆模块，别硬解字符串表，直接走 v3 绕过加载路线**（无需解密就能破解）。若确需解密，需先精确剥离所有反调试 IIFE（轮换结束 `0x535ca))` 后到 `const _0x53c0d4=(function(` 之前的 5506 字符区域），再在 vm 中独立加载。

## 6. 验证

- 启动日志（%TMP%/mrite-startup.log）：`完整性校验通过 → auth-service 注册完成 → 窗口创建完成`
- 进程：4 个 Mrite.exe 稳定
- 界面：无激活遮罩/无授权弹窗/全部面板可访问