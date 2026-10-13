# Modex-MH-Agent 明文目录 + Python 后端 + .pyd 保护形态实战（v1.7.1）

## 形态特征（与纯 Electron 应用完全不同）

```
resources/app/                  ← 明文目录，无 app.asar！
├── main.js                     明文主进程
├── backend/                    Python FastAPI 后端
│   ├── main.py                 明文入口
│   └── services/
│       ├── llm_client.pyd      ★ API 客户端 + 端点完整性自检（Cython）
│       ├── skill_crypto.pyd    ★ skills 解密（AES-GCM，dk 服务器下发）
│       ├── license_guard.pyd   ★ 授权（连 license.mingheng.xin）
│       ├── state_store.pyd     DB + preset
│       └── workflow_engine.pyd 工作流（model_preset_id 解析）
├── routers/settings.pyd        ★ update_settings 强制 base_url
├── dist/assets/index-*.js      前端（认准 index.html 引用的那个！）
└── skills/*/SKILL.md.enc       技能全加密
```

**三个关键机制**：
1. **.pyd 优先于 .py**：同名明文 .py 不生效！必须移走/改名 .pyd
2. **启动自愈 healBeforeBackend()**：每次启动拉 manifest 校验 sha256，**还原被修改的文件**（最大坑）
3. **cleanupLeakedBackendSources()**：启动删与 .pyd 同名的 .py（反编译防护）

## 破解四线

### 线 1：llm_client.pyd → llm_client.py（API 锁解锁）
```bash
mv llm_client.cp311-win_amd64.pyd llm_client.cp311-win_amd64.pyd.bak
# 写同名 llm_client.py，保留全部导出：
# AGENT_KEYS / AGENT_PRESET_KEY / ENV_MAPPING / call_llm / describe_image /
# get_all_settings / get_env_for_subprocess / test_connection / verify_endpoint_integrity / _locked_url
```
- `verify_endpoint_integrity()` 恒 True（原版校验锁定 URL 主机名）
- `_locked_url()` 保留返回原域名（兼容调用方），但不做强制
- `call_llm` 从 settings 读 base_url/api_key/model_id，空/旧 mhcoding 回落 `DEFAULT_BASE_URL`（env `MH_DEFAULT_BASE_URL` 可覆盖）

### 线 2：settings.pyd → settings.py（路由解锁）
```python
router = APIRouter(prefix="/api/settings")   # ★ 必须带 prefix，否则 FastAPIError
@router.get("") / @router.put("") / @router.get("/presets") / ...（10 路由）
```
**返回结构必须对齐前端期望（minified JS 里的消费代码）**：
- GET /api/settings → `{"settings": {...}}`（前端读 e.settings）
- GET /api/settings/presets → `{"presets": [...]}`（前端 Array.isArray(e.presets)）
- preset 项含 `base_url` + `has_key` 字段
- update_settings 不再强制 base_url
- 预设表自建 base_url 列（ALTER TABLE ADD COLUMN）

### 线 3：前端 patch（dist/assets/index-XXX.js）
1. 预设弹窗加 Base URL 输入框（原表单只有名称/模型ID/Key）
2. **draft 初始化必须含 base_url**：`onAdd:()=>p({id:'',name:'',model_id:'',api_key:'',base_url:''})`；`onEdit:e=>p({...base_url:e.base_url||''})`（否则 React 非受控输入框值不更新/编辑丢值）
3. onSave 提交透传 `base_url:f.base_url||''`
4. 全局保存不再强制 y1：`{...e,executor_base_url:y1,...}` → `Object.assign({},e,{executor_base_url:e.executor_base_url||'',...})`

### 线 4：对抗启动自愈（不挡则改动被还原！）
1. `healBeforeBackend()` 开头直接 return
2. `initUpdater()` 开头直接 return
3. `updater-config.json` server_url → `http://127.0.0.1:9`
4. `cleanupLeakedBackendSources` 加 PROTECTED 名单（llm_client/settings 保留明文）

## 网络阻断（防偷偷访问服务器）
- socket hook 测 DNS：`verify_license_online`/`renew_license_online` → `license.mingheng.xin`
- 调用点排查：grep main.py（明文）确认唯一调用在用户主动激活路由
- `claude_runner._force_online_verify` 是已废弃遥测（docstring 自述）

## 未破解部分
- skills 内容解密 dk：服务器在线验证下发、内存态不落盘；本地派生 master 通不过 `_validate_secret_chain` → 需在线激活一次拿 dk

## 经验要点
1. 明文目录 ≠ 随便改：Cython pyd 保护核心，同名 .py 需移走 .pyd 才生效
2. 前端返回结构逐字段对齐：`Array.isArray(e.presets)` / `e.settings` 决定 API 形状
3. 启动自愈是最大威胁：先查 heal/updater 再持久化修改
4. React 非受控输入框：新增 input 必须同步 patch state 初始化对象
5. 多个 index-*.js 时认准 index.html 的 `<script src>`
6. 全部备份：.pyd → .bak、JS → .bak