# asar 重建状态（2026-08-16 会话，未完成）

## 已完成的构建步骤（磁盘现状已落盘）

1. **权威规则库已创建**：`E:\Project\M Ultra\M-Ultra-数模\rules-library\`
   - `solve/数模全自动/{求解规范.md, 求解计划.md}`（源自 Mrite-main/Skill/CLAUDE.md）+ `solve/通用/`（兜底）
   - `paper/高教社杯/`、`paper/高教社杯-数据题/`、`paper/华数杯/`（自 M Ultra root 三模板目录复制，含 fonts）
   - `common/` + `external/`（自 userData 复制）+ `templates.json`（3 模板 → solveScheme=数模全自动）
   - 共 65 文件 / 67MB

2. **品牌化补丁已应用**（app_content 内，已 node --check 通过）：
   - renderer/index.html：splash(Brand=M Ultra, Tag=专为数模打造的智能建模工作台)、标题栏、home-brand、设置 logo alt、app-name、terms-lead
   - renderer/panels/dashboard.js：作者的话 + 竞赛日程卡
   - renderer/panels/settings.js：补丁对话框 title/filters
   - src/core/bootstrap.js：启动错误框
   - package.json：name=m-ultra、description、author（version 2.5.0 未动——绑定解密 key）

3. **rules-library 已同步三处**：app_content/rules-library（随 asar 打包）、app.asar.unpacked/rules-library（引擎优先读）、userData %APPDATA%\MriteUltra\rules-library（原目录已备份为 `rules-library.bak-20260816`；Mrite_中等/快速/高级 与 user-solve/user-paper 保留）

4. **exe 更名**：MRITE_2.50\M_Ultra.exe（Mrite.exe 副本）；`首次运行看这里.txt` 已重写为 M Ultra 版

## ❗ 未完成：asar 重建失败（下一步从这里继续）

执行 `npx asar pack app_content app.asar --unpack-dir "assets/python-env,assets/TinyTeX,node_modules/@anthropic-ai,node_modules/@img,node_modules/@napi-rs,node_modules/better-sqlite3,node_modules/sharp"`
→ **产出 app.asar = 2,691,105,028 字节（2.69GB）**，说明 unpack 参数未生效（原 asar 仅 113MB）。

当前位置：
- `resources/app.asar` = 2.69GB 错误产物（需重打包覆盖）
- `resources/app.asar.old` = 原始 113MB 可运行版（mv 改名，未删）
- `resources/app.asar.v250.orig.bak` = 原始 113MB 备份副本
- `resources/app_content/` = 已含全部新规则库 + 品牌补丁的完整源码（2.6GB）

### 下一步修复路径

1. 用 Node API glob 数组重打包（勿用 CLI 逗号列表）：
   ```js
   const asar = require('@electron/asar');
   await asar.createPackageWithOptions('app_content', 'app.asar', {
     unpackDir: ['**/python-env/**', '**/TinyTeX/**', '**/@anthropic-ai/**',
                 '**/@img/**', '**/@napi-rs/**', '**/better-sqlite3/**', '**/sharp/**']
   });
   ```
   （注意 createPackageWithOptions 会同时产出 app.asar.unpacked —— 与现有 resources/app.asar.unpacked 按需合并，勿删原有 python-env/TinyTeX）
2. **立即校验**：`ls -la app.asar` 体积应为 ~110-120MB；`npx asar list app.asar | grep -E '^\\\\rules-library'` 能看到新规则库条目
3. 启动 `M_Ultra.exe` 验证：模板轮播 3 模板、无 Mrite 残留、可编译论文

### 回到 electron-asar-modification 的第 5 步坑（验证勿 extractAll，直接读 header）

## 未做的验证（等 asar 修复后）

- [ ] 应用启动 + 截图（用户习惯视觉验证）
- [ ] 三套模板 xelatex 编译零错误（TinyTeX: assets/TinyTeX/bin/windows/xelatex.exe）
- [ ] userData templates.json 实际被加载（3 模板可选）
- [ ] exe 图标换 M Ultra logo（rcedit，后续）