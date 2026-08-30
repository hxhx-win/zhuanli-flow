---
name: cn-patent-mainline-analysis
description: 当用户已有明确技术方向、选定模块、扫描确认方向或 `source-material-roles.json`，需要在已确认方向下整理保护路径候选、技术特征分层、候选发明点用途表和检索输入时使用。不做项目扫描（用 `cn-patent-repo-scout`），不做现有技术检索（用 `cn-patent-prior-art-search`），不起草正式稿（用 `cn-patent-formal-drafting`）。触发词：主线分析、保护路径候选、技术特征分层、候选发明点用途表、检索输入、`mainline-analysis.md`、`evidence-matrix.md`、mainline analysis。
---

# 专利性分析与检索输入整理

围绕已确认技术方向整理保护路径候选、技术特征分层、候选发明点用途表和检索输入，为后续外部检索提供结构化材料。

## 使用边界

- 用户只有项目目录，想“看看有什么能申专利 / 扫描项目 / 推荐方向” → 使用 `cn-patent-repo-scout`。
- 用户已经给出技术方向、选定模块、扫描结果或核心资料清单 → 使用本 skill。
- 用户要完整起草、检索、审稿和导出流程 → 使用 `cn-patent-domain-runtime`。

编排模式判断：`patent/<patent-slug>/state/patent-iteration-state.json` 存在 → 编排模式（额外回写状态字段）；否则 → 独立模式。

## 工作流

| 步骤 | 动作 | 产出 |
|------|------|------|
| 1 | 只读探索项目入口、核心模块、实验资料 | 项目理解 |
| 2 | 抽取技术问题、技术步骤、约束关系、输入输出 | 技术方案骨架 |
| 3 | 确认技术方向来源并设计 1 条或多条保护路径候选 | `mainline-analysis.md` 的 `## 已确认技术方向` 和 `## 保护路径候选` |
| 4 | 判断保护客体（方法/装置/系统/组合） | `## 保护客体初步判断` |
| 5 | 建立技术特征分层表（必要/优选/实施细节 + 作用/效果/主体归属/写入位置） | `## 技术特征分层` |
| 6 | 建立候选发明点用途表 | `## 候选发明点用途表` |
| 7 | 汇总检索输入和待检索确认问题 | `## 检索输入摘要` 与 `## 待检索确认问题` |

## 核心纪律

- 主线分析不得脱离 `selected_direction` 重新推荐新方向；若发现方向不成立，应回到 `cn-patent-repo-scout` 或要求用户重新确认方向
- 保护路径候选是同一已确认方向下的不同保护写法，不是多条不相关发明主线
- 方向明确且保护写法清楚时，可以只有一条主保护路径；需要多路径时，必须说明方法、装置、系统、设备、介质或核心算法环节之间的取舍
- 技术特征必须分三层：必要技术特征 / 优选技术特征 / 实施细节，并为每项特征标注技术作用、技术效果、主体归属、适合写入位置和证据来源
- 先建候选发明点用途表再进入外部检索
- 保护路径只完整发散一次，冻结后仅筛选收紧
- 不得在独立权利要求中以函数名、文件名、脚本名替代技术特征
- 缺少明确方向时不得自行扫描并推荐方向，必须切换到 `cn-patent-repo-scout`
- 来自扫描报告的数值得分只作为线索，创新性判断在 Step 1-2 完成
- 本阶段不做现有技术检索，不写推荐结论或创造性结论；真正可主张发明点由 `cn-patent-prior-art-search` 检索后提取
- **N7 子 agent 自判纪律**：读原始资料（PDF / docx / PPT / 截图 / 源码仓库 / 单文件源码 / 配置 / benchmark 脚本 / 日志 / CSV / JSON 数据集 / 用户提供 URL / 内部 wiki / 外部规范文档等任意来源）**优先派子 agent**；当输入资料体量较大（粗略阈值：≥ 30 份代码/文档、或单份 ≥ 500 行、或含多份 PDF/扫描件）时**必须**嵌套派子 agent 分担；体量较小或类型单一时当前 agent 可自行原子完成 读取 + 抽取 + 落盘，但**必须等同满足**：一次完成 读取 + 抽取 + 落盘 + 返回；直接 Write 到 `evidence-matrix.md`；写到磁盘的内容不返回父 agent；返回上限 ≤ 300 字 verbatim quote 或 ≤ 200 字结论。铁律以产物质量为准——证据锚点（文件路径 + 行号）缺失或 verbatim 抽取断裂时，自判选择应回退为嵌套派子 agent 重做
- **evidence-matrix 模板要求**：模板必须含 `## 原文 verbatim 锚点` 节，按 IP 编号挂证据片段，每片段 ≤ 300 字，含来源指针（文件路径 + 行号 + 章节）；模板见 [assets/evidence-matrix.template.md](assets/evidence-matrix.template.md)
- **mainline-analysis 模板要求**：各保护路径的 `风险` 字段、技术特征分层 `待确认事项` 字段用统一表头便于下游抽取迁移；模板见 [assets/mainline-analysis.template.md](assets/mainline-analysis.template.md)
- **编号锚点落盘规则**：mainline-analysis.md 中保护路径锚点 P1 / P2 / …、evidence-matrix.md 中发明点锚点 IP-1 / IP-2 / … 作为下游文档反向引用的定义源头保留原样，但**章节标题处必须紧跟一句话名称**（如 `### P1 按 track 隔离的累加器写入` / `### IP-1 …`），不得留下光秃秃的 `### P1` 或 `### IP-1`；IP-* / F-* / TP-* / G-* / Q-* 等**表格列内**编号是机读锚点，保留原样无需展开
- evidence-matrix 与 evidence-quality-signals.yml 必须由同一个子 agent 一次性产出；不允许把信号文件留给主 agent 事后补写；信号文件字段定义见 `references/evidence-quality-signals-schema.md`

## 输出物

所有路径相对于用户项目根目录，禁止写入 skill 目录。

模板：

- [assets/evidence-matrix.template.md](assets/evidence-matrix.template.md)
- [assets/mainline-analysis.template.md](assets/mainline-analysis.template.md)

| 逻辑产出 | 文件 | 说明 |
|----------|------|------|
| 证据矩阵 | `patent/<patent-slug>/evidence/evidence-matrix.md` | 独立文件；记录资料路径、技术要点、实验/性能证据与缺口，供检索、正式稿、审稿和补证复用 |
| 主线分析报告 | `patent/<patent-slug>/analysis/mainline-analysis.md` | 主线分析单一报告；包含已确认技术方向、保护路径候选、保护客体初步判断、技术特征分层、候选发明点用途表、检索输入摘要和待检索确认问题 |
| 证据可信度信号 | `patent/<patent-slug>/evidence/evidence-quality-signals.yml` | mainline 子 agent 在抽取 evidence-matrix.md 同一次任务内产出；按 `references/evidence-quality-signals-schema.md` 中 source_type 七档 + confidence 三档 + 强制思考四步定义；不查文件后缀，按内容判 |

`mainline-analysis.md` 至少包含以下章节：

- `## 已确认技术方向`：来自用户直接指定方向或 `repo scout` 的 `selected_direction`；若用户直接声明方向，标注 `source: user-declared`
- `## 保护路径候选`：1 条或多条同一方向下的保护写法，每条至少含保护路径名称、保护客体、独权核心、技术问题、核心手段、预期效果、证据来源、风险
- `## 保护客体初步判断`：方法、装置、系统、设备、介质或组合保护的初步取舍
- `## 技术特征分层`：按保护路径或发明点分节，列必要技术特征、优选技术特征和实施细节；每项至少包含特征编号、技术特征、技术作用、技术效果、主体归属、适合写入位置、证据来源和待确认事项
- `## 候选发明点用途表`：按保护路径归类，固定用途为 `独权候选`、`从权候选`、`实施例支撑`、`替代实施方式`、`分案保留`、`暂不写入`
- `## 检索输入摘要`：汇总检索关键词、保护路径候选、候选发明点、关键证据和检索范围
- `## 待检索确认问题`：列出需要通过外部检索确认的新颖性、区别特征和技术效果问题

主线分析阶段的候选发明点不能直接作为独立权利要求核心。正式稿的独权核心只能消费检索后确认的 `claimable_invention_points`、`distinguishing_features` 和 Gate A 用户确认的 `selected_mainline`；说明书、实施例、从属权利要求和附图说明可读取完整上游产物作为支撑来源。

## 编排模式回写字段

回写状态文件 `patent/<patent-slug>/state/patent-iteration-state.json`：

- `source_material_roles`（若有新增核心资料）
- `selected_direction`：来自 `repo scout` 或用户声明的已确认技术方向
- `evidence_matrix_path` → `patent/<patent-slug>/evidence/evidence-matrix.md`
- `mainline_analysis_path` → `patent/<patent-slug>/analysis/mainline-analysis.md`
- `protection_path_candidates`：从 `mainline-analysis.md` 的 `## 保护路径候选` 解析的保护路径摘要数组（供检索消费）
- `protection_object`：来自 `## 保护客体初步判断` 的初步建议；`selected_protection_object` 只在 Gate A 用户确认后写入
- `feature_layers`：从 `mainline-analysis.md` 的 `## 技术特征分层` 解析的摘要；建议保留 `id`、`level`、`feature`、`technical_role`、`technical_effect`、`subject`、`drafting_position`、`evidence`、`open_issue`
- `invention_points`：从 `mainline-analysis.md` 的 `## 候选发明点用途表` 解析的候选发明点摘要
- `selected_mainline`：仅 Gate A 用户确认后写入，主线分析阶段不得写入

## 常见错误

- 把 repo scout 已确认方向又拆成多个不相关发明方向 → 应回到 repo scout 或标注分案，不得塞进同一保护路径分析
- 把应用场景误写成核心技术特征 → 平台无关骨架优先
- 证据不足的点强行拼成宽泛独立权利要求 → 标注风险，不硬拼
- 只有项目目录就直接做主线分析 → 先用 `cn-patent-repo-scout` 确认方向和核心资料
- 把扫描脚本的数值得分当作最终创新性判断 → 脚本只做初筛
- 把代码注释当作技术效果证据 → 优先用实验数据和性能对比

## 参考资料

- 详细分析方法论：[references/patentability-analysis.md](references/patentability-analysis.md)
- 特征分层与候选发明点用途表规则：[references/feature-layering.md](references/feature-layering.md)
- 对接编排器规则：[references/handoff-to-drafting.md](references/handoff-to-drafting.md)
- 可选前置 skill：`cn-patent-repo-scout`（没有明确方向时先扫描和确认核心资料）
- 可选关联 skill：`cn-patent-prior-art-search`（主线确定后做检索验证）
- 证据可信度信号 schema：[references/evidence-quality-signals-schema.md](references/evidence-quality-signals-schema.md)
