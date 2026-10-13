# `_venv_python()` 路径层级修复

## 问题

`workflow.py` 的 `_venv_python()` 方法 fallback 路径只能上2层，但实际需要上3层才能到项目根：

```python
# ❌ 旧代码
return str((self.task_dir / ".." / ".." / ".venv" / "Scripts" / "python.exe").resolve())
```

- `task_dir` = `data/tasks/<task_id>/`
- 上2层 → `data/`
- 拼 `.venv/Scripts/python.exe` → `data/.venv/...` ❌ 不存在

## 修复

改用 `config.PROJECT_ROOT` 绝对定位：

```python
return str((config.PROJECT_ROOT / ".venv" / "Scripts" / "python.exe").resolve())
```

`config` 已在文件顶部 `import config`，`PROJECT_ROOT` 在 `config.py` 定义为项目根目录。

## 验证

正确路径：`E:\Project\M Ultra\M-Ultra-数模\.venv\Scripts\python.exe` ✅