# 空响应静默完成诊断实录（2026-08-22 高教社杯任务）

## 现象
用户报：mrite 任务跑了几分钟自己"跑完了"，进度 100%、显示"所有任务已经完成处理"，但没有任何求解产物。

## 证据链（诊断顺序，可直接复用）

1. **工作区盘点** `%APPDATA%\Trigon Agent\mrite\workspace\<任务名>\`：
   - `task.json` 只有启动命令；`.mrite-ws.json` 是真正的状态文件。
   - `求解/` 里只有 数据预处理.py + 预处理数据.csv —— 有预处理、无求解计划正文、无 问题X 目录。
   - `论文/` 全是模板占位符（摘要还是 "...是...领域的重要研究课题"），157KB 的 论文.pdf 是模板骨架空壳编译，不是真论文。
2. **状态文件** `.mrite-ws.json`：status=completed / progress=100 / durationMs≈329s，但 `chatHistory` 最后一条 AI 消息 **text 长度 = 0**；倒数第二条是 "现在撰写详细求解计划…"。fileOps 显示只走到读 求解规范.md/求解计划.md。
3. **日志** `%APPDATA%\Trigon Agent\logs\mrite-YYYY-MM-DD.log`：
   - `SDK消息间隔 120032ms | type=assistant | step=13` —— 最后一个流事件后沉默整整 120 秒，然后到的是空 assistant 消息。
   - `[Task] 完成 | steps=13 | inputTok=241 | outputTok=3165` —— 引擎按成功收尾。
4. **导出目录** `E:\Project\<任务名>\`（exportResults 产物）：论文/ 里全是模板文件 → 证实 AI 根本没写任何内容。

## 根因（两层）
- 上游：openrouter stealth/ox-alpha 写长输出（求解计划）时流式中断，返回空 assistant 消息，SDK 判定回合 success 结束。偶发，网络/上游侧。
- 本地 bug：`src/services/task/runner.js` 的 `result` 分支只调 `getResultErrorMessage(msg)`——subtype=success 且 error 为空就一路 `markTaskCompleted(progress=100)`，**不校验最后一轮是否为空文本、产物是否存在**。空转被包装成正常完成。

## 修复方向（runner.js 两处）
1. `result` 处理分支加空结果校验：subtype=success 但最后一条 AI 文本为空 / 本轮 steps 无新增产物 → 不 markTaskCompleted，改发可重试错误（"模型返回了空响应，已停止"）。
2. 可选：检测到空响应时自动 resume 一次（1~2 次）再报错。

## 恢复手段
sessionId 已存 `.mrite-ws.json` → 界面点「继续」从断点续跑，预处理成果不丢。

## 排查口诀
先看工作区实际产物 → 再看 .mrite-ws.json 的 chatHistory 尾部（找 0 长度消息）→ 再看当日日志的 SDK消息间隔 大间隔条目 → 最后核对导出目录是否只是模板拷贝。"completed + 无产物" ≠ 跑完，是被静默掐断。
