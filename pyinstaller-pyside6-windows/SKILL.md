---
name: pyinstaller-pyside6-windows
description: 用 PyInstaller 打包 PySide6 应用在 Windows 上的模式。
---

# PyInstaller 打包 PySide6 应用（Windows）

覆盖 PySide6/PyQt6 桌面应用打包为独立 .exe 的完整模式，包括资源路径解析、路径陷阱、PySide6 特有坑、安装/卸载程序打包。

## 核心模式：frozen 检测 + _MEIPASS

PyInstaller 打包后的 exe 会把资源解压到临时目录 `_MEIPASS`，代码运行时不再在磁盘上。**所有资源访问必须用 `frozen` 判断**：

```python
if getattr(sys, "frozen", False):
    _SELF_DIR = os.path.dirname(os.path.abspath(sys.executable))
    _ASSET_DIR = getattr(sys, "_MEIPASS", _SELF_DIR)
else:
    _SELF_DIR = os.path.dirname(os.path.abspath(__file__))
    _ASSET_DIR = _SELF_DIR

# 资源（图片/图标/数据）从 _ASSET_DIR 读
ICON_PATH = os.path.join(_ASSET_DIR, "图标.ico")
# 可执行文件从 _SELF_DIR 找
MAIN_EXE = os.path.join(_SELF_DIR, "主程序.exe")
```

`_ASSET_DIR` 和 `_SELF_DIR` 是两个概念：
- **`_SELF_DIR`**：exe 运行的目录，同目录下可以放其他 exe（安装程序找主程序用）
- **`_ASSET_DIR`**：PyInstaller 解压资源的临时目录，图片和数据在这里

## Spec 文件中的 `__file__` 陷阱

⚠️ **Spec 文件中 `__file__` 不可用**（NameError）。Spec 文件由 PyInstaller 直接 `exec`，没有 `__file__` 变量。

```python
# ❌ 报错
_BASE = os.path.dirname(os.path.abspath(__file__))

# ✅ 正确
_BASE = os.getcwd()
```

所有路径用绝对路径拼接：
```python
a = Analysis(
    [os.path.join(_BASE, '主程序.py')],
    datas=[(os.path.join(_BASE, '图标.ico'), '.')],
)
exe = EXE(..., icon=os.path.join(_BASE, '图标.ico'))
```

## PySide6 特有坑

### `QColor(name, alpha)` 不工作

`QColor("#F5F5F7", 220)` 在 PySide6 中抛 TypeError：

```python
# ❌ TypeError
QColor("#F5F5F7", 220)
# ✅ 正确
QColor(245, 245, 247, 220)
```

### `hiddenimports` 必须声明

```python
hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
```

### ⚠️ HTTPS 网络请求必须声明 ssl/urllib hiddenimports + 源码顶部 import

**症状：** 源码直接运行能联网，但打包后的 exe 里 `urllib.request.urlopen("https://...")` 报 `<urlopen error unknown url type: https>`，天气/API 全部失败。

**根因：** PyInstaller 未自动收集 `ssl` 模块，exe 里 HTTPS handler 缺失。这是打包后才暴露的坑——本地跑源码永远测不出来。

**修复（两步，缺一不可）：**

**第 1 步：** `hiddenimports` 里显式加上网络栈：

```python
hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
               'ssl', '_ssl', 'urllib.request', 'urllib.parse', 'socket',
               'http.client', 'email'],
```

**第 2 步（容易被忽略）：** 源码顶部**必须**有 `import ssl` 和 `import urllib.request`。仅靠 `hiddenimports` 可能不够——PyInstaller 收集了 ssl 模块的文件，但运行时 `urllib` 的 HTTPS 处理器需要 `ssl` 被主动 import 后才能注册。如果源码只在函数内部 `import urllib.request`（懒加载），处理器可能来不及注册。

```python
# 在源码顶部，和 import json, import os 等一起：
import ssl
import urllib.request
import urllib.parse
```

用 `urllib` 拉取天气、API 的应用都要加。**验证时必须在打包后的 exe 上测，不能只跑源码。**

### excludes 减少 exe 体积

```python
excludes=['matplotlib', 'numpy', 'PIL', 'cv2'],
```

## 安装/卸载程序打包规范

- **安装程序**用 `_SELF_DIR` 找主程序 exe（`MAIN_EXE = os.path.join(_SELF_DIR, EXE_NAME)`）
- **主程序**用 `_ASSET_DIR` 找图片/音效/数据
- **卸载程序**复制到安装目录（`%LOCALAPPDATA%\\应用名\\`），注册表 `UninstallString` 指向它
- 打包时 `datas` 只包含图标等静态资源，不要包含 exe 本身

### 卸载程序必须加 `uac_admin=True`

**没有这个标志，控制面板会报"没有足够的权限卸载"：**

```python
exe = EXE(
    ...
    uac_admin=True,   # 必须加，否则控制面板无法调用卸载程序
)
```

`uac_admin=True` 在 exe 的 PE 头中添加 `requestedExecutionLevel="requireAdministrator"` 的 UAC 清单，控制面板在调用卸载程序时会先弹 UAC 确认窗口。

### 注册表写入 HKCU 不需要管理员权限

`HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\YourKey` 的写入不需要管理员权限，只影响当前用户。这是个人桌面应用的标准做法，不要用 HKLM。

### 运行时智能检测管理员身份（推荐模式）

不要硬编码写 HKCU 还是 HKLM，也不要通过 `uac_admin=True` 强制提权。在安装器启动时用 `is_admin()` 检测，动态决定路径和注册表位置：

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

# 注册表写入跟随：
hive = winreg.HKEY_LOCAL_MACHINE if is_admin() else winreg.HKEY_CURRENT_USER
key = winreg.CreateKey(hive, UNINSTALL_REG_KEY)

# 自启动跟随：
hive = winreg.HKEY_LOCAL_MACHINE if is_admin() else winreg.HKEY_CURRENT_USER
key = winreg.CreateKey(hive, RUN_REG_KEY)

# 快捷方式跟随：
if is_admin():
    desktop = os.path.join(os.environ.get("PUBLIC", "C:/Users/Public"), "Desktop")
else:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
```

**安装器不要加 `uac_admin=True`**，否则非管理员用户无法运行安装器。让安装器以当前用户身份运行，在运行时检测权限并决定策略。

### 默认安装路径用 `%LOCALAPPDATA%`

不要用 D 盘或 C 盘根目录作为默认路径——这些位置可能需要管理员权限。`%LOCALAPPDATA%` 是当前用户目录，始终可写：

```python
default = os.environ.get("LOCALAPPDATA") or os.path.join(
    os.path.expanduser("~"), "AppData", "Local")
```

### ❌ 提权复制模式（`--copy-only`）——已废弃，不再使用

**本模式会导致永久性卸载权限陷阱，禁止使用。** 文件在受保护目录（Program Files）但注册表写 HKCU → 非管理员用户无法删除。应改为运行时 `is_admin()` 检测，智能选择安装路径和注册表位置（详见 `references/windows-installer-privilege-architecture.md`）。

### 控制面板卸载流程

```
控制面板 → 点击卸载 → UninstallString → 卸载程序.exe → UAC确认 → 卸载UI界面 → 删除文件/清理注册表
```

### 静默卸载模式

`QuietUninstallString` 指向 `--quiet` 参数，用于自动化卸载。`--quiet` 模式下不显示 UI，直接执行卸载操作：

```python
if "--quiet" in sys.argv:
    do_uninstall()
    time.sleep(2.5)  # 等待自删命令完成
    sys.exit(0)
```

## 已移除的功能

### PyInstaller 6.0+ 移除了 `--key` 加密

`--key` AES 字节码加密在 PyInstaller v6.0 中被移除（https://github.com/pyinstaller/pyinstaller/pull/6999）。替代方案：
- **PyArmor**（`pip install pyarmor`）—— 专业源码保护，但试用版限制大脚本（~1000行以上需商业许可证）
- 无加密方案时，PyInstaller 仍编译 .py 为 .pyc 字节码，源码不在 exe 中

## 常见错误排查

| 错误 | 原因 | 修复 |
|---|---|---|
| `FileNotFoundError: 图标.ico` | 硬编码相对路径，没做 frozen 判断 | 加 `_MEIPASS` 路径 |
| `NameError: __file__` | spec 文件用了 `__file__` | 改用 `os.getcwd()` |
| `TypeError: QColor.__init__` | `QColor(str, int)` | 改 `QColor(r,g,b,a)` |
| `ImportError: No module named PySide6.QtCore` | spec 缺 hiddenimports | 加 PySide6 模块 |
| steps 为空除零 | 打包后代码找 `dist/` 但资源在 `_MEIPASS` | 用 `_SELF_DIR` |
| 打包后 HTTPS 请求失败 `<urlopen error unknown url type: https>` | PyInstaller 漏了 `ssl` 模块 | `hiddenimports` 加 `ssl`, `_ssl`, `urllib.request`, `urllib.parse`, `socket`, `http.client`, `email` |