# 小白言软著助手 v3 — verify 回连真服务器形态破解（实战参考）

小白言软著助手在开发者拿破解版重混淆后发布的"半重置"版本。核心新形态：**把 `verify()` / `activate()` 从本地判定改回连真授权服务器**，同时**删除了 v2 的 codeHash 完整性校验**。本文是该形态的脱敏实战记录。

## 版本识别

与 v2 的关键差异：

| 项 | v2 | v3（本形态） |
|----|----|-------------|
| `license.js` 导出 | 9 个（含 `getCodeHash`/`getExpectedHash`） | 7 个（**无哈希函数**） |
| 配置 `ch` 字段 | 有（XBY1 加密的 codeHash） | **无** |
| `verify()` 行为 | 本地判定 / 发服务器 | **改回发真实服务器**，非 0 即死 |
| 字符串表 | 189 条（base64 变体 + 数组轮换） | 同结构，无哈希相关条目 |

**识别特征**：
- `license.config.json` 只有 `k`/`s`/`server`/`heartbeatMinutes`，无 `ch`
- 混淆模块 `Object.keys(module.exports)` 缺 `getCodeHash`/`getExpectedHash`
- 字符串表解码后找不到 `getCodeHash`、`getExpectedHash` 字样，但仍有 `/api/act`、`/api/ver`、`X-Signature` 等
- `require` 原版 `verify()` 返回 `{code: 30001, message: "机器码不存在"}`（连服务器被拒）

## 调用序列（用 Proxy require + `Module._compile` 捕获，不要纯静态 grep）

```
engine.ensureScripts
security.runFastCheck
license.getState
license.verify          ← 唯一硬门禁：非 0 即闪退/提示激活
license.getConfig
env.checkEnvironment
```

## 破解思路

**比 v2 更直接**：因为 codeHash 门禁已被删除，无需同常量哈希绕过。只要把 `verify()`/`activate()` **本地化**（返回 `{code:0}` 不发请求）+ 重写 `security.js` 空返回即可。

1. `require` 混淆模块 → 确认 7 导出接口
2. 整体重写 `license.js`：`getState()` 返回 activated:true + 长期有效期；`verify()` 直接 `{code:0, valid:true}`；`activate()` 直接成功（写个本地 license.json 让状态持久）
3. 整体重写 `security.js`：4 导出全部返回空 `{capture:[], vm:[]}`
4. 重打包 asar

## 关键点

- **开发者回连真服务器的意图**是"本地破解码无法通过服务器校验"，但**客户端判定逻辑仍在你手里** —— 把 verify/activate 改成本地直通，服务器根本不被调用，其 30001/10001 拒绝无从生效
- 这形态的防御**不如 v2 完整**（删了 codeHash，等于少一层）
- 若开发者想真加固：**核心判定必须放服务器做**（客户端只提交凭据、接受结果），而不是在客户端代码里判

## 实战验证结果

- 模块级：license 7 导出 + security 4 导出，逐一匹配原版
- 行为：`getState().activated===true`、`verify().code===0`、`activate('任意').code===0`
- main.js 启动模拟：fake Electron + 真实破解 gen 模块 + `Module._compile` 编译混淆 main.js，`app.exit` 打桩拦截闪退 → **未闪退，启动完成**
- 总计 23/23 通过（含 6 个临时分析脚本清理检查）

> 脱敏原则：本文不含真实密钥/凭据/服务器域名/哈希值。通用手法见 `client-encryption-bypass.md`；v2（含哈希）见 `xiaobaiyan-v2-obfuscated-crack.md`。