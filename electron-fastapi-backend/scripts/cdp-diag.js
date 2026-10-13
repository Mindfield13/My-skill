// CDP DOM 诊断：URL / body 长度 / 导航数 / 面板 id / 点击后状态
// 用法: node cdp-diag.js [port=9223]
async function main() {
  const port = process.argv[2] || '9223';
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const page = targets.find((t) => t.type === 'page');
  if (!page) { console.error('未找到 page target'); process.exit(1); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0; const pending = new Map();
  const send = (method, params = {}) => new Promise((res) => { const m = ++id; pending.set(m, res); ws.send(JSON.stringify({ id: m, method, params })); });
  ws.onmessage = (e) => { const msg = JSON.parse(e.data); if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); } };
  await new Promise((res) => (ws.onopen = res));
  const ev = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
    if (r.exceptionDetails) return 'EXC: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text).slice(0, 250);
    return JSON.stringify(r.result?.value ?? null);
  };
  console.log('URL:', await ev('location.href'));
  console.log('body html len:', await ev('document.body.innerHTML.length'));
  console.log('nav btns:', await ev('document.querySelectorAll(".app-nav-btn").length'));
  console.log('panels:', await ev('["home","task","write","view","ext","settings"].map(p=>p+":"+(document.getElementById(p+"Panel")?"Y":"N")).join(" ")'));
  const view = (process.argv[3] || 'task');
  console.log(`click ${view}:`, await ev(`(function(){ const b=document.querySelector('.app-nav-btn[data-view="${view}"]'); if(!b) return "no-btn"; b.click(); return "clicked"; })()`));
  await new Promise((r) => setTimeout(r, 1200));
  console.log(`${view}Panel class:`, await ev(`document.getElementById("${view}Panel") ? document.getElementById("${view}Panel").className : "MISSING"`));
  console.log(`${view}Panel html len:`, await ev(`document.getElementById("${view}Panel") ? document.getElementById("${view}Panel").innerHTML.length : -1`));
  ws.close(); process.exit(0);
}
main().catch((e) => { console.error(e); process.exit(1); });