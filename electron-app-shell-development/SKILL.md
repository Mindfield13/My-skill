---
name: electron-app-shell-development
description: Build Electron host-shell apps, themes, model providers.
---

# Electron Host-Shell App Development (Windows)

Use when building or continuing an Electron "shell" app that hosts multiple sub-apps (WebContentsView slots), 3-mode theming, a preload bridging API, or a model-provider module — and when smoke-testing Electron on Windows. Modeled on the Trigon Agent framework (see `references/trigon-agent-framework.md` for that project's concrete layout).

## 1. Core architecture (proven pattern)

- **Shell chrome in own BrowserWindow + one WebContentsView per app**: sidebar/titlebar live in the shell's DOM; each app is a `WebContentsView` with bounds = content area (e.g. `{x:74, y:31, w-74, h-31}` for 74px icon nav + 31px titlebar). Keep a `Map id→view`; bring to front by `contentView.removeChildView(old)` then `addChildView(next)` (never destroy/recreate).
- **Manifest registry**: `src/apps/<id>/manifest.json` → `{id, name, icon, entry, main?, order, wallpaper}`. `main` is a module `module.exports = ({app, api}) => api('method', handler)` that registers app-scoped IPC handlers.
- **One preload for shell + all app views**: app identity via `webPreferences.additionalArguments: ['--host-app=<id>']`, read with `process.argv.find(a => a.startsWith('--host-app='))`.
- **Theme broadcast**: `nativeTheme.themeSource = settings.theme` (light|dark|system); broadcast `{mode, effective}` to all registered webContents; pages set `document.documentElement.dataset.theme = effective`. In system mode, re-broadcast on `nativeTheme.on('updated')`.
- **Inject design tokens into ported apps**: `webContents.insertCSS(tokens.css)` + `insertCSS(glass-app.css)` on `dom-ready` — apps get tokens/CSS classes without touching their code (later-injected style wins the cascade).
- **Wallpaper**: `insertCSS('html.<wall-class> body{background-image:url("' + pathToFileURL(bg).href + '");...}')` — always pathToFileURL for paths that may contain Chinese/spaces.

## 2. Preload bridge — THE contextBridge name-collision pitfall

`contextBridge.exposeInMainWorld('trigon', api)` creates a **non-configurable restricted global property** on `window`. Any page top-level `const trigon = window.trigon;` then throws:

```
Uncaught SyntaxError: Identifier 'trigon' has already been declared
```

(ECMAScript `HasRestrictedGlobalProperty`.) Fix: page scripts must use a DIFFERENT identifier — `const host = window.trigon;` — and reference `host.*` throughout (rename with `patch` + `replace_all`). This affects every ported app; document the rule in the porting guide.

Other bridge rules: `contextIsolation:true, nodeIntegration:false, sandbox:false`; route ALL calls through one `ipcMain.handle('host:invoke', (e, {app, method, args}))` dispatcher; app-scoped handlers checked BEFORE global handlers. Declare app-scoped handlers with flat positional args (`handler({appId, args, sender})`, `args[0]=first arg`) — callers must NOT wrap arguments in an extra array or `args` comes back double-wrapped.

## 3. Windows automated smoke testing (file-based evidence)

On Windows **electron.exe is a GUI-subsystem executable — stdout often never reaches bash pipes**, and wrapper `$?` can report 0 for a lock-quit. Never trust console output or exit code alone.

Verified workflow:
1. All evidence to FILES: `progress.log` (appendFileSync), `results.json` (PASS/FAIL array), screenshots.
2. Run electron with `ELECTRON_ENABLE_LOGGING=1` to surface renderer console errors.
3. **Stale-process check before every run**: a timed-out foreground run leaves `electron.exe` holding `app.requestSingleInstanceLock()`; the next run quits instantly with exit 0, faking success. Check `tasklist | grep -i electron`; kill with `MSYS_NO_PATHCONV=1 taskkill /F /T /IM electron.exe` — SINGLE slashes; `//F //IM` (double) silently fails in git-bash.
4. End smoke with `process.exit(fail?1:0)` — NOT `app.exit()` (unreliable at terminating on Windows in practice). Wrap EVERYTHING in try/catch that writes results + exits, plus a global watchdog (`setTimeout` 100s → process.exit(1)).
5. `waitFor(fn)` must race each poll iteration: `Promise.race([Promise.resolve().then(fn), sleep(800).then(()=>'TIMEOUT')])` — a bare `await fn()` inside the loop hangs FOREVER if `executeJavaScript` never resolves, so the outer timeout never fires.
6. **Phantom-PASS trap — never pass a bare FUNCTION into `Promise.race`.** `Promise.race([async () => {...}, killer])` treats the non-thenable function as an immediately-FULFILLED value, so `await` returns the function object itself (truthy!) — the body never runs, no log lines, no artifacts, and the check still reports PASS. Guard every timeout wrapper: `function withTimeout(p, ms, tag){ if (typeof p === 'function') p = p(); ... }`. Diagnostic when a check PASSES too instantly with ZERO log lines from inside the promise body and ZERO artifacts: the body never executed — the harness lied, not the app. Keep forensic markers in the smoke script (module-load line `log('FILE=' + __filename + ' size=' + fs.statSync(__filename).size)`, `CALL`/`ENTER` log lines before each step) so a future hunt can prove exactly which code ran.

## 4. Full-window screenshots including WebContentsView overlays

- **`win.webContents.capturePage()` does NOT capture WebContentsView overlays** — only the shell's own DOM.
- Use `desktopCapturer.getSources({types:['window'], thumbnailSize})`, then match source by `s.name === win.getTitle()` (fall back to `s.id === 'window:'+win.id`, then any `window:` source). Keep the window `show()`+`focus()`ed.
- **Pitfall (Electron 43.4.0)**: `webContents.getMediaSourceId()` throws `Insufficient number of arguments` (native binding bug) — avoid it; title/name matching is probe-verified.
- **Always read-back verify screenshot writes**: `fs.existsSync(file) && fs.statSync(file).size > 0` — an unverified "success" can silently produce NO file and destroy visual evidence (seen this session: checks PASSed, files absent).
- Wrap desktopCapturer in a timeout in case it hangs.
- **Capture APIs are machine/version-specific — probe first, verify with pixels.** On this machine (Electron 43.4.0/Windows): shell `win.webContents.capturePage()` gave real 3.1MB frames (wallpaper+glass); `desktopCapturer` name-matched thumbnails were real for PLAIN windows but ~99.8% BLACK (36KB @2560×1604) for the window WITH WebContentsView children even while the UI rendered fine on screen; WebContentsView capturePage came back empty; CDP `Page.captureScreenshot` via `webContents.debugger` hung ~98s; offscreen-view capturePage worked in isolated probes. Before trusting ANY capture path in a new environment, run a 30-line probe that writes the PNG and checks `fs.statSync(file).size > 0` + pixel stats (`PIL: mean luminance, % bright pixels (>180)`). A near-black image with a plausible byte count means the capture path failed, not the theme. Full probe matrix: `references/windows-capture-forensics.md`.
- **CSS `url()` resolves relative to the CSS FILE, not the document.** `src/shell/css/shell.css` needs `url("../../../background.png")` to reach the project root (one `../` per directory level); counting wrong silently 404s the wallpaper and the whole UI looks flat/dark — check this before suspecting the theme system.

## 5. Model-provider module (dual protocol)

- Two protocols: `openai` (POST `{base}/chat/completions`, `Authorization: Bearer`) and `anthropic` (POST `{base}/messages`, `x-api-key` + `anthropic-version: 2023-06-01`; extract `system` messages to top-level `system` field; `max_tokens` REQUIRED).
- Streaming: `stream:true` + SSE parse (`chunk.split(/\r?\n/)`, lines starting `data:`, `[DONE]` terminator — avoid raw `\n` literals in source on MSYS, use regexes). Forward deltas to the renderer over per-request channels `host:chat:chunk:<rid>`; preload subscribes with `ipcRenderer.on` and removes the listener on `done`.
- Persist provider configs in a JSON settings store; `merged()` = presets + user overrides + **every** `custom:true` entry. Pitfall: a `savedMap.get(id)` guard in the custom push loop filters out ALL customs (they're always in savedMap) — just push unconditionally.

## 6. Electron install on China mirrors

- Registry = npmmirror; binary needs `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/`.
- `npm i -D electron` can finish in ~1s WITHOUT downloading the binary (postinstall skipped/failed silently). Verify `node_modules/electron/dist/electron.exe`; if missing run `ELECTRON_MIRROR=... node node_modules/electron/install.js`.

## 7. npm 12 allow-scripts whitelist blocks project-scope tarball installs

An Electron app that bundles offline tarballs and runs `npm install ./foo.tgz` at runtime (a common "snapshot install" pattern) hits this on npm >= 12:

```
npm error code EALLOWSCRIPTS
npm error -- allow-scripts is not allowed in project-scoped installs. Add the entries to the "allowScripts" field in package.json, or to .npmrc, instead.
```

Root cause: the user's `~/.npmrc` (or workspace config) sets `allow-scripts=<pkg1>,<pkg2>,...` as a security whitelist, and npm 12 enforces it even when `--ignore-scripts` is already on the command line — the tarball's presence in a project-scoped install triggers the check regardless of whether any script would actually run.

Fix that WORKS — write a `.npmrc` into the isolated install directory BEFORE invoking npm:

```ts
fs.writeFileSync(path.join(installRoot, ".npmrc"),
  "allow-scripts=*\nignore-scripts=true\n", "utf8");
```

Then run npm with `--ignore-scripts --no-audit --no-fund --loglevel=error` (relative paths with `./tgz/x.tgz` prefix, since cmd.exe caps absolute-path arg length near 8191 chars).

What DOESN'T work (tried, don't bother):
- `--allow-scripts=true` on the CLI — npm 12 explicitly rejects it for project-scoped installs; the error message even names the two allowed paths (`package.json.allowScripts` or `.npmrc`).
- Adding entries to the user-level `allow-scripts=` whitelist — you'd have to enumerate every tarball's package name, and tarballs are hashed/random IDs by design.

Verify the patch with a tiny probe before trusting a multi-hundred-package install: extract 3 tarballs into a scratch dir, drop the `.npmrc`, run `npm install ./tgz/*.tgz` there. If those 3 pass in ~1s, the fix is correct — but a 3-tarball green != 241-tarball green if you're nervous about arg-length or network hiccups; run the full set once with `loglevel=error` if you want file-backed evidence.

## Pitfalls quick list
- contextBridge restricted-global name collisions (§2) — rename page identifiers.
- GUI stdout swallowed + fake exit 0 from stale single-instance lock (§3).
- `capturePage` misses WebContentsViews; `getMediaSourceId()` broken in 43.4.0 (§4).
- Unverified screenshot writes → read-back check (§4).
- `app.exit()` unreliable on Windows in practice → `process.exit` in smoke (§3).
- Bare `await fn()` in waitFor → permanent hang; bare FUNCTION in `Promise.race` → instant phantom PASS, body never runs (§3).
- Capture paths machine-specific: near-black PNG with plausible size = capture failed; probe + pixel-verify (§4).
- Double-slash taskkill silently fails (§3).
- npm >= 12 blocks project-scope tarball installs behind an allow-scripts whitelist even with `--ignore-scripts`; CLI flag is refused, `.npmrc` in the install dir is the fix (§7).
- Windows write_file lint "Cannot find module E:\e\..." is a checker-cwd false positive; verify with `node --check` from the project dir.

## References
- `references/trigon-agent-framework.md` — Trigon Agent project: layout, provider presets & endpoints, `window.trigon` API surface, manifest schema, smoke checklist state & next steps.
- `references/windows-capture-forensics.md` — probe matrix of Electron capture APIs on this machine (shell capturePage OK / desktopCapturer+WebContentsView black / view capturePage empty / CDP hang), pixel-verification snippet, and the phantom-PASS debugging arc.
- `references/css-override-tailwind-spa.md` — concrete technique for injecting CSS overrides into a Tailwind CSS v4 SPA hosted in a WebContentsView: mapping CSS custom properties, overriding utility classes (`bg-indigo-500` → `--accent`), glass effect injection, component overrides (cards, buttons, inputs, scrollbars, segmented controls), and theme-aware selectors via `data-theme`. Use when porting a third-party SPA into the shell.