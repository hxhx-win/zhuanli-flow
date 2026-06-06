---
name: cn-patent-docx-export
description: 当用户已有中文发明专利 Markdown 正式稿（通常由 `cn-patent-formal-drafting` 产出），要求导出为可编辑 `.docx` 文档时使用。覆盖导出前附图资产准备、按国家知识产权局四类表格对齐单文件预提交稿、页眉页脚、模块页码重启、段落格式、权利要求编号、LaTeX 公式转 Word `m:oMath` 公式对象、按 `figure-manifest.json` 嵌入已生成附图，并可后置导出官方模块分片稿。仅做版式与结构转换，不修改技术方案或权利要求实质内容。触发词：导出 docx、专利 Word、CNIPA 模板、官方模块分片稿、`figure-manifest.json`、`--split-output-dir`、docx export。
---

# 中文专利草稿 DOCX 导出

将 Markdown 专利正式稿导出为 `.docx`。主 agent 可按 `figure-manifest.json` 派子 agent 准备附图资产；导出脚本只处理版式、结构和嵌入已存在图片，不修改技术方案或权利要求实质内容。默认输出一份完整查看稿，并在用户指定 `--split-output-dir` 时额外生成说明书摘要、权利要求书、说明书、说明书附图等分片稿；摘要附图合并进入说明书摘要分片。

## 使用场景

- 正式稿已通过 `cn-patent-project-drafting` 质量检查，需要输出 Word 文档
- 需要去掉 Markdown 痕迹（代码围栏、标题标记）转为正式排版
- 需要将 LaTeX 公式转为 Word 公式对象（m:oMath）
- 需要按起草阶段交付的 `figure-generation-plan.md` / `figure-manifest.json` 准备附图资产并嵌入 DOCX
- 需要在单一 DOCX 中让摘要、权利要求书、说明书、说明书附图分别对齐国家知识产权局官方表格格式
- 需要后置导出官方模块分片稿，便于人工整理提交材料
- 用户明确授权在未完成 Gate C 的情况下带风险导出

## 不适用场景

- 草稿尚未完成起草流程 → 使用 `cn-patent-project-drafting`
- 需要修改技术方案、权利要求或发明点 → 退回起草 skill
- 需要直接生成完整电子申请包或请求书 → 本 skill 输出单文件预提交稿和可选分片稿，不负责电子申请系统填报

## 执行流程

1. **确认输入**：Markdown 正式稿路径和输出 `.docx` 路径
2. **检查交接条件**：质量检查报告通过 + Gate C 确认，或用户带风险授权；不满足即停止
3. **环境检查**：运行 `patent-env-check.py`（位于 `cn-patent-project-drafting/scripts/`），确认 pandoc/python-docx 可用；阻断项必须先解决
4. **公式源校验**：检查起草报告中 LaTeX 公式源结论；独立公式必须为 `latex` 代码块，段内变量必须为 `\(...\)` 或 `$...$`；有硬错误则停止导出
5. **导出前附图资产准备**（可选）：若正式稿需要附图，读取 [references/专利附图生成后端.md](references/专利附图生成后端.md)，主 agent 按 `figure-manifest.json` 的 `primarySkill` / `preferredBackend` 派只读子 agent 生成或复制图片资产。子 agent 不得修改正式稿正文，不得重新发明附图内容。主 agent 汇总结果并确认每个必需条目的 `imagePath` 已存在；缺失则停止，除非用户明确授权缺图或无图导出。
6. **DOCX 导出**：执行 `export-patent-draft-docx.py`；有附图时传入已校验且 `imagePath` 均已就绪的 `--figure-manifest` 参数；需要分片稿时传入 `--split-output-dir`
7. **导出后验证**：执行 `extract-docx-text.py --verify`，检查官方表格格式、页脚页码、摘要、权利要求、说明书和附图规则
8. **报告结果**：输出路径、验证结论、仍需人工微调的排版项；仅报告格式问题，不回写技术方案

## 验证清单（脚本自动检查）

| 检查项 | 级别 |
|--------|------|
| Markdown 残留（围栏、标题标记） | FAIL |
| 页眉完整性（4 个 section header） | FAIL |
| 页面设置（A4、官方页边距：上/左 25mm，右/下 15mm） | FAIL |
| 页脚页码存在，且各官方模块 section 从 1 重新编号 | FAIL |
| 摘要字数、摘要正文形态 | FAIL |
| 权利要求禁用表述与句号规则 | FAIL |
| 说明书必需部分（技术领域、背景技术、发明内容、具体实施方式） | FAIL |
| 段落格式（行距 360、首行缩进 200、两端对齐、宋体） | FAIL |
| 页眉官方样式（黑体、加粗、14pt、居中、字间距、无下边线） | FAIL |
| 公式对象存在性（m:oMath > 0） | WARN |
| 公式结构正确性（m:nary 主体非空） | WARN |
| 附图嵌入（w:drawing、image rels、word/media） | WARN（manifest 存在时）/ INFO（无 manifest） |
| 权利要求编号连续性 | WARN |
| Section 顺序（摘要→摘要附图→权利要求书→说明书） | WARN |
| 分片稿存在性与可打开性（指定 `--split-output-dir` 时） | FAIL |
| 残留 pandoc 样式（Heading/Compact/SourceCode） | WARN |

verdict 为 PASS 时导出完成；WARN 列出待人工确认项；FAIL 必须修复后重新导出。

## 格式基准

所有版式参数由脚本从 `assets/reference.docx` 提取实现，公式源约束见 [references/专利草稿DOCX输出格式.md](references/专利草稿DOCX输出格式.md)。

## 常见错误

- 源稿中写 `sum(...)` 或 `mu(θ)` 等伪公式文本而非 LaTeX → 导出脚本无法转换，必须退回起草修正
- 未运行环境检查直接导出 → pandoc 缺失时脚本会阻断，不会降级为纯文本
- 附图 manifest 缺失、字段不足或图片资产缺失 → 停止导出前资产准备；不得从附图说明重新推断
- 在 Gate C 未确认时导出 → 必须有用户明确授权，否则停止

## 脚本与命令

详见 [references/commands.md](references/commands.md)。跨平台工具映射见 `cn-patent-project-drafting` 的 `references/agent-tool-mapping.md`。
