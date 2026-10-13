# 结构化产物流水线 — skill 深度绑定参考

## 问题背景

在 M-Ultra workflow 中，"加载完整 SKILL.md 文本"只是让 LLM **看到规则**，
但 LLM 大概率还是会按惯性跑。真正的 skill 绑定需要一套**结构化产物机制**，
每个步骤产出特定格式的文件，后续步骤**消费**这些文件做交叉验证。

## 产物链设计

```
读题阶段 (comp-prob-analysis):
  SKILL.md 要求 → PROBLEM_FACTS.json + CAPABILITY_CHECKLIST.json
  workflow 实现 → artifacts.build_problem_facts() + artifacts.build_capability_checklist()
  产物位置 → task_dir/求解/PROBLEM_FACTS.json, CAPABILITY_CHECKLIST.json

求解阶段 (comp-modeling + comp-code):
  SKILL.md 要求 → 每个问题产出 problem_N_results.json
  workflow 实现 → 在 system prompt 中要求 LLM 代码末尾调用固定函数写 JSON
  产物位置 → task_dir/求解/问题N/problem_N_results.json
  汇总     → task_dir/求解/all_results.json

审计阶段:
  workflow 实现 → artifacts.verify_results_json() 做 schema 校验
                 → artifacts.write_audit_ok() 写 AUDIT_OK 凭证到 RESULTS.md
  产物位置 → task_dir/求解/问题N/RESULTS.md（含 AUDIT_OK 标记）

论文阶段 (comp-paper-zh):
  SKILL.md 要求 → 每个数字 traceable 到 results.json
  workflow 实现 → base_context 中嵌入 results.json 内容；
                 → artifacts.trace_numbers_in_text() 校验正文数字可溯源
  禁止      → 论文出现未写进 results.json 的数字

编译阶段 (comp-compile-zh):
  workflow 实现 → 校验 PDF 时间戳是否比 all_results.json 新
                 （如果 PDF 比数据旧 → 图表可能过期，告警）

交火阶段 (comp-review):
  需要      → 消费 CAPABILITY_CHECKLIST 做逐条能力覆盖检查
             → 消费 LOGIC_CONTRACT 做逻辑对抗
```

## 关键设计原则

### 1. 产物是契约，不是附件
每个 skill 的产物格式必须在 workflow 中**明确定义**（schema），
而不是依赖 LLM 自由发挥。`artifacts.py` 中的 `verify_results_json` 定义了这个契约。

### 2. 下游只消费 JSON，不消费裸文本
论文生成阶段的 base_context 中，results.json 的内容必须被嵌入，
并且论文 prompt 必须明确告知"数字必须来自 results.json"。
裸 CSV/txt 文件只能作为辅助参考。

### 3. 校验是自动化的，不是人肉检查
`trace_numbers_in_text` 用正则从论文正文提取数字，
然后与 results.json 中的数字做集合比较。未溯源的数字就是"编造"。

### 4. 跨步引用有硬约束
- 读题阶段产出的 CAPABILITY_CHECKLIST 必须在求解阶段被消费（每个能力项要有对应求解）
- 求解阶段产出的 results.json 必须在论文阶段被消费（每个数字可溯源）
- 交火阶段产出的 CROSS_REF 必须在最终版本中被修复

### 5. 校验失败要阻断或告警
- schema 校验失败 → 告警但不阻断（LLM 可能写了合法但非标准格式）
- 数字溯源失败 → 告警并列出未溯源数字
- PDF 时间戳异常 → 告警建议重跑

## artifacts.py 模块结构

```
artifacts.py
├── extract_figure_manifest(text)  → 从 markdown 提取 FIGURE_MANIFEST 锚点区块
├── verify_results_json(path)      → 校验 results.json 的 schema + 大小 + 必需字段
├── write_audit_ok(json_path, n_constraints) → 写 AUDIT_OK 凭证
├── build_capability_checklist(prob_count, text, llm) → LLM 生成能力清单 JSON
├── build_problem_facts(text, llm) → LLM 生成问题参数化 JSON
├── trace_numbers_in_text(text, results_dir) → 论文数字溯源校验
└── manifest_figure_check(manifest, img_dir) → FIGURE_MANIFEST 对账
```

## 已落地的绑定点（截至 2026-08-18）

| 绑定点 | 实现位置 | 产物 | 状态 |
|--------|---------|------|------|
| 读题 → CAPABILITY_CHECKLIST | `_step_read_problem` → `artifacts.build_capability_checklist` | `CAPABILITY_CHECKLIST.json` | ✅ |
| 读题 → PROBLEM_FACTS | `_step_read_problem` → `artifacts.build_problem_facts` | `PROBLEM_FACTS.json` | ✅ |
| 求解 → results.json | `_code_prompt` system prompt 要求 LLM 代码写 JSON | `problem_N_results.json` | ✅（LLM 承诺） |
| 求解 → 审计凭证 | `_write_audit_ok` → `artifacts.verify_results_json` + `write_audit_ok` | `RESULTS.md` 含 AUDIT_OK | ✅ |
| 求解 → 汇总 | `_write_all_results` | `all_results.json` | ✅ |
| 论文 → 数字溯源 | `_step_paper` → `artifacts.trace_numbers_in_text` | 日志告警 | ✅ |
| 编译 → 时间戳校验 | `_step_compile` | 日志告警 | ✅ |
| 交火 → 结构化 cross_ref | 待实现 | `CROSS_REF.json` | ⬜ |
| 交火 → 能力覆盖检查 | 待实现 | 消费 `CAPABILITY_CHECKLIST` | ⬜ |