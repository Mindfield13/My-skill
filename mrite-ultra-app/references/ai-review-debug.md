# AI 深度评审 / AI 分析 调试记录

## 故障现象

点击"AI 深度评审"按钮后：
- 按钮变"评审中…"然后卡住 / 报"AI 未返回有效 JSON" / 无反应

## 诊断方法

当功能不工作时，**追踪完整调用链**，不要只修表面问题：

```
review.js → mrite-bridge.js (preload) → ipcRenderer.send('ai-analyze-latex')
  → project.js (main process) → fetch/Anthropic SDK → SSE stream
  → ai-fix-chunk/ai-fix-done events → review.js 解析 JSON
```

## 已知故障模式

### 1. 前端读错配置路径

`review.js` 和 `score.js` 从 `Mrite.STATE.settings.apiBase` 读取配置，但该字段默认空字符串。
实际配置存在 `Mrite.STATE.settings.apiModels[index]`（多 profile 结构），通过 `Mrite._getActiveApiConfig()` 获取。

**修复**：`settings.apiBase` → `(Mrite._getActiveApiConfig && Mrite._getActiveApiConfig()) || {}`

### 2. 后端硬编码 Anthropic SDK

`project.js` 的 `ai-analyze-latex` handler 只用 `@anthropic-ai/sdk`，但用户可能用 OpenAI 兼容端点（DeepSeek、Qwen、自定义等）。

**修复**：检测协议分支：
- Anthropic 协议（`api.anthropic.com`、`/anthropic`、模型名含 `claude`）→ Anthropic SDK
- OpenAI 协议 → `fetch` + `POST /v1/chat/completions` + SSE 流式解析

### 3. 推理模型特殊处理

推理模型（DeepSeek R1、商汤 flash-lite 等）的 SSE 流中：
- `delta.content` 在思考阶段为 null
- `delta.reasoning` 在思考阶段有内容
- 最终 JSON 输出在 `delta.content` 中（思考完成后）

**修复**：`const chunk = delta.content || delta.reasoning` 两个字段都纳入

### 4. JSON 被代码块包裹

模型可能输出 ` ```json\n{"key": "value"}\n``` ` 格式。

**修复**：先 `replace(/```(?:json)?\s*/gi, '').replace(/\s*```/g, '')` 剥代码块，再正则提取 JSON

### 5. max_tokens 不足

推理模型需要更多 token 用于思考链。`max_tokens: 4096` 可能不够，至少 8192。

### 6. 按钮卡住无响应

`ipcRenderer.send('ai-analyze-latex', ...)` 是 fire-and-forget，如果 main process handler 未注册或崩溃，`ai-fix-done` 事件永远不会发出，Promise 永不 resolve，按钮永远显示"评审中…"。

**修复**：重启 Trigon Agent（main process 代码需要重启才能载入）。

## 调用链

```
review.js:
  startAiAnalyze(prompt, apiBase, apiKey, apiModel)  ← 传入配置
  → ipcRenderer.send('ai-analyze-latex', {prompt, apiBase, apiKey, apiModel})
  → onAiFixChunk(fn) / onAiFixDone(fn)  ← 订阅事件
  → Promise 等待 done 事件

project.js (main process):
  ipcMain.on('ai-analyze-latex', ...)
    → 判定 isAnthropic
    → Anthropic SDK / fetch SSE
    → sender.send('ai-fix-chunk', {delta, fullText})
    → sender.send('ai-fix-done', {text: fullText, success: true})

mrite-bridge.js (preload):
  startAiAnalyze: ipcRenderer.send('ai-analyze-latex', ...)
  onAiFixChunk: ipcRenderer.on('ai-fix-chunk', callback)
  onAiFixDone: ipcRenderer.on('ai-fix-done', callback)
```