# 客户端加密体系破解手法（通用）

Electron/Node 桌面应用的常见「加密反破解」设计，以及对应的通用绕过手法。适用于安全评估、授权绕过、防篡改分析。

## 威胁模型

客户端应用的所有代码（含 asar 包）对攻击者开放。**任何在客户端执行的加密/判定逻辑，最终都可以被还原或改写** —— 因为代码为了运行必须自带解密能力。本文件围绕这个根本事实给出分析路径。

## 1. 代码混淆（javascript-obfuscator 等）

### 识别
- 源码单行化、变量名为 `_0x...` 十六进制
- 字符串收进数组，运行时通过解码器还原
- 常见配置：`controlFlowFlattening`（控制流平坦化）、`deadCodeInjection`、`selfDefending`（自我防御，格式化即崩溃）

### 通用字符串解码器（base64 变体）

```javascript
const ALPHA = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/=';
function decode(s) {
  let out = '', idx = 0, c = 0, b1 = 0;
  for (let i = 0; i < s.length; i++) {
    c = ALPHA.indexOf(s[i]);
    if (~c) {
      b1 = idx % 4 ? b1 * 64 + c : c;
      if (idx++ % 4) out += String.fromCharCode(255 & b1 >> (-2 * idx & 6));
    }
  }
  let pct = '';
  for (let i = 0; i < out.length; i++) pct += '%' + ('00' + out.charCodeAt(i).toString(16)).slice(-2);
  try { return decodeURIComponent(pct); } catch (e) { return ''; }
}
```

### 破解策略（重要）
**不需要完整反混淆**。程序的调用方（main/entry）只依赖被混淆模块的**导出接口**（行为约定），不依赖内部实现。因此：
1. `require` 被混淆的模块 → `Object.keys(module.exports)` 拿到真实接口名
2. 整体重写该模块为清晰实现（导出接口不变、行为按需改动）
3. 替换进包即可 —— 无需理解混淆代码在干什么

> ⚠️ selfDefending/格式化检测：若重写后仍加载原混淆文件并报 "debugger" 或崩溃，说明开启了自我防御 —— 整体重写模块天然规避。

## 2. 配置加密（对称 XOR / 简单流密码）

### 常见形态
- 字段不再明文化（如 `k`/`s`/`secret`/`iv`），而是 `前缀 + XOR + base64`
- 前缀用于校验解密是否正确（如 `XBY1`）
- 同一个密钥加密所有字段

### 通用解密
```javascript
function xorDecrypt(encB64, key) {
  const b = Buffer.from(encB64, 'base64');
  let out = '';
  for (let i = 0; i < b.length; i++)
    out += String.fromCharCode(b[i] ^ key.charCodeAt(i % key.length));
  return out; // 若带前缀再 strip
}
```

### 密钥获取三招（按成本排序）
1. **调用公开 API**：配置读取函数（`getConfig()` 等）内部必然解密，直接 require 后调用 → 明文。零成本。
2. **已知明文攻击**：任一字面明文已知（如 appId、邮箱、host），`key[i] = cipher[i] ^ plain[i]` 还原密钥流；再用它解其他字段验证。
3. **源码正则提取**：密钥常量常以字面量存在于代码（`const KEY = '...'`），或由字符串表多段拼接。配套工具脚本往往用正则提取它 —— 直接照抄该正则。

## 3. 完整性哈希校验（防篡改）

### 常见形态
- 对关键文件（license.js/security.js/核心引擎）计算 SHA-256（常取前 N 位拼接）
- 本地比对：`getExpectedHash()`（从配置解密）vs `getCodeHash()`（实时计算）→ 不等则退出/闪退
- 服务端比对：请求体携带 `codeHash`，服务器与记录的期望值比对 → 不等拒绝授权

### 绕过（关键）
- 本地比对：让 `getCodeHash()` 与 `getExpectedHash()` **返回同一常量**（用原版哈希值即可）→ 恒等，永不闪退
- 服务端比对：**不要**用配套工具（如 `update-hashes.js`）重新生成新哈希 —— 服务器记录的是**原版代码**哈希。正确做法是让请求函数（activate/verify）**完全本地化**，不发请求，服务器比对无从生效
- 若必须联网：把 `EXPECTED_CODE_HASH` 也视为已泄露常量，本地假服务器照抄返回

## 4. 传输层：HTTPS + 证书钉扎 + 请求签名

### 常见形态
- `session.defaultSession.setCertificateVerifyProc()` 钉扎特定证书/CA
- 签名串：`method\npath\ntimestamp\nnonce\nbodyHash` + HMAC-SHA256(appSecret)
- 请求头：`X-App-Key / X-Timestamp / X-Nonce / X-Signature / X-Body-Hash`

### 绕过关键
这些只防**中间人/重放/伪造服务器**。若授权判定被改写为本地直通（见 §3），则不发起任何请求 → 传输层防护全部失效。**先本地化，再谈协议**。

## 5. 本地 Token 加密（safeStorage / DPAPI / Keychain）

- Windows: Electron `safeStorage` 基于 DPAPI（当前用户凭据）
- 常见回退缺陷：`isEncryptionAvailable()` 为 false 时回退明文（`raw:` 前缀）—— 可通过伪造环境或改写代码触发回退
- 换机器/换用户无法解密，但攻击者只关心本机破解 → 影响有限

## 6. 整体检查清单（评估任一客户端应用）

```
[ ] 包可提取（asar/unpacked）？  → 能 → 客户端防线全线可审计
[ ] 授权判定在客户端？           → 是 → verify/activate 可本地化
[ ] 配置字段加密？               → 是 → 走 §2 三招拿明文
[ ] 代码混淆？                   → 是 → 走 §1 整体重写（保接口）
[ ] 完整性哈希？                 → 是 → 走 §3 同常量 + 完全本地化
[ ] 证书钉扎/签名？              → 是 → 本地化后无意义
[ ] 服务端强校验？               → 是 → 唯一硬防线：核心逻辑放服务端才有效
```

## 结论

客户端加密体系无论做几层，最终防线都是**服务端权威**。客户端所有加密/混淆/哈希/签名只能抬高分析成本，不能阻止破解 —— 分析时按「本地可还原、接口可替换、请求可本地化」三条主线推进即可。

---
> 实战案例：小白言软著助手 v2（混淆 + XOR 配置 + codeHash 双重校验）完整破解过程见同目录 `xiaobaiyan-v2-obfuscated-crack.md`（脱敏原则：不含真实密钥/凭据/哈希值）。