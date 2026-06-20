---
name: cn-patent-repo-scout
description: 当用户只提供项目目录、代码仓库或技术资料，并要求“看看有什么能申专利 / 扫描项目 / 推荐专利方向 / 找核心资料”，但尚未明确技术主线或保护方向时使用。独立于完整起草编排器；扫描后由用户在 AskUserQuestion 中二选一：进入完整编排器或暂停。已有明确方向时改用 `cn-patent-mainline-analysis`；不做保护路径设计、不做现有技术检索、不起草正式稿。触发词：专利方向扫描、看看能申什么专利、推荐专利方向、找核心资料、`source-material-roles.json`、repo scout、direction scan。
---

# 专利方向扫描

扫描项目资料，发现可申报方向，辅助用户确认技术方向和核心资料。只做方向发现和资料角色准备，不做保护路径设计、现有技术检索或专利起草。

## 边界

- 本 skill 独立运行，不读取或创建 `patent/<patent-slug>/state/patent-iteration-state.json`。
- 扫描产物是项目级缓存，可被多个专利方向复用。
- Top-N 所有方向都要先落盘；完成方向记录后必须停住，让用户选择下一步。
- 若用户已明确技术方向、保护客体或选定模块，改用 `cn-patent-mainline-analysis` 设计保护路径。
- 若用户明确要完整起草专利或继续既有状态文件，改用 `cn-patent-workflow-orchestrator`。

## 工作流

| 步骤 | 动作 | 产出 | Gate |
|------|------|------|------|
| S1 | 确认扫描根目录、排除规则；必须呈现权重维度表并等待确认或调整 | 确认后的权重 | **用户确认权重** |
| S2 | 资料可读性预检：枚举待扫描文件的后缀，对照 [references/material-readability.md](references/material-readability.md) 判断每类格式当前环境是否能完整读取；对不可完整读取的资料输出提示并按当前环境给出安装命令推荐 | `patent/repo-scout/readability-report.md` | **用户选择处理方式** |
| S3 | 运行只读扫描或 `scripts/patent-repo-scout.py`；若缓存可复用，可直接进入 S4 | `patent/repo-scout/repo-profile.json` | — |
| S4 | 逐问澄清:至少 2 轮，一次一问，优先多选题 | 澄清记录和排序依据 | — |
| S5 | 呈现 Top-N 推荐方向，并为所有方向生成独立记录 | `recommendation-report.md` + 每个方向的 `direction-record.json` 和 `source-material-roles.json` | — |
| S6 | 停住并通过 `AskUserQuestion` 控件让用户在「进入完整编排器」与「暂停」之间二选一；用户可指定任一 `<direction-slug>` 继续 | 下一步选择 | **用户选择下一步** |

## 资料可读性预检纪律

- S2 必须先枚举扫描根目录下所有文件后缀（可结合 `find` / `Get-ChildItem` 或脚本输出），与 [references/material-readability.md](references/material-readability.md) 对照判断每类格式在当前环境的可读取程度（完整 / 仅文本 / 不可读）。
- 必须先检测当前**操作系统**（Linux / macOS / Windows）以及对应包管理器（`apt` / `dnf` / `brew` / `winget` / `choco` / `scoop` / `pip`），再据此挑选可执行命令。
- 对每类不可完整读取的资料，必须明确告知用户：
  - 涉及的文件清单（或样例 + 数量）；
  - 缺失的内容维度（如 PDF 页图像、docx 嵌入图、PNG 视觉内容、扫描件文字等）；
  - 这种缺失对方向发现的潜在影响（例如附图缺失会削弱"证据完备性"评分）。
- 必须基于当前操作系统和已检测到的命令，按 [references/material-readability.md](references/material-readability.md) 中的工具表给出**可执行的安装命令**，并按"最小够用 / 完整办公套餐 / 含 OCR"分档推荐。Windows 环境优先给 `winget` 命令，缺失时回退到 `choco` 或 `scoop`，并显式提示需要 PowerShell 管理员权限。
- 在用户选择以下任一处理方式之前，不得进入 S3：
  - 安装推荐工具后重跑预检；
  - 接受当前可读范围，标记缺失资料为 `unreadable`；
  - 用户手动补充内容（如手动粘贴关键截图文字、提供已转换文本）。
- 预检结果必须写入 `patent/repo-scout/readability-report.md`，并在后续 `repo-profile.json` 与 `recommendation-report.md` 的"证据线索"小节里引用，方便用户第二次回看时知道哪些方向受可读性限制影响。
- 违反：跳过预检直接扫描，或对不可读资料静默忽略 → 必须回退重做 S2。

## 子 agent 扫描

在 Claude Code 等支持子 agent 的环境中，仓库规模较大或目录较多时，可按目录或模块分派只读子 agent 并行扫描。子 agent 只能读取资料并返回结构化发现，不得写入 `patent/repo-scout/`，不得单独评分、排序或生成推荐报告。

子 agent 优先按目录或子模块分片，例如 `src/`、`modules/`、`examples/`、`docs/`、`benchmark/` 等。避免多个子 agent 重复扫描同一目录。

每个目录扫描子 agent 返回结果时，再按以下字段归类发现：

- 核心代码线索：算法、控制流程、数据处理、接口链路。
- 文档线索：README、设计文档、技术交底、论文草稿。
- 证据线索：benchmark、仿真结果、日志、图表。
- 架构线索：模块关系、输入输出、执行平台、消息流。

主 agent 负责统一合并发现、应用权重、排序 Top-N，并生成 `recommendation-report.md`、`direction-record.json` 和 `source-material-roles.json`。

## 权重确认纪律

- 必须在对话中呈现四维度权重表：技术创新性、证据完备性、保护价值、实施清晰度。
- 默认权重见 [references/evaluation-dimensions.md](references/evaluation-dimensions.md)。
- 必须提供多选题让用户确认或调整，例如“默认 / 更看重保护价值 / 更看重创新性 / 自定义”。
- 用户未确认前不得开始扫描或评估。
- 用户回复“默认”视为确认；回复具体比例则按用户比例更新。

## 澄清纪律

- 扫描完成后不得直接输出最终推荐表，必须先逐问澄清。
- 一次只问一个问题，不堆叠。
- 至少完成 2 轮澄清问答后才能呈现 Top-N 评估结果。
- 根据用户回答动态调整推荐排序和权重。
- 不替用户拍板，只收敛到可选范围。
- 违反：直接输出评估表而跳过澄清问答 → 必须回退重做 S3。

## 输出路径

- `patent/repo-scout/readability-report.md`：资料可读性预检结果，含每类后缀的可读取程度、缺失维度、按当前操作系统给出的安装命令以及用户所选处理方式。
- `patent/repo-scout/repo-profile.json`：扫描元数据。
- `patent/repo-scout/recommendation-report.md`：推荐方向报告，含可复用打分和澄清依据。
- `patent/repo-scout/directions/<direction-slug>/direction-record.json`：每个推荐方向的独立记录，包含方向摘要、评分、证据线索、候选核心资料和确认状态。Top-N 中所有方向都必须生成。
- `patent/repo-scout/directions/<direction-slug>/source-material-roles.json`：该方向的资料角色清单。未被用户选中时可记录候选核心资料，但必须标记为待确认；用户确认后才可作为主线分析或编排器输入。

这些路径相对于用户项目根目录，禁止写入 skill 目录。

`<direction-slug>` 应基于方向名称生成，使用小写字母、数字和连字符；中文方向可使用简短英文含义或拼音。若同名已存在，追加 `-2`、`-3` 等后缀。

`recommendation-report.md` 中每个方向必须列出对应的 `direction-record.json` 和 `source-material-roles.json` 路径，便于用户第二次打开报告时直接选择其他方向。

## 下一步选择

S6 必须通过 `AskUserQuestion` 控件呈现两个选项，禁止只用纯文本列出：

- 进入 `cn-patent-workflow-orchestrator`：启动完整起草编排器（包含主线分析、现有技术检索、技术交底、正式稿起草、代理师审稿、DOCX 导出），并用对应方向的 `patent/repo-scout/directions/<direction-slug>/source-material-roles.json` 初始化资料角色。
- 暂停：只保留扫描报告和各方向记录，不创建编排状态文件。

进入编排器前，必须先得到用户明确选择的 `<direction-slug>`；只有用户在 S6 选择该方向后，`selected_direction` 才可标记为 `repo-scout-confirmed`。不得因为已生成方向记录就自动创建 `patent/<patent-slug>/state/patent-iteration-state.json`。

用户在 `AskUserQuestion` 中选择「进入编排器」后，本 skill **不得**直接调用 `cn-patent-workflow-orchestrator`。必须先输出以下提示并停住，等用户手动 `/compact` 后重新触发编排器：

> 已选择进入完整起草编排器。当前会话上下文已较重，建议先执行 `/compact` 压缩上下文，然后重新调用 `cn-patent-workflow-orchestrator` 继续完整起草。编排器会从 `patent/repo-scout/directions/<direction-slug>/source-material-roles.json` 读取方向和资料，不依赖扫描过程中的对话上下文，所以压缩不会丢失已确认的选择。

## 常见错误

- 把扫描脚本的数值得分当作最终创新性判断 → 脚本只做初筛。
- 跳过权重确认直接扫描 → 必须先等用户确认权重。
- 跳过资料可读性预检直接扫描 → 必须在 S2 输出 `readability-report.md` 并让用户选择处理方式。
- 对不可读资料静默忽略，不告知用户 → 必须列出具体文件和缺失维度。
- 推荐安装命令时不区分操作系统（例如在 Windows 上给 `apt-get`）→ 必须按检测到的 OS / 包管理器组装命令。
- 跳过澄清直接推荐最终方向 → 必须完成至少 2 轮澄清。
- 只给用户选中的方向生成记录 → Top-N 所有方向都必须生成独立记录。
- 多个方向共用一个 `source-material-roles.json` → 必须按方向保存，避免覆盖。
- 让子 agent 写扫描报告或方向记录 → 子 agent 只读返回发现，主 agent 统一落盘。
- S6 用纯文本列出选项让用户回复 → 必须通过 `AskUserQuestion` 控件呈现「进入编排器 / 暂停」两选。
- 用户选「进入编排器」后直接调用 `cn-patent-workflow-orchestrator` → 必须先输出 `/compact` 提示并停住，由用户手动压缩上下文后重新触发编排器。
- 自动进入编排器或创建状态文件 → 必须等用户选择下一步。
- 把代码注释当作技术效果证据 → 优先用实验数据、性能对比和明确实现。

## 参考资料

- 评估维度与打分指引：[references/evaluation-dimensions.md](references/evaluation-dimensions.md)
- 资料可读性与工具映射：[references/material-readability.md](references/material-readability.md)
- 交接规则：[references/handoff.md](references/handoff.md)
