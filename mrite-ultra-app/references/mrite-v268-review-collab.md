# Mrite v2.6.8 独立版：破解字段 + 评审中心扩展 + 局域网协作解锁（2026-08-27 实录）

> 应用：`E:\Project\Mrite\Mritev2.6.8\`（明文"开源版" v2.6.0，账号登录制）。
> 破解明细属 electron-app-crack-analysis 领域（该技能为用户自有，无法补丁），本篇记录与 Mrite 家族直接相关的扩展/评审/协作实现，后续改 v2.6.8 先读此文件。

## 1. 关键路径与状态

- userData = `%APPDATA%\MriteUltra-2.6.0\`（bootstrap.js `app.setPath('userData', ...MriteUltra-<version>)`，version 取 package.json = 2.6.0）
- 工作区：`userData\workspace\` + `userData\Workspace-Extend\` + 设置 outputPath（本次实测输出在 `E:\Project\Mrite\output\高教社杯_2026-08-25_22-54-27\`）
- **扩展 = 物理目录** `resources\extensions\builtin\<id>\`：`src/services/extension.js` 的 `getBuiltinDir()` = `path.join(process.resourcesPath, 'extensions', 'builtin')` → 新增内置扩展直接丢物理目录即可，**不重打包 asar**。（asar 内也有一份 extensions/ 副本，仅冗余）
- 内置扩展：write（host，LaTeX 工坊宿主）、draw（X6 流程图）、code（代码工作台）、review（本次新增评审中心）
- 扩展中心"开发中"占位卡：`renderer/toolbar.js` 的 `_placeholderRegistry`（无 main.js 纯 UI 桩），后端引用 0 即占位

## 2. 评审中心扩展（从 Trigon Framework 移植）

**后端（进 asar，需重打包）**：
- `src/services/score.js` — 纯 Node 评分引擎（无 electron 依赖，可独立 node -e 单测）：
  - 7 维 × 85 分：摘要15/结构15/图表12/编译15/求解12/支撑10/合规6
  - `_normLocal` 校准：local≥81 → 64+(t-81)/4*21；≥70 → 46+…；否则 t/70*46
  - 缓存 `工作区/.mrite-score.json`，**SCORE_VERSION 版本戳**（规则变更 +1，loadCached 版本不符自动重算——用户改评分规则后必须这样做）
  - `collectAiContext`：walk 3 层，论文 14KB + 源码 10KB 预算，中文<30 字跳过、500B 以下代码跳过
  - `scanWorkspaces(roots)` 按名去重、需含 论文/ 或 求解/
- `src/ipc/score.js` — IPC：`score-workspace`（缓存优先）/ `score-workspace-force`（论文.log 缺失 → notReady 拦截）/ `score-list` / `score-scan-all` / `score-ai-context` / `score-apply-ai` / `review-ai-analyze` / `score-get-roots`
- AI 调用：读 `ctx.db.getAllSettings()` → `apiModels[_activeModelIndex]`（fallback 扁平 apiBase/apiKey/apiModel）→ `isAnthropicEndpoint(baseURL, format)`（task/prompt 导出）分支 Anthropic `/v1/messages`（x-api-key + anthropic-version）或 OpenAI `/chat/completions`（Bearer）；非流式 180s 超时，返回 {success, text}

**前端（扩展 main.js）**：
- 注册：`window.MriteExtension.review = { id, activate(api, hostEl), deactivate() }`；工坊 dispatcher `_writeSwitchMode` 自动建 `writeMode_review` 容器并调 activate
- 数据源 = `window.electronAPI.scoreScanAll/scoreWorkspace/scoreAiContext/reviewAiAnalyze/scoreApplyAi`（preload 暴露）
- AI prompt 照搬 Framework review.js：四维 reasonable/correct/innovate/express 0-100 + comment + suggestions（3-6 条精确到文件/章节/脚本），防虚高段（国一国二 0.48%/1.96%）
- 加权：本地 35% + AI 65%（w: 0.20/0.30/0.30/0.20）→ final

**评分规则（用户 2026-08-27 定稿，改回会挨批）**：
1. **摘要正文长度不限**（删 250-700 区间判定，有内容即满分项）
2. **页数记录缺失不扣分**（`论文.mritepages` 缺失/不完整 → 中性项 "不计分扣"）
3. **30 页限制只判正文，附录不计入**；无 mritepages 时**不得**拿 论文.log 总页数（含附录）套 30 页上限——只作信息展示给满分，防止正文 26 页+附录 9 页被总页 35 误判超限

## 3. 局域网协作解锁（v2.6 预览版 UI 门禁）

- 后端完整：`collab-server.js`（WS 0.0.0.0:45231 起，占位顺延 +10；UDP 发现 45232；MAX_MEMBERS=4；文件锁/保存广播/编译投票 60s 超时/共享区 Workspace-Share/25MB 上限）+ `collab-client.js`。**无 license 门禁**（只认 6 位协作码）
- UI 两处门禁（`renderer/panels/collab.js`）：
  1. `_collabSwitch('collab')` 原 `_collabSetSwitch('solo') + toast '当前协作功能暂未开放'` → 改为 `Mrite._collabAutoHost()`（有开项目自动建房，无项目打开创建房间弹窗）
  2. `_collabSettingsNav('collab')` 原渲染"暂未开放"占位 → 删分支走通用逻辑，加 `if (pane==='collab') Mrite._collabRenderStatusPane()`
- 验证协议（不改应用，raw WS 客户端即可）：
  - 启动 `--remote-debugging-port`（**v2.6 注释说已移除反调试但 `applySecurity` 仍查此参数，需先 `if(false)` 包掉**）
  - CDP 调 `collabHostStart({projectName, projectPath, texFile, code, name})` → 得 wsPort
  - Node 原生 WebSocket 连接：先收 `hello-required` → 错码回 `error{AUTH_FAIL}`、对码回 `welcome{memberN}` + `project-snapshot{files}` → `request-lock` 回 `lock-granted` → `save-file` 落主机磁盘验证
  - 单机双开：`--multi-instance` 启动第二实例（独立 userData + 跳过单实例锁），可直接验证双端 UI

## 4. 内测（Beta）功能解锁 + 后端接线（同一类 UI 门禁）

设置里 5 张"内测中"卡（图表配色/摘要风格/参考文献/流程图风格/量化约束）原是纯 UI 桩（cfg-card-locked + toggle 无 checkbox + 后端零引用）：
- 前端：解锁 HTML（真 checkbox + 可点 chip data-val + qc-num 输入）；`_onSolveToggle` map 加 5 key；新增 `_pickSolveChip(group,el)`、`_renderBetaSolveConfig()`、`_autoSaveSettings` 读 8 个 qc 值；`storage.js renderSettings` setChk + 调恢复
- 后端：`src/core/database.js` 把 18 个新 key 加入 `PLAINTEXT_SETTING_KEYS`（否则密文写进 CLAUDE.md 变乱码）；`src/services/task/index.js` 赛题信息块（生成风格同款接入点）把开启项映射成具体指令注入 CLAUDE.md `## 内测功能配置`（配色→matplotlib 色系、摘要→3 种写法、参考文献→GB/T7714/APA/IEEE、流程图→3 种画法、量化→页数/图/公式/表区间）

## 5. 踩坑备忘

- Hermes 对 API key 类字段脱敏成 `*** `：patch 照抄会写入字面 `***` → `Unexpected token '**'`。修复：`/apiKey: \*\*\* / → apiKey: '',`；改完每个文件 `node --check`
- 残留进程占单实例锁：`tasklist | grep Mrite` + `MSYS_NO_PATHCONV=1 taskkill /F /PID <pid>`（`//F` 会被 MSYS 路径转换坑掉）
- 重打包 asar 后验证补丁：手动解析 header（`indexOf('{"files"')` → u32@idx-4=jsonLen → u32@4=P → 负载基址 8+P），不要用 asar 库 extractFile（对有歧义条目会 TypeError