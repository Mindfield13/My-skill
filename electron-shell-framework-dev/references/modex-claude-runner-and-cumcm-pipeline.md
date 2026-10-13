# Modex claude_runner 执行链与 CUMCM 管道性能（实测诊断 2026-08）

实测对象：E:\Project\Framework（Trigon 壳 + modex + cumcm 组件）。所有结论来自读源码验证，非猜测。

## 1. Claude CLI 解析顺序（claude_runner）

候选列表（按序取第一个存在的）：
```
1. <安装目录>/runtime/node/node_modules/@anthropic-ai/claude-code/bin/claude.exe   ← 自带
2. %LOCALAPPDATA%/claude/claude.exe          ← 系统安装，仅兜底
3. %LOCALAPPDATA%/Programs/claude/claude.exe
```
Framework 里自带 v2.1.132 存在 ⇒ **实际永远用自带的**，与系统 Claude Code 互不影响。
runner 还会把 `.cmd` shim 换成同目录 `.exe` 直跑。

## 2. 子进程环境变量优先级（llm_client.get_env_for_subprocess + runner）

| 优先级 | 来源 | 行为 |
|---|---|---|
| ① 最高 | `~/.claude/settings.json` 的 `env` 块（cc-switch 写入） | 直接注入子进程，其他来源不覆盖同名变量 |
| ② | 软件 SQLite settings（aris.db `model_presets` / ENV_MAPPING 键） | 仅补 cc-switch 没设的 |
| ③ 兜底 | 代码常量 DEFAULT_BASE_URL（破解版默认 DeepSeek） | 两边都没配才用 |

关键细节：
- `get_env_for_subprocess` 会主动 `pop("ANTHROPIC_API_KEY")` 和 `OPENAI_API_KEY`（避免与 cc-switch 的 `ANTHROPIC_AUTH_TOKEN` 冲突），且循环后再次 pop。
- runner 内部又 copy(os.environ) 后再叠一层 cc-switch env —— 双保险走 cc-switch。
- **结论：CLI 执行器的模型切换只有 cc-switch 生效；软件内"自定义模型/预设"只影响 Python 内部 call_llm 路径（editor/reviewer 等辅助调用），管不到 CLI 子进程。**

cc-switch 配置实例（~/.claude/settings.json）：
```json
{"env": {"ANTHROPIC_BASE_URL": "http://127.0.0.1:15721",
         "ANTHROPIC_AUTH_TOKEN": "PROXY_MANAGED",
         "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-6[1M]", ...}}
```

## 3. 模板 model 名覆盖 cc-switch 映射的坑

cumcm_a.py 等模板写死 `Step(model="claude-sonnet")` / `model="gpt-4o"`；bridge 把它包成
`step_model={"model": ...}` 传入 run_skill，runner 设：
```
ANTHROPIC_DEFAULT_SONNET_MODEL = claude-sonnet   ← 覆盖 cc-switch 配的真实名
ANTHROPIC_DEFAULT_OPUS_MODEL  = gpt-4o           ← 代理没映射过这个名字
```
后果：该步骤绕开 cc-switch 模型路由，本地代理(127.0.0.1:15721)收到裸名字 → 落到兜底模型或重试。
修法：模板不传 model，或在 runner 里把别名映射为代理认识的真实模型名。

## 4. 会话延续断裂（纯浪费）

`run_skill` 有 `resume_session_id` 参数且结果返回 `session_id`，但 `modex_bridge.BridgeSkillRunner.run()`
从不传 resume ⇒ 每步全新 claude -p 冷启动、从零探索 workspace 重读上一步产物。

## 5. CUMCM 国赛管道慢的量化原因（按影响排序）

1. **每步冷启动 + 巨型 prompt**：串行逐步跑，每步一个新 claude.exe。comp 系列 SKILL.md 合计 ~9500 行
   （comp-paper-zh 1572 / paper-figure 1299 / comp-paper-zh-docx 1224 / comp-prob-analysis 952 /
   comp-code 765 / comp-modeling 555 …），12 步乘起来小时级是正常水位。
2. **无会话延续**（见 §4）。
3. **模板模型覆盖**（见 §3）→ 走慢的兜底路由。
4. **FAST_MODE 默认关**：skill 开头检测 workspace CLAUDE.md 里 `MH_FAST_MODE=1`；
   未设则完整模式（多方案对比推敲/灵敏度深挖/反复重写）。竞赛期间在 workspace 写一行即提速。
5. checkpoint=True 的步骤每处停下等人工确认（A 卷 8 处）。
6. auto-paper-improvement-loop 本身是循环技能。
7. 输出非流式：runner 用 communicate() 一把读完，UI 观感"卡住"，其实在跑。
8. TinyTeX 首次编译缺包现场装包，第一篇特别慢属正常。

## 6. "秒完成但无产物" = simulated 降级，不是快

workspace 只出现 `.checkpoint_*.json` 且内容 `"note":"simulated"` ⇒ modex_bridge.mount() 失败，
Pipeline._execute 走"无 SkillRunner → 模拟执行"分支（engine/__init__.py L234 附近）。
排查：后端启动日志找 `[modex_bridge] mount failed at <path>: <err>`；
常见原因是 sys.modules['config'] 抢注（bridge 已处理）或 .pyd 需要 py3.11 而 spawn 了错误 python。

## 7. 改进清单（性价比序）

1. bridge 传递 session_id → 下一步 resume_session_id。
2. 去掉模板写死的 model= 或做别名映射，保住 cc-switch 路由。
3. 竞赛时 workspace CLAUDE.md 写 `MH_FAST_MODE=1`。
4. 非关键步骤（figure_flow / quality-check）去 checkpoint 或降 quality。
