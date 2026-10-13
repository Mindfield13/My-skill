# Windows 启动脚本对比

## 为什么 .bat 比 .ps1 更常用

| 特性 | .bat | .ps1 |
|------|------|------|
| 双击即用 | ✅ 是 | ❌ 需先 `Set-ExecutionPolicy` |
| 环境变量清除 | `set VAR= && cmd /c "..."` | `$env:VAR=""` |
| 后台启动 | `start /min cmd /c` | `Start-Process -WindowStyle Hidden` |
| 等待就绪 | `:wait 循环 + curl` | `Start-Sleep` 或 `while` 循环 |
| Electron 启动 | 完整路径 `electron.exe` | `Start-Process "electron.exe"` |

## 常见失败原因

1. **`start` 工作目录不对** → `start` 新窗口默认 `%windir%`，用 `start /d "DIR"` 或硬编码路径
2. **`start` 不认识 `.cmd`** → 用 `.exe` 完整路径
3. **环境变量没清除** → `set` 在 `start` 的父进程里无效，必须写在 `cmd /c "set ... && command"` 同一行
4. **Electron 启动后立即退出** → 检查 `package.json` 的 `main` 字段，或工作目录是否有 `package.json`
5. **端口被占用** → 旧进程没杀干净，先 `taskkill /F /IM electron.exe` 再启动
6. **curl 在 Windows 上不存在** → 用 `timeout` 代替等待，或写 Python 脚本做 health check