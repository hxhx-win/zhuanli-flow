# 正式稿起草规则

本文件只规定 `cn-patent-formal-drafting` 的正式稿写作规则。方向发现、保护路径筛选、现有技术检索、创造性判断和代理师审稿不在本文件处理。

## 输入前提

正式起草前必须已经具备：

- 已确认的主线、保护客体、区别特征和检索后可主张发明点。编排模式下必须 `drafting-context.gate_a.status` 为 `passed`、`confirmed` 或 `approved`，且 `drafting-context.gate_a.selected_title`、`selected_mainline`、`selected_protection_object`、`claimable_invention_points`、`distinguishing_features` 已写入。
- 支撑证据：代码、技术交底、实验数据、图表、日志或设计文档。
- 资料角色声明：原创/核心/论文/代码/技术交底只作为发明证据；参考样稿只借结构和风格；现有技术材料只在被明确声明后使用。

缺少主线、区别特征或核心证据时，不得输出“看起来完整”的正式稿，应回到主线分析、检索或补证流程。

编排模式下，正式稿输入文件消费规则（**起草 subagent 仅读 disclosure-draft.md + pre-draft-review.md + drafting-context.json，不读 mainline-analysis / prior-art-search-report / evidence-matrix 三份上游产物，也不读 state.json 全量**；上游产物的关键内容由 disclosure 第 2/3/4/5/6/7 节和 pre-draft 的 risk_inputs / oneliner 段在上游 skill 阶段已完整吸收；state.json 中起草所需子树由编排器在 step 4 派单前用 `cn-patent-project-drafting/scripts/extract-drafting-context.py` 预提取为 `drafting-context.json`）：

- 背景技术 / 最接近现有技术：从 `disclosure-draft.md` 第 2 节（背景技术与现有技术）+ 第 7 节（与现有技术对比）取。
- 独立权利要求骨架：从 Gate A 确认的 `drafting-context.gate_a.selected_mainline` + `drafting-context.gate_a.claimable_invention_points` + `drafting-context.gate_a.distinguishing_features` 取（drafting-context.json 子字段）。
- 从属权利要求梯队：从 `disclosure-draft.md` 第 4.x 节末"附加技术特征"段 + 第 6.1 节"其他发明点 / 可选保护层次"段取。
- 实施方式与技术效果：从 `disclosure-draft.md` 第 4 节各小节正文 + 第 5 节（技术效果）取。
- 工程参数 / 公式 / 阈值：从 `disclosure-draft.md` 第 4.X 节"关键工程数值表"段取。
- 起草侧风险处理建议：从 `pre-draft-review.md` 的 `## risk_inputs` 段"起草侧处理建议"列取（每条必须在正式稿对应位置落地）。
- **专利部门强制意见**：当 `drafting-context.handoff.drafting_initiator = patent_dept` 且 `drafting-context.handoff.notes_fill_mode ∈ {prompt, document, manual}` 时，必须读取 `drafting-context.handoff.patent_dept_notes_path` 指向的 `patent-dept-notes.md`。**该文件具有最高优先级**，能力涵盖但不限于：覆盖 `drafting-context.gate_a.drafting_decisions.*`、`drafting-context.gate_a.selected_title` / `selected_mainline` / `selected_protection_object`、`claimable_invention_points` 写法、pre-draft-review.md risk_inputs 风险处理建议；追加新增说明书章节、实施例、从权、附图、术语；强调技术细节；限制措辞 / 命名禁用词；其他任意撰写指示。**所有 notes 条款均须落入正式稿**，与本规则、drafting-context.json 字段冲突时一律以 notes 为准。落入正式稿后必须在 evidence notes 中按条款类型逐条登记，便于回溯。`notes_fill_mode = skip` 或 path = null 时视为无强制意见。

铁律（N6 消费契约固化）：
- 起草 subagent **完全不读** mainline-analysis.md / prior-art-search-report.md / evidence-matrix.md 三份上游产物。
- 上游产物的关键内容已由上游 skill（cn-patent-mainline-analysis、cn-patent-prior-art-search、cn-patent-disclosure-draft）在 disclosure-draft.md 与 pre-draft-review.md 中完整落地；如发现 disclosure / pre-draft 中缺失某项关键内容，应记录为待确认事项，由编排器在 Gate A 前补齐，**不得**起草 subagent 自行回查上游。
- 起草 subagent 不可派孙 agent；任何需要回查的原文细节必须由编排器在 step 4 派单前显式写入 prompt。

`selected_direction` 只是已确认技术方向，`prior_art_search.recommended_mainline` 是兼容字段、语义为检索后推荐保护路径；二者都不能替代 `drafting-context.gate_a.selected_mainline`。

## 正式稿输出结构

正式稿 Markdown 必须按导出脚本识别的 section 标题组织。`reference.docx` 中的“技术领域、背景技术、发明内容、附图说明、具体实施方式”属于说明书内部小节，不作为和“摘要/权利要求书/说明书”同级的导出 section。

```markdown
## 摘要
【摘要正文】

## 摘要附图
【摘要附图说明文字】

## 权利要求书
1. 【独立权利要求】
2. 【从属权利要求】

## 说明书
### 发明名称

【发明名称正文】

### 技术领域

【技术领域正文】

### 背景技术

【背景技术正文】

### 发明内容

【发明内容正文】

### 附图说明

【图1、图2等说明文字】

### 具体实施方式

### 实施例1
【实施例正文】

### 可选实施方式
【可选实施方式正文】
```

`说明书附图` 不作为必需 Markdown section；有附图时由 `figure-manifest.json` 和导出脚本在 DOCX 中生成/嵌入对应附图内容。

交付给 `cn-patent-docx-export` 前，必须删除内部工作章节：

- `# 证据来源`
- `# 风险点与待确认事项`
- 分析表、工作记录、修改计划、检索过程记录

附图交接清单和 `figure-manifest.json` 按 [figure-handoff.md](figure-handoff.md) 处理。

## Markdown 源补充预检

`../SKILL.md` 已规定导出契约。本节只补充实际导出中常见但容易被忽略的问题；落盘正式稿前必须自查。

- `###` 仅用于说明书内部小标题：发明名称、技术领域、背景技术、发明内容、附图说明、具体实施方式、实施例N、可选实施方式、替代实施方式。步骤编号、参数说明、公式推导、实验条件、风险说明等均写成正文段落，不设小标题，也不要加粗。
- 不要为了“说明书附图”手写空的 `## 说明书附图`；只有在 manifest 中存在已生成 `imagePath` 时，导出阶段才生成说明书附图内容。
- 不要在正式稿正文中保留 `附图交接清单`、figure-generation 说明、manifest 摘要或图片生成记录；这些只能存在于独立交接文件。
- 不要把 `# 证据来源`、`# 风险点与待确认事项`、分析表、工作记录、修改计划、检索过程记录写入正式稿。
- 公式源按 [formula-and-math.md](formula-and-math.md) 写；避免 `sum(...)`、`sqrt(...)`、`mu(...)` 等伪公式文本。


## 写作原则

- 保护对象是技术方案、技术特征组合及步骤或模块关系，不是仓库文件名、函数名、脚本名或界面操作。
- 凡写入权利要求的技术特征，说明书必须展开；凡写入技术效果，必须对应具体技术手段。
- 合理推断可以作为实施例或待确认事项，不得写成确定事实。
- 应用场景、平台、中间件和仿真环境通常放入实施例；只有其本身构成区别特征并有证据支撑时，才写入权利要求。
- 文风必须是专利文本，不写“本文提出”“本课题研究了”“实验表明优于所有现有方法”“点击按钮实现”等表述。
- 成熟稿件的核心不是篇幅长，而是权利要求、说明书和实施方式之间形成可追溯的“特征 -> 作用 -> 技术效果”链条。
- 软件类稿件应把代码标识符抽象为技术对象、数据结构、判定条件、执行路径或模块关系；代码标识符仅在首次出现时括号辅助，不得替代技术特征。
- 公式触发规则只按 [formula-and-math.md](formula-and-math.md) 执行；本文件不另设独立公式触发条件。
- 起草前必须按 [claim-type-classification.md](claim-type-classification.md) 判定保护客体类型，并只读取命中的一个细分 reference。

## 保护客体细分模板

从摘要、权利要求书到说明书的详细写法不在本文件重复维护。起草前先读取 [claim-type-classification.md](claim-type-classification.md) 完成判型，再按保护客体进入细分 reference：

- 命中方法类、多主体方法、方法+装置+设备+介质组合保护时，读取 [method-claim-drafting.md](method-claim-drafting.md)。
- 命中结构类时，读取 [structural-claim-drafting.md](structural-claim-drafting.md)。
- 系统、装置、电子设备、存储介质通常作为方法类配套保护处理，读取方法类模板；同时出现结构信号时，按主要区别特征选择方法类或结构类，无法确定则回到 Gate A。

细分 reference 负责维护推荐表达、摘要、权利要求书、背景技术、发明内容、附图说明和具体实施方式模板。本文件只规定正式稿输出契约、通用写作原则、单一路由和资料不足处理。



## 资料不足处理

- 缺少已确认主线、区别特征或核心支撑证据：阻断，回到前序流程。
- 缺少局部参数、替代实施方式或非核心实施细节：可标为“待用户确认”或“默认假设”，不得写成确定事实。
- 缺少参考样稿：不阻断正式起草，但不得臆造样稿风格。

资料不足时，输出应区分：

- 已确定内容
- 默认假设
- 待确认事项
- 需要补充的证据
