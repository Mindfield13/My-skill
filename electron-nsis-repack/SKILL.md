---
name: "electron-nsis-repack"
description: "Analyze, patch, and repack Windows NSIS/Electron installers."
---

# Electron / NSIS Installer Analysis & Repack

Windows installers built by electron-builder (NSIS target) are a PE stub + `$PLUGINSDIR` payload (usually `app-64.7z`) containing the Electron runtime + `resources/app.asar`. You can analyze, patch and repack them without the original build machine.

## When to use
User hands you a `.exe` installer (most Electron Windows apps are NSIS) and asks to analyze it, fix a bug, restyle UI, or rebuild after source edits.

## Tools
- `7z` for NSIS/7z: `"/c/ProgramData/chocolatey/tools/7z.exe"` (install: `winget install 7zip.7zip`).
- `npx asar` for asar pack/extract.
- `makensis` for NSIS compile: `"C:/Program Files (x86)/NSIS/makensis.exe"` (install: `winget install NSIS.NSIS`).

## Analysis (read-only)

```bash
file "Setup.exe"                                  # → PE32 + Nullsoft Installer self-extracting archive
7z l "Setup.exe"                                  # → Type = Nsis, SubType = NSIS-3 Unicode; payload $PLUGINSDIR/app-64.7z
7z x "Setup.exe" -o_extracted/ -y
7z x "_extracted/\$PLUGINSDIR/app-64.7z" -o_extracted/\$PLUGINSDIR/app/ -y
npx asar extract "_extracted/\$PLUGINSDIR/app/resources/app.asar" app_content/
```

Typical layout: `main.js` (main process), `src/renderer.js`, `src/index.html`, `src/styles.css`, `gen/*` (engine/llm/chat), `preload.js`.

## Repack — the critical path

### 1. Patch source files
Edit files under `app_content/`. Also keep a copy in a `fix/` dir for diffing.

### 2. Repack asar
```bash
cd "_extracted/\$PLUGINSDIR/app/resources"
rm -f app.asar
npx asar pack app_content app.asar
```

### 3. Update the 7z payload — ⚠️ KNOWN PITFALL
`7z u archive file` does NOT replace-in-place at the correct path. It adds the file under the full CLI path you named (e.g. `app/resources/app.asar` alongside the old `resources/app.asar`), and the **old entry stays active** — the installer runs the OLD code.

**Correct sequence:**
```bash
# Delete stale entry, then stage at correct relative path
7z d app-64.7z "resources/app.asar" -y
mkdir -p _stg/resources && cp app.asar _stg/resources/app.asar
cd _stg && 7z a "../app-64.7z" "resources/app.asar" -y

# Verify only ONE entry exists
7z l ../app-64.7z | grep -i asar   # expect: resources\app.asar  (NOT app\resources\app.asar)
```

### 4. Compile NSIS
The `installer.nsi` script MUST be **UTF-8 with BOM** (`\xef\xbb\xbf` prefix) or makensis aborts with `Bad text encoding: installer.nsi:1`.

Use `!addplugindir "plugins"` pointing at the extracted `$PLUGINSDIR/*.dll`. Copy `app-64.7z`, `modern-wizard.bmp`, `icon.ico` into the build dir.

```bash
"C:/Program Files (x86)/NSIS/makensis.exe" installer.nsi
```

### 5. Verify the repack
**Never skip this step** — the 7z path pitfall can silently produce a broken installer.

```bash
7z e "Setup.exe" "app-64.7z" -o_vfy/ -y
cd _vfy
7z e app-64.7z "resources/app.asar" -y
npx asar extract app.asar _asar
grep -c "yourFixMarkerText" _asar/path/to/file.js   # expect ≥1
```

### 6. User communication: "你确定改了吗" prevention
After every repack, do TWO things:

1. **Verify the CHANGE is in the built installer** (not just the source file). Extract app.asar from the FINAL installer and grep for the fix marker — this is what the user's machine will actually run.
2. **Tell the user the installer path and that they must REINSTALL** to see the effect. Users who installed an earlier version may be looking at old screenshots. If the user asks "你确定改了吗" (are you sure you changed it?), the fix was verified in step 1 — confirm the installer path and ask them to reinstall.

```bash
# After repack, verify the built installer contains the fix
7z e "Setup.exe" "app-64.7z" -o_vfy/ -y
cd _vfy && 7z e app-64.7z "resources/app.asar" -y && npx asar extract app.asar _asar
grep "yourChange" _asar/src/styles.css
# → shows the line, confirming the change is in the installer
# Then tell user: "安装包已更新：path/to/Setup.exe，需要重新安装才能看到效果"
```

## Critical pitfalls

| Issue | Fix |
|-------|-----|
| Chinese paths break `strings`/`7z` | `cd` into dir + relative names, or Python `open(..., 'rb')` |
| `$PLUGINSDIR` in bash paths | Escape `\$PLUGINSDIR` or double-quote |
| `grep -c` exits 1 on 0 matches | Use separate commands, not `&&` chains |
| `7z u` adds at wrong path (see §3 above) | Delete old entry, stage at exact relative path |
| Hermes read_file shows `apiKey: apiKey...m()` | Tool display mask; verify with `repr(lines[n])` via execute_code |
| NSIS script `Bad text encoding` | Must be UTF-8 with BOM (`\xef\xbb\xbf`) |
| After repack, installer size changes | Expected — verify via grep, not size |
| `patch` tool + regexes with `\n` | `patch` can inject a REAL newline into a regex literal (e.g. `/\r?\n/` becomes broken). After any regex patch, `node --check` + re-read the line. Fix broken regexes with `execute_code` string replace, not another `patch`. |
| NSIS `ExecWait` 变量展开 | 用**双引号外层**包裹命令行，让 NSIS 在传参前展开 `$VAR`。单引号外层会保留字面 `$_7zPath` → 7z 找不到文件。**正确**：`ExecWait "$_7zPath x -y -ba $PLUGINSDIR\app-64.7z -o$INSTDIR" $0`。中文路径无需内嵌引号，双引号外层已足够。 |
| 中文路径下 `File` 命令静默跳过 | NSIS `File "X"` 在中文项目路径下可能**静默不报错、不嵌文件**（`-V1` 日志显示 0 字节），导致运行时找不到工具/载荷。修复：(1) 用 `-V2/-V4` 日志确认 `File:` 输出是文件真实大小（如 `7z.exe 358400 bytes`），不是 0；(2) 构建前把工具/载荷拷贝到**ASCII 路径 stage 目录**（如 `/tmp/xby_stage/`），`cd` 进去再 `makensis`；(3) 反编译最终 exe 用 7z `l` 命令核对嵌入文件数（应有 7z.exe + app-64.7z + icon.ico + unins.ico + app 目录）；(4) 永远**不用 `rm -f *.exe` 通配符**删除 exe，会误删 `7z.exe`。 |
| NSIS `RequestExecutionLevel none` + 默认目录 | 非管理员账号下 `CreateProcess` 报 `WinError 740`。改 `RequestExecutionLevel none` + `InstallDir "$APPDATA\app"`（per-user），无需提权即可静默安装。 |
| 沙盒/无 GUI 环境跑安装器失败 | `start /wait` 和 `ShellExecute(runas)` 在 Hermes 沙盒、headless、无桌面会话下**全部失败**。不要用 Python `subprocess.run(...installer)` 端到端验证。改用**离线模拟**：`7z x Setup.exe → 抽出 7z.exe + app-64.7z → 用抽出的 7z.exe 执行与 ExecWait 展开后完全相同的命令行 → 核对产物`。结果等价且稳定。 |

## Supporting references

- `references/electron-theme-toggle.md` — full pattern for `nativeTheme.themeSource`, `win.setTitleBarOverlay`, `html.theme-dark/.theme-light` CSS classes, `preload` IPC `theme:changed` channel, and dark-mode CSS pitfalls (e.g. `#batchParallel` missing selectors).
- `references/icon-alignment-pattern.md` — SVG icon baseline alignment fixes: `display: block` on SVGs, `inline-flex` on ghost buttons, `vertical-align: middle` on status dots, global `button svg` guard rule.
- `references/liquid-glass.md` — Apple Liquid Glass (macOS Sequoia 风格): pure `backdrop-filter: blur(20px) saturate(180%)` approach with `cubic-bezier(0.25,0.8,0.25,1)` transitions, `scale(0.98)` active states, per-component blur values, sidebar shadow separation, modal blur(40px), overlay rgba(0,0,0,0.4)+blur(5px), input focus white glow, dark mode rgba(30,30,30,0.65), and the required gradient+floating-light-spot body background.
- `references/segmented-control-pattern.md` — Apple segmented control for equal-width option groups: `gap: 0` track, transparent segments, floating selected state, `gap: 6px`+`padding: 6px 8px` for icon-text breathing room.