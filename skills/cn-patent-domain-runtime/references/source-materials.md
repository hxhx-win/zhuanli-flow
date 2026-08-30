# 资料入口与证据抽取

> Windows 原生环境：命令中的 `python3` 请用 `python` 或 `py` 代替。

## 必要输入

使用本 skill 时，先确认或通过只读探索补齐以下信息：

- 项目根目录。
- 用户对资料性质的声明：原创资料、核心资料、论文资料、代码资料、技术交底、参考样稿、现有技术/参考文献或其他。
- 参考样稿路径，例如 `patent/`、`.doc/.docx/.pdf`。
- 技术交底、论文草稿、设计文档、实验结果、图表或日志路径。
- 重要代码或算法入口；若用户不知道，可由 Agent 通过只读检索判断。
- 期望输出类型：分析版、正式稿、审稿迭代版、局部权利要求、摘要或证据矩阵。

## 可读取的资料类型

优先从以下材料中抽取专利证据：

- 项目主入口脚本和核心算法模块。
- 仿真脚本、实验结果、图表和日志。
- 技术交底、论文草稿、需求说明和设计文档。
- `patent/` 或同类目录中的参考专利样稿。
- 设备接口、控制链路、消息定义和执行平台资料。

## 资料角色声明与隔离规则

项目开始时先记录用户声明的资料角色。默认只写入状态文件 `source_material_roles`，不再同步生成 `.agents/outputs/evidence/source-material-roles.md`：

```bash
python3 scripts/new-iteration-state.py --project-root . --output-path patent/<patent-slug>/state/patent-iteration-state.json --material-roles-path patent/<patent-slug>/source-material-roles.json
```

若资料角色来自 `cn-patent-repo-scout`，先由用户确认扫描方向和核心资料，再将 `patent/repo-scout/directions/<direction-slug>/source-material-roles.json` 导入或复制到 `patent/<patent-slug>/source-material-roles.json`。编排器不得主动运行扫描，也不得在用户未选择进入完整起草流程时创建状态文件。

角色规则：

- 用户声明为“原创资料、核心资料、论文资料、代码资料、技术交底”的材料，只作为发明证据和实施依据，不得自动归入参考文献、现有技术或格式样稿。
- 用户声明为“参考样稿、格式样稿”的材料，只抽取结构、格式、段落层级、权利要求节奏和措辞风格，不参与发明点来源判断。
- 用户声明为“现有技术、参考文献、对比文献”的材料，才能进入现有技术检索、最接近现有技术或参考文献对比。
- 未声明角色的材料先标记为 `unclassified_requires_confirmation`，不得擅自把核心资料当作参考文献或现有技术。

## 统一资料入口

无论资料来自用户直接提供、`cn-patent-repo-scout` 交接，还是 Agent 只读探索发现，进入编排器前都先直接使用或复制为 `patent/<patent-slug>/source-material-roles.json`。该文件只做资料登记、角色隔离和方向来源记录，不替代主线分析、现有技术检索或 Gate 确认。

资料来源规则：

- 用户已明确声明技术方向、核心资料或保护对象时，`selected_direction.source` 记为 `user-declared`，不得再强制进入 `cn-patent-repo-scout` 做 Top-N 方向推荐。
- 用户只提供项目目录、代码仓库或资料包，且尚未明确技术方向时，先使用 `cn-patent-repo-scout`；用户在 S5 选定方向后，`selected_direction.source` 才可记为 `repo-scout-confirmed`。此时 `repo-scout` 生成的 `source-material-roles.json` 已是交接结构，不需要手工二次转换，只需复制到单案目录并交给初始化脚本导入状态文件。
- 用户提供资料但未声明性质时，条目 `role` 记为 `unclassified_requires_confirmation`，`requires_confirmation` 记为 `true`；确认前不得作为发明证据、参考样稿或现有技术使用。
- Agent 只读探索发现的重要代码、文档或实验资料，只能作为候选条目写入并标记 `requires_confirmation: true`，除非用户已明确授权其资料角色。

推荐结构：

```json
{
  "selected_direction": {
    "source": "user-declared",
    "title": "用户声明或待确认的技术方向",
    "summary": "基于用户提供资料整理的方向摘要"
  },
  "items": [
    {
      "path": "src/algo/core.py",
      "role": "核心资料",
      "description": "用户声明的核心算法实现",
      "requires_confirmation": false
    },
    {
      "path": "materials/unknown.pdf",
      "role": "unclassified_requires_confirmation",
      "description": "用户提供但尚未声明资料性质",
      "requires_confirmation": true
    }
  ]
}
```

角色映射优先级：

1. 用户显式声明优先。
2. `cn-patent-repo-scout` 已确认方向的交接文件次之。
3. Agent 只读探索或文件类型推断只能生成待确认候选，不得覆盖用户声明。

## 资料角色确认（步骤 0→1）

步骤 0.2 之后、步骤 1 之前校验 `patent/<patent-slug>/source-material-roles.json`（资料性质；可读性见 0.1 env-check）。

- **未确认则阻断**：`items` 为空、`selected_direction.title` 为空，或任一条目 `requires_confirmation: true` / `unclassified_requires_confirmation` → 请用户为路径指定角色并补方向，写入 JSON；有变更则重跑 `new-iteration-state.py --material-roles-path ...`。Agent 不得将推断标为已确认。
- **已确认则通过**：回显「路径 | 角色」；`repo-scout-confirmed` 且 scout S5 已完成时只问是否调整，不重复逐文件标注。

## 推荐读取顺序

1. 先找项目主入口，判断完整流程和输入输出。
2. 再找核心算法模块，抽取关键技术步骤、变量、约束和目标函数。
3. 再找实验、仿真或执行链路资料，抽取可量化技术效果和实施方式证据。
4. 最后读用户明确声明为参考样稿的材料，借结构和术语风格，不直接照搬原文。

如果用户只提供项目目录且尚未明确方向，应先使用 `cn-patent-repo-scout` 扫描并确认核心资料；本编排器不要生成扫描报告，也不要把探索结果写回 skill 本体。

## 证据标记规则

抽取证据时，优先标记为以下四类：

- 明确实现：源码或文档直接实现该技术特征。
- 明确展示：图表、实验或仿真结果直接展示该技术效果。
- 合理推断：从已有实现可合理推出，但未直接明写。
- 待用户确认：现有材料不足，必须等待用户补证。

长期复用的证据索引可写入 `.agents/outputs/evidence/`，但不写入 `references/`。

## PDF 提取前置检查

只要输入资料中存在 `.pdf`，先检查 PDF 文字提取能力，再进入证据抽取、主线选择或正式稿生成：

```bash
python3 .agents/skills/cn-patent-domain-runtime/scripts/test-pdf-extraction-readiness.py --path "materials" --project-root .
```

检查顺序不得依赖固定目录：

1. 用户显式提供的 `-PdfToolPath`，或环境变量 `CN_PATENT_PDF_TEXT_TOOL`、`PDF_TEXT_TOOL_PATH`、`PDFTOTEXT_PATH`。
2. 系统 `PATH` 中的 `pdftotext`，或可用的 Python `pypdf` / `PyPDF2`。
3. 当前项目配置中的 PDF 工具路径，例如 `.agents/config/patent-pdf-tools.json` 或状态文件中的 `pdf_extraction.tool_path`。

若没有可用工具链，必须中断并提示用户选择：提供已有工具路径；选择安装目录并授权安装；或提供已提取文本版本。不得静默跳过 PDF。

若工具链存在但抽取结果为空，必须中断并说明可能是扫描件或无文字层，要求 OCR 工具链、可提取版本、已提取文本，或用户明确确认排除该 PDF。

## 参考样稿抽取入口

对 `.doc`、`.docx`、`.pdf`，统一使用当前 skill 的抽取入口：

```bash
python3 scripts/extract-reference-text.py --path "patent/<参考样稿>.docx" --max-paragraphs 80 --project-root .
```

说明：

- `.doc/.docx` 默认走可读文本抽取，必要时回退 Word COM。
- `.pdf` 优先依赖文字层；抽取前先通过通用 PDF 工具链检查，工具缺失或抽取为空都会阻断流程。

## 使用原则

- 代码、注释、图表和实验输出是主证据。
- 参考专利样稿只借结构和风格，不直接照搬原文。
- 原创资料、核心资料、论文资料、代码资料和技术交底不得自动降格为参考文献或现有技术来源。
- 若某项技术效果仅来自工程推断，应标记为“待用户确认”。
