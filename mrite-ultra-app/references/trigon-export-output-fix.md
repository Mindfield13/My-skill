# Trigon MRITE 导出输出目录修复

> 2026-08-20 | 现象：任务跑完但输出文件未出现在 E:\Project

## 根因

`src/main/services/mrite/index.js` 中 `mctx.getCustomOutputPath` 返回 `''` 空字符串，导致 `file.js` 的 `syncOutput()` 函数检查到 `customOut` 为空直接跳过导出：

```javascript
// file.js syncOutput()
function syncOutput() {
  const customOut = ctx.getCustomOutputPath();
  if (!customOut) return { success: true, targetDir: workDir, skipped: true }; // ← 永远走这里
  // ...
}
```

## 修复

将 `getCustomOutputPath` 从硬编码 `''` 改为从 DB 读取 `outputPath` 设置并解密：

```javascript
getCustomOutputPath: () => {
  try {
    const db = require('./src/core/database').getDb();
    if (db) {
      const row = db.prepare("SELECT value FROM settings WHERE key = 'outputPath'").get();
      if (row && row.value) {
        const parts = String(row.value).split(':');
        // AES-256-GCM 密文格式: iv:authTag:ct
        // IV 是 12 字节 = 24 hex 字符，authTag 是 16 字节 = 32 hex 字符
        if (parts.length === 3 && parts[0].length >= 24 && parts[1].length === 32) {
          try {
            const crypto = require('crypto');
            const os = require('os');
            const hostname = os.hostname(), cpuModel = (os.cpus()[0]||{}).model||'';
            const plat = os.platform()+'_'+os.arch(), totalMem = os.totalmem();
            const mc = crypto.createHash('sha256').update([hostname,cpuModel,plat,String(totalMem)].join('|')).digest('hex').substring(0,16).toUpperCase();
            const key = crypto.createHash('sha256').update(mc+'|mrite-db-v2').digest();
            const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(parts[0], 'hex'));
            decipher.setAuthTag(Buffer.from(parts[1], 'hex'));
            let d = decipher.update(Buffer.from(parts[2], 'hex'));
            d = Buffer.concat([d, decipher.final()]);
            const path = d.toString('utf8').trim();
            if (path) return path;
          } catch (e) { /* 解密失败走 fallback */ }
        }
        // 明文存储的路径
        const v = String(row.value).trim();
        if (v) return v;
      }
    }
  } catch (e) { /* ignore */ }
  return '';
},
```

## 验证

```bash
# 启动后检查 DB 中的 outputPath
node -e "
const crypto = require('crypto'), os = require('os');
const sqlite3 = require('better-sqlite3');
const db = new sqlite3.DB(process.env.APPDATA + '/Trigon Agent/data/mrite.db');
const row = db.prepare(\"SELECT value FROM settings WHERE key = 'outputPath'\").get();
const parts = row.value.split(':');
const hostname = os.hostname(), cpuModel = (os.cpus()[0]||{}).model||'';
const key = crypto.createHash('sha256').update([hostname,cpuModel,os.platform()+'_'+os.arch(),String(os.totalmem())].join('|')).digest('hex').substring(0,16).toUpperCase();
const dKey = crypto.createHash('sha256').update(key+'|mrite-db-v2').digest();
const d = crypto.createDecipheriv('aes-256-gcm', dKey, Buffer.from(parts[0], 'hex'));
d.setAuthTag(Buffer.from(parts[1], 'hex'));
console.log('outputPath:', Buffer.concat([d.update(Buffer.from(parts[2], 'hex')), d.final()]).toString());
"
```

## 坑

- IV 是 12 字节（24 hex 字符），不是 16 字节（32 hex）。检查 `parts[0].length === 32` 会错误判断已加密的字段为明文。
- 机器码必须用 Node 算（`os.cpus()[0].model`），Python `platform.processor()` 返回的 CPU 字符串不同 → AES-GCM InvalidTag。
- 修改后需 `node --check` 验证语法，然后重启应用。