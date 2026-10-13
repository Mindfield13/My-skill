# Windows Electron Capture Forensics (probe matrix)

Machine: Windows 11, git-bash, Electron 43.4.0, Node 24, PIL available. Findings from the Trigon Agent build/smoke session (2026-08). Treat every row as machine-validated, not universal — re-probe per environment.

## Validated capture paths (wrote files, bytes>0, pixel-verified)

| Path | Result | Notes |
|---|---|---|
| `win.webContents.capturePage()` (SHELL page) | ✅ Real frames | 1206×769 window → 3.1MB PNG; mean≈171, bright≈60%. Does NOT include native WebContentsView layers. |
| `desktopCapturer.getSources()` on PLAIN BrowserWindow | ✅ Real thumbnails | Match source by `s.name === win.getTitle()` (in probe the name was the window title). `s.id === 'window:' + win.id` does NOT match on Windows — media source ids are HWND-based with `:0``:1` suffix. |
| WebContentsView with `offscreen:true` (isolated probe) | ✅ capturePage real frames | 58KB; worked with preload+sandbox:false+backgroundThrottling:false and real `loadFile` pages. |

## Needs-probe / failed on this machine (do NOT assume; verify per environment)

| Path | Result |
|---|---|
| `view.webContents.capturePage()` on an ON-SCREEN WebContentsView | Empty (`img.isEmpty()`). |
| `desktopCapturer` thumbnail of window WITH WebContentsView children | ~99.8% black (36KB @ 2560×1604) while the window visibly rendered on the desktop. OS-composited capture of native-view windows unreliable here. |
| CDP: `wc.debugger.attach('1.3')` + `Page.captureScreenshot` on a view | Hung ~98s, then `target closed while handling command`. No `withTimeout` around it = run hangs until the global watchdog fires. |
| `webContents.getMediaSourceId()` | Throws `Insufficient number of arguments` (native binding regression) — never build source matching on it. |

## Verdicts that CAME FROM this matrix (not assumptions)

- The UI itself rendered fine — proof came from `win.webContents.capturePage()` (3.1MB wallpaper+glass frames), which is the ONE capture path that always worked here. A near-black full-window thumbnail is a capture-path failure, not a theme failure.
- Because no single path captured "chrome + view composited" reliably here, split evidence: shell capture + DOM/IPC checks for views (executeJavaScript assertions: `!!document.querySelector('#provider-list')`, `data-theme` attribute after `theme.set('dark')`, rendered text content).

## Pixel verification snippet (PIL)

```python
from PIL import Image, ImageStat
im = Image.open(p).convert('L')
st = ImageStat.Stat(im)
px = list(im.getdata())
dark = sum(1 for x in px if x < 80)/len(px)*100
bright = sum(1 for x in px if x > 180)/len(px)*100
print(f'mean={st.mean[0]:.1f} dark={dark:.1f}% bright={bright:.1f}%')
# light-mode UI should show substantial bright%; an all-dark capture (~99%) = capture failed
```

## Probe pattern (before trusting ANY capture path in a new environment)

1. Create BrowserWindow (+ WebContentsView if testing view capture) with `show:true`.
2. Load a page with a known bright/contrast marker (e.g. gradient background).
3. Try the capture API, `writeFileSync` the PNG, assert `statSync(file).size > 1000`.
4. Assert pixel stats (mean/bright%) — a "plausible byte count" alone is NOT evidence.

## The phantom-PASS debugging arc (root cause reused everywhere)

Symptom: smoke reported PASS for screenshots, files absent → write-back verification added (`existsSync + size>0`) → still PASS → forensic module-load line proved the NEW code was executing → `shot ENTER` fired then instant PASS with ZERO internal log lines → conclusion: promise body never ran. Root cause: `withTimeout(async () => {...}, ms)` passed the UNINVOKED function into `Promise.race([fn, killer])`; a non-thenable function is an immediately-fulfilled value, so the result was the function object itself (truthy). Fix (`if (typeof p === 'function') p = p()` in the timeout wrapper) and keep the forensic markers + write-back checks permanently in smoke scripts.