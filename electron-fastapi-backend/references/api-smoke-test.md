# API 冒烟测试 + 全功能检查（class 级流程）

用户要求"检查软件运行逻辑及每个功能是否正常运行"时，按此流程系统性验证，而不是抽样点击。

## 步骤（已验证）
1. **后端 API 逐个冒烟**：写 `tools/smoke_test.py`，`check(name, cond, detail)` 收集结果，结尾 `ok/total` 汇总 + `sys.exit(1 if fail else 0)`。覆盖全部端点：health / config / tasks CRUD / progress / steps / evaluate / ai-evaluate(report) / requirements / requirements/files / file 读取 / xlsx-preview / pdf-info / pdf-page / rules / rules/read / templates / step 参数校验（非法 step 应 400）。
2. **前端 8 页截图**：`node tools/cdp-one.js <view> <out.png>` 逐页跑（见 SKILL.md CDP 段：先 bringToFront、Node WebSocket 用 addEventListener、响应驱动）。配合 `vision_analyze` 逐页确认无空白/报错/布局错乱。
3. **关键链路补测**：LLM（AI 评估真实跑一次即证明连通）、PDF 渲染（pdf-page 返回 base64 image 长度>0）、xlsx 表格（html 含 `<table`）、LaTeX 编译（find 到 has_pdf 任务）。
4. **静态语法全检**：`for f in src/renderer/js/*.js src/renderer/js/views/*.js; do node --check; done` + `py_compile src/backend/*.py`。
5. **运行进程残留**：检查 CDP 端口 / 后端端口 / visibilityState（window hidden 会影响截图，见 SKILL.md）。

## 坑（实测）
- **urllib 不自动编码中文 query**：`urllib.request.Request(url)` 直接拼中文 path 会抛编码错或发畸形请求 → `url = quote(path, safe=":/?=&%")` 后再拼 BASE。curl 在 git-bash 传中文 query 也会 "Invalid HTTP request received"——API 测试统一用 Python urllib + quote。
- **404 不一定是 bug**：测某任务缺少的文件类型（如该任务无 xlsx）→ 404 是正确降级。对照文件系统确认：`find data/tasks/<id> -name "*.xlsx"` 看是否存在，换有该文件的任务重测。
- **vision 对业务状态标签（红"出错"徽标）误读为页面报错**：截图分析时区分"渲染正常 + 业务状态"与"页面 JS 错误"。
- vision 一次只能看一张图；8 页并发调 vision_analyze 即可。

## 结果报告格式
按 后端/前端/链路 三块给表，标注每项 ✅/❌ + 证据（状态码、字符数、截图路径），最后给总结论与遗留问题。