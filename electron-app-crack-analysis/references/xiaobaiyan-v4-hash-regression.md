# 小白言软著助手 — 哈希回潮形态破解（实战参考）

小白言软著助手"开发者拿破解版反复重混淆"系列中的新形态：**codeHash 门禁重新加回**（配置 `ch` 字段回归 + `gen/update-hashes.js` 明文脚本），`license.js` 导出增至 10 个，新增 `getContentDk`（模板文件解密密钥）。本文是该形态的脱敏实战记录。

## 版本识别

与前一版（v3 回连真服务器）的差异：

| 项 | v3 | 本形态（哈希回潮） |
|----|----|--------------------|
| `license.js` 导出 | 7 个（无哈希函数） | **10 个**（含 `getCodeHash`/`getExpectedHash`/`getContentDk`） |
| 配置 `ch` 字段 | 无 | **有**（XBY1 加密） |
| `update-hashes.js` | 无 | **有**（明文，重算 codeHash 注入配置） |
| `verify()` 行为 | 连真服务器 | 本地判定（哈希比对） |

## 识别特征

- `license.config.json` 出现 `ch` 字段
- `gen/update-hashes.js` 明文存在，注释提示：`混淆流程: obfuscate.js 会在混淆后注入 XBY_SECRET_KEY 环境变量调用本脚本（混淆后正则提取不到密钥）` —— **密钥被移到环境变量**，是防御升级信号
- 新增 `gen/templates/names-core.prompt.enc`（加密模板，`getContentDk` 提供解密密钥）
- `require` 原版模块，`getCodeHash()` == `getExpectedHash()`（原版代码未被篡改）

## 调用序列（用 Proxy require + `Module._compile` 捕获）

```
engine.ensureScripts
security.runFastCheck
license.getExpectedHash
license.getCodeHash        ← 哈希门禁：不等即 app.exit(1)
license.getState
license.verify
license.getConfig
env.checkEnvironment
```

## 破解思路

**同 v2 核心**：哈希同常量绕过 + 激活本地化。差异点：

1. **导出集合必须逐一匹配原版（含新增）**：原版 10 导出，破解版也需 10 导出，`getContentDk` 等新增导出返回固定占位值，别漏别多
2. **`update-hashes.js` 不必动**：其作用是"改代码后重算 ch 注入配置"，但破解版走本地化激活（不发请求、不更新配置），该脚本永远不会被调用
3. 重写 `security.js` 4 导出空返回
4. `getCodeHash()` 与 `getExpectedHash()` 返回同一常量（取原版哈希值即可），本地比对恒成立
5. `verify()`/`activate()` 完全本地化（`{code:0}` 不发请求）

## 关键点

- `update-hashes.js` 注释里"正则提取不到密钥，走环境变量"是开发者针对"上次被正则抓到密钥"的补丁，**不影响破解**：客户端哈希比对与密钥都在你手里
- 真加固方向仍是**核心判定放服务器**：客户端无论怎么加哈希/加密/环境变量，运行时必然能还原明文
- 该形态攻击面与 v2 等价，是 v2/v3 之间的"折返"

## 实战验证结果

- 模块级：license 10 导出（含 `getContentDk`）、security 4 导出，逐一匹配原版
- 行为：`getState().activated===true`、`getCodeHash()==getExpectedHash()`、`verify().code===0`、`activate('任意').code===0`
- main.js 启动模拟：fake Electron + 真实破解 gen 模块 + `Module._compile` 编译混淆 main.js，`app.exit` 打桩拦截闪退 → **COMPILED + STARTUP_OK + 未闪退**
- 总计 15/15 通过（含 changed-paths 临时文件清理检查）

> 脱敏原则：本文不含真实密钥/凭据/服务器域名。通用手法见 `client-encryption-bypass.md`；v2（哈希首次出现）见 `xiaobaiyan-v2-obfuscated-crack.md`；v3（哈希删+回连服务器）见 `xiaobaiyan-v3-verify-server-crack.md`。