# Electron 43.4.0 / Windows capture & verification matrix

Verified 2026-08 on Win11 + MSYS git-bash, Electron 43.4.0, during the Trigon Agent shell build
(BrowserWindow shell + WebContentsView per app).

## Capture capability matrix

| Method | Shell (BrowserWindow wc) | App view (WebContentsView) | Notes |
|---|---|---|---|
| `wc.capturePage()` on-screen | ✓ real frames | ✗ empty nativeImage | native views not in window compositor capture |
| `wc.capturePage()` offscreen (`offscreen:true`) | n/a | ✗ empty AFTER initial attach; ✓ after forced re-attach | see quirk below |
| `desktopCapturer.getSources()` window thumbnail | ✓ plain windows (match by title) | ✗ near-black when window HAS WebContentsView children | `s.name === win.getTitle()` |
| CDP `Page.captureScreenshot` via `wc.debugger` | n/a | ✗ hangs ~98s then "target closed while handling command" | avoid |
| `wc.getMediaSourceId()` | ✗ binding throws "Insufficient number of arguments" | — | match sources by title instead |

Standalone probes (plain windows, no shell) ALL capture fine — never trust a standalone replica to
predict behavior inside the real shell process.

## The offscreen re-attach quirk (root cause, A11 probe)

Symptom: fresh offscreen view, `loadFile` completes, page JS runs (executeJavaScript + DOM queries OK),
but `capturePage()` → empty for the LIFE of the view (chat/settings/hello views all failed).

Proved NOT the cause (each eliminated with an in-app control probe while everything else held equal):
webPreferences combo, dom-ready `insertCSS`+theme broadcast, wallpaper CSS injection, view size
(600×420 vs 1206×769), single executeJavaScript before capture, capture order view-vs-shell,
`win.show()/focus()`, re-setBounds after load, waitFor polling hammer.

Proved cause (A11): the manager-created view's initial attach never starts the offscreen paint
pipeline. Forcing `contentView.removeChildView(v)` → `contentView.addChildView(v)` →
`setBounds(layout())` → sleep(600–800ms) makes `capturePage` return real frames (~68 KB PNG).

Working smoke capture pattern for app views:

```js
// TRIGON_OFFSCREEN=1 makes appManager create views with webPreferences.offscreen:true
try {
  win.contentView.removeChildView(view);
  win.contentView.addChildView(view);
  appManager.layout();               // or view.setBounds(chrome-aware bounds)
} catch (e) {}
await sleep(600);
const img = await view.webContents.capturePage();
// never trust img.isEmpty() check alone — also fs.existsSync + statSync().size > 0 after toPNG write
```

## Control-probe methodology (reuse when hypotheses stall)

When separate standalone replicas pass but the real flow fails, insert probes INSIDE the real process:
- One throwaway WebContentsView created with identical webPreferences vs the manager-created one.
- Single-variable A/B: keep every probe's pass/fail line in a timestamped log.
- Log each incremental hypothesis (size, handlers, wallpaper, eJS, order, focus, rebound, waitFor…)
  — the 12-probe run here (A, A1, A3, A4, A5, A7, A8, A9, A11, A12) is what finally isolated A11.

## Pixel verification when the vision API is flaky

- PIL luminance stats: `mean`, share of pixels <80 (dark) and >180 (bright).
  Real light-mode shell: mean ~171, bright ~60%. Bogus black captures: 99.8% dark.
- Compare light vs dark screenshots of the same page — theme switch must move the stats.
- Downscale to ≤1500px width JPEG (quality ~88) before `vision_analyze` if the provider rejects
  2560px PNGs with HTTP 400 "Unexpected item type in content".

## Async helpers that prevent fake passes / hangs

```js
function withTimeout(p, ms, tag) {
  if (typeof p === 'function') p = p();            // Promise.race treats a fn as fulfilled!
  let timer;
  const killer = new Promise((_, rej) => { timer = setTimeout(() => rej(new Error('timeout ' + (tag || ''))), ms); });
  return Promise.race([p, killer]).finally(() => clearTimeout(timer));
}

async function waitFor(fn, timeout) {              // per-iteration race: a never-settling fn
  const t0 = Date.now();                            // cannot hang the deadline
  for (;;) {
    try {
      const r = await Promise.race([Promise.resolve().then(fn), sleep(800).then(() => 'W8T')]);
      if (r !== 'W8T' && r) return true;
    } catch (e) { /* retry */ }
    if (Date.now() - t0 > (timeout || 8000)) return false;
  }
}
```