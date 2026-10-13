// CDP 交互测试：点击导航/设置按钮 + 收集 console error/warning + 截图
// 用法: node cdp-test.js [port=9223]
const fs = require('fs');

async function main() {
  const port = process.argv[2] || '9223';
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const page = targets.find((t) => t.type === 'page');
  if (!page) { console.error('未找到 page target'); process.exit(1); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0; const pending = new Map();
  const send = (method, params = {}) => new Promise((res) => { const m = ++id; pending.set(m, res); ws.send(JSON.stringify({ id: m, method, params })); });
  await new Promise((res) => (ws.onopen = res));
  // 启用 console 捕获并叠加消息处理
  ws.send(JSON.stringify({ id: 999, method: 'Runtime.enable' }));
  const errors = [];
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.method === 'Runtime.consoleAPICalled' && (msg.params.type === 'error' || msg.params.type === 'warning')) {
      errors.push(msg.params.type + ': ' + msg.params.args.map((a) => a.value || a.description || '').join(' '));
    }
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); }
  };
  await new Promise((r) => setTimeout(r, 1200));
  const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.value;

  await evalJs(`document.querySelector('.app-nav-btn[data-view="task"]').click()`);
  await new Promise((r) => setTimeout(r, 900));
  console.log('任务面板可见:', await evalJs(`!document.querySelector('#taskPanel').classList.contains('hidden')`));
  console.log('任务卡片数:', await evalJs(`document.querySelectorAll('#taskPanel .task-card').length`));

  await evalJs(`document.querySelector('.app-nav-btn[data-view="settings"]').click()`);
  await new Promise((r) => setTimeout(r, 900));
  const hasTestBtn = await evalJs(`!!document.querySelector('#set-test')`);
  console.log('设置页测试按钮存在:', hasTestBtn);
  if (hasTestBtn) {
    await evalJs(`document.querySelector('#set-test').click()`);
    await new Promise((r) => setTimeout(r, 6000));
    console.log('模型测试结果:', await evalJs(`document.querySelector('#set-test-result').innerText || '(空)'`));
  }
  await new Promise((r) => setTimeout(r, 400));
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(process.argv[3] || 'interact.png', Buffer.from(shot.data, 'base64'));
  console.log('console errors/warnings:', errors.length ? errors : '(无)');
  ws.close(); process.exit(0);
}
main().catch((e) => { console.error(e); process.exit(1); });