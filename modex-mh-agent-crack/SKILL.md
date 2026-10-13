---
name: modex-mh-agent-crack
description: "Crack Modex-MH-Agent API. Steps: py, heal, wrapper, ui."
license: MIT
---

# Modex-MH-Agent 破解方案

## 适用场景
Modex-MH-Agent 强制绑定 `mhcoding.xyz` API 网关，无法使用自定义模型。本方案解除此限制，支持任意 OpenAI 兼容端点。

## 核心问题 & 解法

### 1. API 绑定
`llm_client.pyd` 强制 base_url，`settings.pyd` 强制写入固定值。
**解法**：明文 `.py` 替换 `.pyd`（原 .pyd 保留 .bak）。

### 2. 启动自愈
`main.js` 的 `healBeforeBackend()` 校验 sha256 下载覆盖。`cleanupLeakedBackendSources()` 删除同名 .py。
**解法**：heal 开头 return + updater-config 断网 + PROTECTED 名单。

### 3. 子进程 env 覆盖（核心难点）
`claude_runner.pyd`（Cython 二进制）创建子进程时**显式传入自定义 `env={}`**，丢弃 `os.environ`。Monkey-patch 无效（`workflow_engine.pyd` 用 `cimport` 持有硬引用）。
**解法**：`claude.exe` 包装器（见下文）。

## 完整步骤

### 前置条件
- Modex-MH-Agent 已安装，用户有 `~/.claude/settings.json`（cc-switch）
- Python 3.12+，PyInstaller 6+

### 1. 替换后端模块
备份原 pyd，创建 `llm_client.py`（verify_endpoint_integrity 恒 True、_locked_url 可自定义、call_llm 读 settings、get_env_for_subprocess 返回 cc-switch env、模块级从 settings.json 和 aris.db 注入 env）和 `routers/settings.py`（不再强制 base_url）。

### 2. 禁用自愈
```javascript
// main.js
function healBeforeBackend() { return; }
function initUpdater() { return; }
const PROTECTED = new Set(['llm_client', 'settings', 'claude_runner']);
```

### 3. 禁用更新
```json
{ "server_url": "http://127.0.0.1:9", "check_interval_hours": 0 }
```

### 4. 编译 claude.exe 包装器（核心）
```python
# claude_wrapper.py — PyInstaller 编译为 .exe 替换原 claude.exe
import os, sys, json, subprocess, sqlite3
from pathlib import Path
WRAPPER_DIR = Path(sys.executable).parent.resolve()
REAL_CLAUDE = WRAPPER_DIR / "claude.exe.real"
# 1) 加载 cc-switch 配置
cc_cfg = Path.home() / ".claude" / "settings.json"
if cc_cfg.exists():
    try:
        with open(cc_cfg) as f:
            cfg = json.load(f)
        if "env" in cfg:
            for k, v in cfg["env"].items():
                if v is not None: os.environ[k] = str(v)
    except Exception: pass
# 2) 从预设数据库取真实 API key
try:
    db = Path(os.environ.get("APPDATA","")) / "MHAgent" / "db" / "aris.db"
    if db.exists():
        con = sqlite3.connect(str(db))
        row = con.execute("""SELECT p.api_key FROM model_presets p
            JOIN settings s ON s.value=p.id AND s.key='executor_preset_id' LIMIT 1""").fetchone()
        if row and row[0]: os.environ["ANTHROPIC_API_KEY"] = row[0]
        con.close()
except Exception: pass
# 3) 调用真实 claude.exe
if not REAL_CLAUDE.exists(): sys.exit(1)
try:
    proc = subprocess.run([str(REAL_CLAUDE)]+sys.argv[1:], env=os.environ)
    sys.exit(proc.returncode)
except Exception as e: print(f"Error: {e}", file=sys.stderr); sys.exit(1)
```

**部署**：
```bash
python -m PyInstaller --onefile --name claude_wrapper claude_wrapper.py
cd runtime/node/node_modules/@anthropic-ai/claude-code/bin
mv claude.exe claude.exe.real && cp dist/claude_wrapper.exe claude.exe
```

### 5. 前端加 Base URL 输入框
修改 `dist/assets/index-bqivY7Dt.js`：新增 Base URL 输入框，透传 base_url，全局保存不再强制固定值。

## 关键文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/services/llm_client.py` | 创建 | 替换 pyd，解锁 API |
| `backend/routers/settings.py` | 创建 | 替换 pyd，自由 base_url |
| `main.js` | 修改 | 禁 heal/updater + PROTECTED |
| `updater-config.json` | 修改 | 断网 |
| `index-bqivY7Dt.js` | 修改 | 前端 Base URL 输入框 |
| `bin/claude.exe` | 替换 | PyInstaller 包装器 |
| `bin/claude.exe.real` | 重命名 | 原 claude.exe 真身 |

## 验证

```bash
curl http://127.0.0.1:18088/api/health
curl -X PUT http://127.0.0.1:18088/api/settings \
  -H "Content-Type: application/json" \
  -d '{"settings":{"executor_base_url":"https://custom.api/v1"}}'
claude.exe --version && claude.exe -p "hi"
```

## 已知问题
- `claude -p` 不支持 `--model` 参数（cc-switch 代理处理映射）
- 技能文件解密需在线验证（不影响工作流执行）
- 工作流恢复后需重新选择预设