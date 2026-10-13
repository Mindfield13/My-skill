# 高教社杯模板更新：去除目录 + 页数限制

> 2026-08-20 | 高教社杯最新要求

## 变更内容

### 1. 移除 `\tableofcontents`

**高教社杯/论文.tex** — 删除 `\tableofcontents\thispagestyle{empty}\newpage` 三行，替换为注释说明。

**高教社杯/论文章节规范.md** — 同步删除同三行，替换为注释。

**高教社杯-数据题/论文.tex** — 该模板原本就没有 `\tableofcontents`，仅在 `\begin{document}` 后添加页数限制注释。

**高教社杯-数据题/论文章节规范.md** — 删除 `\tableofcontents\thispagestyle{empty}\newpage` 三行（第 85-87 行），替换为注释。

### 2. 添加页数限制规则

**论文章节规范.md**（两个模板）— 新增 `⚠️ 高教社杯最新页数要求` 章节：
- 论文不要目录
- 总页数不超过30页，控制在25页以内
- 控制方法：每章写完检查篇幅，压缩冗余描述，图表精炼
- 编译后验证：`grep 'pages' 论文.log | tail -1`

**Mrite_中等/求解规范.md** — 新增 `三、论文篇幅控制` 章节：
- 论文不要目录（写论文阶段禁止加入 `\tableofcontents`）
- 总页数不超过30页，控制在25页以内
- 各章篇幅控制建议：
  - 摘要：1页
  - 引言：1-2页
  - 模型假设+符号说明：1页
  - 各问题求解（N问）：每个问题3-5页，合计≤15页
  - 模型检验+评价+改进：2-3页
  - 参考文献+附录：1-2页

### 3. 同步到 userData

规则库文件在 `assets/rules-library/` 下修改后，需同步到 `%APPDATA%\Trigon Agent\mrite\rules-library\` 对应目录。`copyMissingSafe` 不覆盖已有文件，必须直接覆盖。

```bash
RULES_USER="$APPDATA/Trigon Agent/mrite/rules-library"
cp assets/rules-library/paper/高教社杯/论文.tex "$RULES_USER/paper/高教社杯/论文.tex"
cp assets/rules-library/paper/高教社杯/论文章节规范.md "$RULES_USER/paper/高教社杯/论文章节规范.md"
cp assets/rules-library/paper/高教社杯-数据题/论文.tex "$RULES_USER/paper/高教社杯-数据题/论文.tex"
cp assets/rules-library/paper/高教社杯-数据题/论文章节规范.md "$RULES_USER/paper/高教社杯-数据题/论文章节规范.md"
cp assets/rules-library/solve/Mrite_中等/求解规范.md "$RULES_USER/solve/Mrite_中等/求解规范.md"
```

## 验证

```bash
# 检查所有模板无 \tableofcontents 命令（注释中的不计）
for f in assets/rules-library/paper/*/论文.tex; do
  if grep -n '\\\\tableofcontents' "$f" | grep -v '^.*%.*'; then
    echo "FAIL: $f 仍有 \\tableofcontents"
  fi
done

# 检查页数限制规则
for f in assets/rules-library/paper/*/论文章节规范.md; do
  grep -q "25页" "$f" && echo "OK: $f" || echo "FAIL: $f 缺页数规则"
done
```