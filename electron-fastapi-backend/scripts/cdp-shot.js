// CDP 截图脚本：连接 Electron/Chromium 调试端口，截取页面 PNG
// 用法: node cdp-shot.js <port> <out.png>
// 依赖: Node 18+ 全局 fetch + Node 22+/24+ 全局 WebSocket（无需额外 npm 包）
const fs = require('fs');

async function main() {
  const port = process.argv[2] || '9223';
  const out = process.argv[3] || 'shot.png';
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const page = targets.find((t) => t.type === 'page');
  if (!page) { console.error('未找到 page target'); process.exit(1); }

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const send = (method, params = {}) => new Promise((res) => {
    const mid = ++id;
    pending.set(mid, res);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); }
  };
  await new Promise((res) => (ws.onopen = res));

  // 等页面稳定（首屏渲染）
  await new Promise((r) => setTimeout(r, 2500));
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
  console.log('saved', out, fs.statSync(out).size, 'bytes');

  const title = await send('Runtime.evaluate', { expression: 'document.title', returnByValue: true });
  console.log('title:', title.result && title.result.value);

  // 抓取页面 console 错误（可选验证）
  const err = await send('Runtime.evaluate', {
    expression: 'window.__hermesErrors ? window.__hermesErrors : "（需应用自己收集）"',
    returnByValue: true,
  });
  console.log('console:', err.result && err.result.value);
  ws.close();
  process.exit(0);
}
main().catch((e) => { console.error(e); process.exit(1); });