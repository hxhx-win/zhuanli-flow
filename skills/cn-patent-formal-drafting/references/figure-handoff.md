# 附图交接规则

## 起草 skill 的附图职责

起草 skill 负责基于已确认正式稿生成以下附图交接产物：

- `patent/<patent-slug>/drafts/figures/<draft-name>/figure-generation-plan.md`：图号、图名、技术内容、证据来源、推荐后端、预期源文件路径和预期图片路径
- `patent/<patent-slug>/drafts/figures/<draft-name>/figure-manifest.json`：结构化附图清单，供导出 skill 消费

起草 skill 不得调用附图生成脚本，不做 Mermaid/PNG/SVG/AI 图像渲染。

附图渲染属于 `cn-patent-docx-export`。只要 `figure-generation-plan.md` 和 `figure-manifest.json` 完整，未渲染图片不得写成撰写阶段风险。
`figure-manifest.json` 的 `imagePath` 应落在同一 `drafts/figures/<draft-name>/` 图件目录或导出 skill 明确约定的输出目录下。

## figure-manifest.json 格式要求

顶层结构必须是对象：

```json
{"entries": [...]}
```

不得直接输出 JSON 数组。原因：导出脚本以 `manifest.get('entries', [])` 消费，数组格式会静默丢失所有附图且不报错。

每个 `entries[]` 条目必须包含公共字段：

- `figureNumber`：图号。
- `caption`：图名/说明文字，仅用于附图说明、计划和人工识别，不作为图片下方标注。导出脚本只将 `figureNumber` 作为图片正下方的居中标注；附图总数在两幅以上时 `figureNumber` 必须为“图N”或阿拉伯数字 N，例如“图1”或“1”；只有一幅图时可以不编号。
- `figureType`：方法流程、系统结构、路径姿态、数据对比、说明性位图或 existing-asset。
- `preferredBackend`：后端类型。
- `primarySkill`：负责生成图片的 skill。
- `imagePath`：最终图片路径，**相对 manifest 所在目录**（即裸文件名，如 `figure-1.png`），不要写成从 patent-root 起的相对路径（如 `drafts/figures/<slug>/figure-1.png`），否则导出脚本按 manifest 目录拼接会路径翻倍。进入 DOCX 导出前必须存在，除非 `generationStatus=skipped-with-authorization`。
- `evidenceSource`：支撑该图的正式稿段落、证据文件或已有图片来源。
- `generationStatus`：`planned`、`generated`、`missing`、`skipped-with-authorization` 或 `existing-asset`。

后端专用字段：

- Mermaid：`mermaidPath`、`mermaidSource` 或 `sourcePath`、`themeConfigPath`、`renderCommand`。`themeConfigPath` 必须指向 `cn-patent-docx-export/references/mermaid-patent-theme.json`，`renderCommand` 必须包含 `mmdc -c <themeConfigPath> -b white`。
- scientific-visualization：`dataPath`、`plotSpec`、`scriptPath`、`stylePreset`、`outputFormats`。
- matplotlib：`dataPath`、`scriptPath`、`plotType`、`axisLabels`、`stylePreset`。
- seaborn：`dataPath`、`scriptPath`、`plotType`、`semanticMapping`、`stylePreset`。
- scientific-schematics：`prompt` 或 `promptPath`、`technicalConstraints`、`reviewLogPath`。
- generate-image/imagegen：`userAuthorization`、`prompt` 或 `promptPath`、`nonEvidenceNotice`。
- existing-asset：`sourceAssetPath`、`licenseOrSourceNote`、`copyTo`。

## 附图后端对齐

附图说明、摘要附图建议和附图交接清单必须对齐 `../cn-patent-docx-export/references/专利附图生成后端.md` 的多类型资产管线。

若该文件不存在或不可读，记录路径与错误并停止，不得臆造后端规则或降级为 Mermaid-only 附图交付。

## 附图类型覆盖

生成 `figure-generation-plan.md` 前，必须先判断正式稿是否需要以下图型：

- 方法流程图：用于摘要附图或方法总览。
- 系统/装置结构图：当权利要求包含系统、装置、模块、单元、设备或执行平台时必须考虑。
- 数据/实验对比图：当说明书引用实验结果、误差、效率、精度或性能对比时必须考虑。
- 已有项目图片：当用户或仓库已有可用图表时优先登记，不自动重绘。

若最终只规划流程图，必须在 `figure-generation-plan.md` 中说明其他图型为何不适用。

## 后端选择依据

| 附图类型 | `preferredBackend` | `primarySkill` | 说明 |
| --- | --- | --- | --- |
| 方法流程、步骤链路、模块关系 | `mermaid-mmdc` | `markdown-mermaid-writing` | 可追踪、可修改，适合流程图和模块关系图 |
| 数据曲线、误差曲线、实验对比 | `scientific-visualization` | `scientific-visualization` | 可在后端专用字段中指定 `matplotlib` 或 `seaborn` 作为实现库 |
| 系统结构、机械结构、路径/姿态示意 | `scientific-schematics` | `scientific-schematics` | 不容易用 Mermaid 表达的技术示意图 |
| 说明性位图、外观场景 | `imagegen` | `generate-image` | 仅在用户授权时使用，不作为权利要求支撑证据 |
| 既有项目图片 | `existing-asset` | `existing-asset` | 登记来源、复制和命名规范化，不重绘 |

流程图不得替代系统结构图、路径姿态示意图或实验数据图。Mermaid 是方法流程和模块关系的优先后端，不是所有附图的默认后端。

## 导出 skill 的职责边界

导出 skill 只能按 `figure-generation-plan.md` 和 `figure-manifest.json` 执行，不得仅凭附图说明自由推断附图内容。

`figure-generation-plan.md` 给人读，说明为何需要这些图、证据来源和后端选择；`figure-manifest.json` 给机器读，驱动导出前子 agent 生成图片和 DOCX 嵌入。两者中的图号、图名和后端选择必须一一对应。
