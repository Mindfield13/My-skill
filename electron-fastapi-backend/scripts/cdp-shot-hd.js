// CDP 高清截图（deviceScaleFactor 2）
// 用法: node cdp-shot-hd.js [port=9223] [out=shot_hd.png] [width=1320] [height=860]
const fs = require('fs');
async function main() {
  const port = process.argv[2] || '9223';
  const out = process.argv[3] || 'shot_hd.png';
  const width = parseInt(process.argv[4] || '1320', 10);
  const height = parseInt(process.argv[5] || '860', 10);
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const page = targets.find((t) => t.type === 'page');
  if (!page) { console.error('未找到 page target'); process.exit(1); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0; const pending = new Map();
  const send = (method, params = {}) => new Promise((res) => { const m = ++id; pending.set(m, res); ws.send(JSON.stringify({ id: m, method, params })); });
  ws.onmessage = (e) => { const msg = JSON.parse(e.data); if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); } };
  await new Promise((res) => (ws.onopen = res));
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 2, mobile: false });
  await new Promise((r) => setTimeout(r, 800));
  const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true });
  fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
  console.log('saved', out, fs.statSync(out).size, 'bytes');
  ws.close(); process.exit(0);
}
main().catch((e) => { console.error(e); process.exit(1); });