# Windows 子进程修复：STATUS_CONTROL_C_EXIT

## 症状

`subprocess.run` 在 Windows 上返回 **3221225794** (0xC000013A = STATUS_CONTROL_C_EXIT)，且 stdout/stderr 为空。

## 根因

父进程的 Ctrl+C 信号传播到子进程组。在 uvicorn/FastAPI 后端中，HTTP 请求处理期间如果触发 Ctrl+C（例如用户中断或其他信号），子进程会被意外终止，且 `text=True` 在 Windows 上的输出缓冲可能丢失。

## 修复

```python
import subprocess, os

proc = subprocess.run(
    [python_exe, script_path],
    cwd=str(workdir),
    capture_output=True,          # 不要 text=True
    timeout=300,
    env=env,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
)

# 手动 decode 避免 Windows text=True 输出丢失
stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
```

## 环境变量清理

```python
env = {**os.environ}
for k in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONUTF8", "PYTHONIOENCODING"):
    env.pop(k, None)
env["PYTHONUTF8"] = "1"
```

## 验证

- 直接运行（`env -u PYTHONPATH ... python script.py`）exit=1 正常，但 subprocess 返回 3221225794 → 需要加 `CREATE_NEW_PROCESS_GROUP`
- 手工 subprocess 测试（python -c 调用 subprocess.run）exit=1 正常但 workflow 里返回 3221225794 → 需要手动 decode