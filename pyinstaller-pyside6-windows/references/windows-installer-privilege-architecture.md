# Windows 安装/卸载程序权限架构（控制面板"没有足够的权限卸载"根因）

从川建国督学桌宠（PySide6 桌面宠物）反复调试「控制面板无法卸载」学到的完整教训。

## 症状

控制面板 → 程序和功能 → 选中应用 → 点卸载 → 立即弹窗：
**"没有足够的权限卸载 川建国督学桌宠。请与系统管理员联系。"**

这个错误发生在**卸载程序执行之前**——控制面板自己就拒绝了，不是卸载程序报的。

## 两个独立的根因（先诊断再处理）

### 根因 1：残留的脏注册表项

卸载程序文件已被手动删除，但注册表 `Uninstall` 键还在，`UninstallString` 指向不存在的文件。控制面板找不到可执行文件 → 报"没有权限"。

- 诊断：枚举注册表键，检查 `UninstallString` 指向的文件是否存在
- 修复：删除残留注册表项

### 根因 2（真正的陷阱）：安装路径和注册表位置不配对

文件装在**受保护目录**（`C:\Program Files` / `D:\Program Files x86\` 等），但卸载注册表写在 **HKCU**（当前用户）。当前用户不是管理员时：

- 控制面板检测到目标文件无法删除（在受保护目录）
- **在调用卸载程序之前**就拒绝 → 报"没有足够的权限卸载"
- 卸载程序的 `uac_admin=True` 标志**没有任何作用**，因为卸载程序根本没被启动

这是旧版安装程序用 `--copy-only` 提权复制文件（文件→Program Files，注册表→HKCU）造成的。

## 核心原则：安装路径决定注册表位置，必须配对

| 当前用户 | 安装路径 | 注册表 | 快捷方式 | 安装器 spec |
|---|---|---|---|---|
| 非管理员（标准用户） | `%LOCALAPPDATA%` | **HKCU** | 当前用户桌面 | 不加 `uac_admin` |
| 管理员 | `%ProgramFiles%` | **HKLM** | 公共桌面 | 不加 `uac_admin` |

**安装器不要加 `uac_admin=True`**，否则非管理员无法运行。运行时用 `is_admin()` 检测，动态决定路径和注册表位置：

```python
def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def default_install_root():
    if is_admin():
        return os.environ.get("ProgramFiles") or r"C:\Program Files"
    return os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local")
```

注册表写入 + 自启动 + 快捷方式都跟随 `is_admin()`：

```python
hive = winreg.HKEY_LOCAL_MACHINE if is_admin() else winreg.HKEY_CURRENT_USER
key = winreg.CreateKey(hive, UNINSTALL_REG_KEY)
```

## 推荐方案：运行时智能检测管理员身份（最完整）

对个人桌面应用最简单、最稳，全程无需管理员权限，控制面板卸载天然正常。

```python
def default_install_root():
    return os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local")
```

## 安装前必须前置检测目标目录可写性

**不要**等复制文件时才捕获 `PermissionError`。点击"开始安装"就先写探针文件：

```python
def _start_install(self):
    root = self.path_edit.text().strip()
    self.install_dir = os.path.join(root, APP_FOLDER)
    try:
        probe = os.path.join(root, ".probe.tmp")
        with open(probe, "w") as f: f.write("ok")
        os.remove(probe)
    except OSError:
        self._on_permission_error()   # 引导换到 %LOCALAPPDATA%
        return
    self.stack.setCurrentIndex(1)
    QTimer.singleShot(150, self._install_worker)
```

不可写时弹窗明确警告，让用户理解后果，并提供一键切换到推荐位置：
```
"所选位置为受保护的系统目录，需要管理员权限才能安装。
装到受保护目录会导致日后无法通过控制面板卸载。
建议安装到用户目录（无需管理员权限）：%LOCALAPPDATA%\...
点「是」使用推荐位置，点「否」返回重选。"
```

## 已废弃：`--copy-only` 提权复制模式

**不要**用 `ShellExecuteExW(verb="runas")` 提权复制文件到受保护目录但注册表留在 HKCU。这是本会话反复出现的卸载权限问题的唯一根因。应删除 `--copy-only` / `_elevated_copy` 死代码。

## 卸载程序排查脚本（诊断优先）

写一个独立脚本枚举所有卸载注册表位置 + 检查文件存在性 + 检查管理员状态：

```python
locations = [
    ("HKCU(64)", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM(64)", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM(32)", winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]
# 对每个 key：枚举子键 → 找 DisplayName/UninstallString/InstallLocation
# 检查 UninstallString 指向的文件 exists？
# 检查 InstallLocation 目录 exists？
# 打印 IsUserAnAdmin()
```

安装目录可能在：`%LOCALAPPDATA%`、`%APPDATA%`、`D:\Program Files x86\`、`C:\Program Files\`、`C:\Program Files (x86)\`、D:/E: 盘根目录（旧版默认路径）。

## 强制清理脚本（给用户 + 自提权）

```python
def is_admin():
    return bool(ctypes.windll.shell32.IsUserAnAdmin())

def relaunch_elevated():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                        f'"{__file__}"', None, 1)
```

管理员权限下：删除 HKCU+HKLM 卸载键、删除 Run 值、删除所有候选安装目录（含 Program Files）、删除快捷方式。

**把清理脚本交给用户**——他们可能已手动删了文件，只留下孤儿注册表键。

## 卸载程序要同时读/删 HKLM 和 HKCU

```python
for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
    try:
        key = winreg.OpenKey(hive, UNINSTALL_REG_KEY, 0, winreg.KEY_READ)
        reg_dir, _ = winreg.QueryValueEx(key, "InstallLocation")
        winreg.CloseKey(key)
        if reg_dir:
            break
    except FileNotFoundError:
        continue
```

## 配套坑（同会话验证）

- **`setWindowFlag` 在可见窗口上重建原生窗口**：先 `hide()` → 存 pos → 改标志 → `move(pos)` → `show()`，否则面板消失。
- **子进程弹窗**：所有 `subprocess.run/Popen` 加 `creationflags=0x08000000`（`CREATE_NO_WINDOW`）。
- **进程不退出**：Qt 玻璃动画 `QVariantAnimation(loopCount=-1)` + `_bg_timer` 让窗口关闭后进程残留。`closeEvent` 里调 `stop_glass()`。
- **`QWidget` 没有 `exec()`**：`AppleStyleInputDialog(GlassWidget)` 调 `dlg.exec()` 静默无效，用本地 `QEventLoop` 的 `_exec()` + `destroyed.connect(loop.quit)`。