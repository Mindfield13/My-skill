# Modex 资产照搬进可分离组件 (cumcm) — 实测记录

来源会话: Trigon Framework (E:\Project\Framework) 新增第三个数模组件 cumcm。
用户定位: **核心架构/底层资产/解题逻辑来自 Modex，UI 用 Trigon Apple 风格；组件可分离、互不干扰**。

## 1. 资产照搬清单 (物理复制, 非引用)

```
src/apps/cumcm/
├── manifest.json               # {id:"cumcm", icon:"🏆", window:false, wallpaper:false, order:6}
├── index.html                  # 加载屏: host.invoke('cumcm:start') → 健康轮询 → location.href 后端
├── main.js                     # 主进程 handler: spawn venv python -m uvicorn --port 18089
├── standalone.js               # 独立运行入口: electron standalone.js (不经壳)
├── backend/
│   ├── config.py               # CUMCM_EMBEDDED 环境变量切数据目录
│   ├── main.py                 # FastAPI + API 路由 + 前端静态托管
│   ├── engine/                 # pipeline / skill_registry / orchestrator
│   ├── templates/              # 自研分词基类 + cumcm_a/b/c.py + Modex 文档模板 .md
│   ├── skills/                 # ★照搬 modex/skills (92 目录, ~180MB)
│   ├── tools/                  # ★照搬 modex/tools (~14MB pyc 工具链)
│   └── figures/                # 自研 figure renderer
├── frontend/                   # 原生 HTML/CSS/JS (无打包)
│   ├── css/app.css             # 自包含 Trigon 令牌 (不依赖 tokens.css)
│   ├── js/app.js
│   └── vendor/katex/           # ★照搬 modex/katex-assets
└── scripts/                    # 安装/启动脚本
```

关键复制命令:
```bash
cp -r modex/skills    src/apps/cumcm/backend/skills
cp -r modex/templates src/apps/cumcm/backend/templates
cp -r modex/tools     src/apps/cumcm/backend/tools
cp -r modex/katex-assets src/apps/cumcm/frontend/vendor/katex
```

## 2. Modex skills 结构真相 (照搬前必须知道)

- 共 92 个 skill 目录，每个目录核心文件是 `SKILL.md` —— **明文**，YAML frontmatter:
  ```yaml
  ---
  name: comp-prob-analysis
  description: "..."
  argument-hint: [competition-problem-text]
  allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent
  ---
  # 正文 (LLM agent 执行的指令)
  ```
- 同目录常有 `.enc` 加密副本 (`SKILL.md.enc`, `templates/*.tex.enc`) —— 明文与 .enc **双份共存**，照搬用明文即可，无需解密。`.enc` 需 `skill_crypto.cp311-win_amd64.pyd`(仅 Python 3.11) 解密。
- 竞赛相关真实技能 id(模板引用要对齐这些):
  `comp-prob-analysis`(赛题分析) / `comp-modeling`(建模) / `comp-stats-topic`(数据统计) / `comp-code`(代码) / `comp-paper-zh`+`comp-paper-zh-docx`(中文论文) / `comp-review`(审稿) / `comp-compile-zh`(中文编译) / `paper-figure` / `paper-figure-drawio` / `quality-check` / `auto-paper-improvement-loop`
- 引擎自建收尾 skill: `final-package` (Python 子类，把工作区 zip 打包)

## 3. SkillRegistry 双格式设计

```python
class MdSkill:      # Modex SKILL.md → 由 LLM agent 执行
class Skill:        # 自研 Python 子类 → 引擎直接 run()

# _load_all(): 先扫 skills/**/SKILL.md (关键 frontmatter 解析 regex),
#              再显式注册 engine/builtin_*.py 内建 skill:
try:
    from engine.builtin_final_package import FinalPackageSkill
    self._skills[FinalPackageSkill.id] = FinalPackageSkill()
except Exception as e:
    logger.debug(...)
```
**坑**: `import builtin_final_package` 裸导入找不到 (engine/ 不在 backend 顶层 sys.path)，必须 `from engine.builtin_final_package import ...`。

## 4. 可分离组件关键代码

### config.py 数据目录切换
```python
if os.environ.get("CUMCM_EMBEDDED") == "1":      # 嵌入 Trigon 壳
    DATA_DIR = ROOT.parent.parent.parent / "cumcm_data"   # Framework/../cumcm_data
else:                                             # standalone.js 独立运行
    DATA_DIR = ROOT.parent / "cumcm_data"
```

### main.js 启动后端 (独立端口 18089, 不与 modex 18088 冲突)
**⚠ 卡加载屏修复后的正确模式 (三铁律)**：
```javascript
function _findPython() {
  // ① 组件自己的 venv
  const venv = path.join(BACKEND_DIR, '.venv', 'Scripts', 'python.exe');
  if (fs.existsSync(venv)) return venv;
  // ② Framework runtime python (py3.11, 有 uvicorn/fastapi/numpy/matplotlib)
  const runtimePy = path.join(__dirname, '..', '..', '..', 'runtime', 'python', 'python.exe');
  if (fs.existsSync(runtimePy)) return runtimePy;
  // ③ 最后才回退系统 python —— 勿打头! Hermes 桌面 `where python` 抓到 hermes venv 3.12 无 uvicorn
  try { const w = require('child_process').execSync('where python',{encoding:'utf8'}).trim().split('\n')[0]; if (w) return w; } catch(e) {}
  return 'python';
}
function _cleanEnv() {
  const env = Object.assign({}, process.env);
  delete env.PYTHONPATH; delete env.PYTHONHOME; delete env.VIRTUAL_ENV;  // ★ Hermes 注入会污染子进程
  Object.assign(env, { CUMCM_EMBEDDED:'1', CUMCM_PORT:String(PORT),
    PYTHONDONTWRITEBYTECODE:'1', PYTHONUTF8:'1', PYTHONIOENCODING:'utf-8', LANG:'en_US.UTF-8', LC_ALL:'en_US.UTF-8' });
  // runtime 工具链入 PATH (node/ git-bash)
  const extra = [nodeDir, path.dirname(pythonExe), gitBin];
  if (extra.length) env.PATH = extra.join(';') + ';' + (env.PATH || '');
  return env;
}
pythonProcess = spawn(_findPython(), ['-m','uvicorn','main:app','--host','127.0.0.1','--port',String(PORT),'--log-level','info'],
  { cwd: BACKEND_DIR, env: _cleanEnv(), stdio:['ignore','pipe','pipe'], windowsHide:true });
```
- ❌ 旧模式 `env: {...process.env, ...}` 会继承 Hermes 注入的 PYTHONPATH/PYTHONHOME → uvicorn import 崩 → 加载屏「正在启动…」永久转圈。
- 排查: 启动前 `console.log('[CUMCM] Using python:', pythonExe)`；卡加载屏先看这行 python 路径选对没。

### FastAPI StaticFiles 目录守卫 (必加)
```python
if FRONTEND_DIR.is_dir():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.is_dir():   # 前端用分离 css/js 时没有 assets/ → 不守卫会 RuntimeError 崩
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        static_file = FRONTEND_DIR / full_path
        if static_file.is_file():
            return FileResponse(str(static_file))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
```

## 5. 通用修复 (本次实测)

### matplotlib 中文乱码 (Win, runtime/python 3.11.9)
```python
import matplotlib
import matplotlib.font_manager as fm
for f in ["C:/Windows/Fonts/msyh.ttc","C:/Windows/Fonts/simhei.ttf","C:/Windows/Fonts/simsun.ttc"]:
    if os.path.exists(f):
        try: fm.fontManager.addfont(f)
        except Exception: pass
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei","SimHei","DengXian","SimSun","sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False
```
验证: `warnings.catch_warnings(record=True)` 渲染中文标题图，断言无 "Glyph ... missing from font" 警告。

### bash curl 中文 JSON → "error parsing the body"
bash 单引号内嵌中文+引号转义坏 body。改用 Python urllib:
```python
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(req) as r: return json.load(r)
```
(或写 JSON 文件 --data-binary @f.json)

## 6. 端到端验证结果 (ad-hoc)
- SkillRegistry 加载 89 技能 (88 MdSkill + 1 Python final-package) ✓
- 三模板 (cumcm_a/b/c) resolve 无缺失 skill ✓ (12/13/13 步)
- final-package 真实执行产出 zip ✓
- 中文图表渲染 0 glyph 警告 ✓
- main.py 干净导入 + uvicorn 启动 + /api/health|templates|skills|analyze|figures/render 全通 ✓