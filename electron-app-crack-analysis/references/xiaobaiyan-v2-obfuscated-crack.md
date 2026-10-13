# 小白言软著助手 v2 — 混淆 + 哈希校验破解实战（2026-08-13）

Electron 43 应用「小白言软著助手」v2 版（security.js 13,634B / license.js 19,299B / main.js 47,935B，全部 javascript-obfuscator 混淆）。本文件是 `electron-app-crack-analysis` skill「进阶：混淆 + 哈希校验版本」章节的实战案例。

## 版本差异

| 文件 | v1 | v2 |
|------|----|----|
| security.js | 3,521B 明文 | 13,634B 混淆 |
| license.js | 9,842B 明文 | 19,299B 混淆 |
| license.config.json | 明文 server/appKey/appSecret | k/s/ch 加密（XBY1+XOR+base64） |
| main.js | 30,980B 明文 | 47,935B 混淆 |
| 新增 | — | update-hashes.js（改码后重算哈希） |

## v2 的四层防护

1. **代码混淆** — javascript-obfuscator：`_0x` 变量、base64 字符串表、字符串拆段拼接
2. **配置加密** — `XBY1` 前缀 + 逐字符 XOR(SECRET_KEY) + base64；k=appKey, s=appSecret, ch=codeHash
3. **codeHash 完整性** — sha256(security.js).slice(0,16) + sha256(license.js).slice(0,16)；本地 main.js 比对 `getExpectedHash()` vs `getCodeHash()`，不等即 `app.exit(1)`；激活/验证时也发给服务器比对 `EXPECTED_CODE_HASH`
4. **正式服务器** — `https://agent.xiaobaiyan.cn` + HTTPS 证书钉扎（setCertificateVerifyProc）

## 关键发现（如何确认调用关系）

用 `Module._compile` + Proxy require（fake electron）加载混淆 main.js，捕获启动时实际调用的模块方法序列：

```
engine.ensureScripts
security.runFastCheck          ← 新增！不是 runSecurityCheck
license.getExpectedHash        ← 新增！本地哈希比对
license.getCodeHash
license.getConfig
env.checkEnvironment
```

> ⚠️ 陷阱：直接跑混淆 main.js 会因 setInterval（心跳 + 安全复查定时器）挂起。必须全局替换 `setInterval = () => 0`，并用 `setTimeout(...,300)` 在微任务完成后 dump 调用序列 + `process.exit(0)`。

## 破解步骤（简版）

1. `require` 混淆模块 → `Object.keys(module.exports)` 拿到真实导出：
   - license.js: 9 个 `getConfig, getMachineCode, getState, activate, verify, clearLicense, errHint, getCodeHash, getExpectedHash`
   - security.js: 4 个 `runSecurityCheck, runFastCheck, detectCapture, detectVM`
2. 整体重写两文件（保持导出接口一致）：
   - security.js 全部返回空 `{ capture: [], vm: [] }`
   - license.js：getState → activated:true（10年）；verify → `{code:0,data:{valid:true}}`；activate → 直接成功，无 fetch；getCodeHash()===getExpectedHash()===原版哈希常量
3. 原版哈希值实测：`getCodeHash()` = `e06ca0f85dd1cac511fac5d79d59c79e`（破解前）
4. 重打包 asar

## 验证

- 模块级：导出集合与混淆版逐一匹配
- main.js 启动模拟：fake electron + `app.exit` 打桩（`console.log('FLASHEXIT:'+c); process.exit(77)`）→ 期待无 FLASHEXIT 输出
- 本次 40/40 全绿（6 组检查：产物/security/license/仿真/Node加载/启动模拟）

## 加密学习要点（已知明文攻击）

配置 `k` 字段 = `b64(XOR('XBY1'+appKey, SECRET_KEY))`。因 appKey 明文已知（运行时代码必然解密），异或可还原密钥流：

```
keyFrag[i] = b64(k)[i] ^ ('XBY1'+appKey)[i]  →  e8bef04712ed3fa876a13288...
```

能用该片段解密 `s` 字段的前 21 位复现 appSecret，证明 XOR+base64 协议可逆。SECRET_KEY 最终来源是混淆代码字符串表拼接（`_0x330b18(0x1ca)+...`），update-hashes.js 用正则 `/const SECRET_KEY\s*=\s*'([^']+)';/` 提取——密钥与解密逻辑都在客户端，运行时可还原明文。

## 服务器端对比关键点

⚠️ 不要用 update-hashes.js 重新生成 ch：服务器 `EXPECTED_CODE_HASH` 记录的是**原版代码**哈希。破解版必须完全本地化（verify/activate 不发请求），否则服务器比对必失败。