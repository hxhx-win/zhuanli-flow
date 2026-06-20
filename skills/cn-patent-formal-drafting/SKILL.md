---
name: cn-patent-formal-drafting
description: >-
  当用户已选定专利主线且完成证据收集（明确给出"已确认的主线 / 区别特征 / 支撑证据"，或提供的 `patent-iteration-state.json` 中 `selected_mainline` 字段已填），要求只起草 DOCX-ready 中文专利 Markdown 正式稿（摘要 + 摘要附图 + 权利要求书 + 说明书 + 附图说明 + `figure-manifest.json`）时使用。若用户从零开始（只给原始项目资料、未选主线），替代推荐：`cn-patent-workflow-orchestrator`。不挑主线、不检索、不审稿、不导出 .docx。触发词：`selected_mainline`、权利要求书、说明书、`figure-manifest.json`。
---

# 正式稿起草

基于已确认主线和证据，输出符合申报要求的 DOCX-ready Markdown 正式稿。

## 双模式

判断逻辑：`patent/<patent-slug>/state/patent-iteration-state.json` 存在 → 编排模式；否则 → 独立模式。

- **独立模式**：用户提供已确认主线 + 支撑证据/资料即可运行
- **编排模式**：由编排器调用，额外回写 `current_draft_path`, `draft_evidence_notes_path`, `embodiment_coverage_plan_path`, `figure_generation_plan_path`, `figure_manifest_path`, `deliverable_readiness`

## 前置读取（按起草阶段加载）

> ⚠️ **不是必须全部读**——按阶段命中加载。原"必读 10 项"已矩阵化，子 agent 只读当前阶段需要的部分以降低上下文压力。

**阶段 0 入口校验**（常驻必读，主输入）：

- [ ] `patent/<patent-slug>/disclosure/disclosure-draft.md`（交底书主体八节；面向读者的人读版本）
- [ ] `patent/<patent-slug>/reviews/pre-draft-review.md`（含 risk_inputs + "起草侧处理建议"列）
- [ ] `patent/<patent-slug>/state/drafting-context.json`（编排器在 step 4 派单前用 `cn-patent-workflow-orchestrator/scripts/extract-drafting-context.py` 生成；含 `gate_a`、`handoff`、`pre_review` 三个子树，~3 KB；起草 subagent **不再 Read state.json 全量**）
- [ ] 检查 `drafting-context.handoff.patent_dept_notes_path`：若非 null 且 `drafting-context.handoff.notes_fill_mode ∈ {prompt, document, manual}` → 读 `patent-dept-notes.md`（**专利部门强制意见，优先级最高**；HTML 注释跳过）；若 `notes_fill_mode = skip` 或字段缺失 → 跳过

> **铁律：起草 subagent 不读 mainline-analysis.md / prior-art-search-report.md / evidence-matrix.md 三份上游产物**；上游关键内容已由上游 skill 完整落入 disclosure-draft.md 与 pre-draft-review.md。详细 source mapping 见 [references/drafting-rules.md](references/drafting-rules.md) §输入前提。

**阶段 1 主线证据确认**（常驻）：

- [ ] [references/drafting-rules.md](references/drafting-rules.md)（起草规则与来源映射）

**阶段 2 权要起草**（常驻 + 命中 1 个判型细分）：

- [ ] [references/language-style-rules.md](references/language-style-rules.md)（B 风格 7 条硬规则；权要 / 发明内容 / 实施方式必读）
- [ ] [references/claim-type-classification.md](references/claim-type-classification.md)（判型）
- [ ] 命中保护客体后**只读 1 个**细分：
  - `protection_object = method` → [references/method-claim-drafting.md](references/method-claim-drafting.md)（涵盖方法、多主体方法、装置 / 电子设备 / 存储介质 / 系统配套保护）
  - `protection_object = structural` → [references/structural-claim-drafting.md](references/structural-claim-drafting.md)
  - `protection_object ∈ {system, device, electronic-equipment, storage-medium}` → 归入方法类配套保护，读 [references/method-claim-drafting.md](references/method-claim-drafting.md)

**阶段 3 说明书起草**（常驻）：

- [ ] language-style-rules.md（阶段 2 已读则免重）
- [ ] [references/formula-and-math.md](references/formula-and-math.md)（公式触发条件 + LaTeX 源规范）

**阶段 4 摘要 + 摘要附图**（无新增 reference，复用阶段 1~3）

**阶段 5 附图交接**（常驻 + 命中加载）：

- [ ] [references/figure-handoff.md](references/figure-handoff.md)
- [ ] 命中需生成附图 → `../cn-patent-docx-export/references/专利附图生成后端.md`（编排模式不存在则阻断；独立模式跳过 figure-manifest，正文起草不受影响）

## 工作流

| 步骤 | 动作 | 产出 |
|------|------|------|
| 1 | 确认主线、证据、保护客体 | — |
| 2 | 按保护客体判型读取细分 reference，起草独立权利要求 → 从属权利要求 | 权利要求书 |
| 3 | 制定实施方式覆盖计划，起草说明书（背景→发明内容→实施方式） | 说明书 + evidence notes |
| 4 | 起草摘要 + 摘要附图建议 | 摘要 |
| 5 | 生成附图交接清单 + figure-manifest.json | 附图产物 |
| 6 | 落盘正式稿 | DOCX-ready Markdown |

## 核心纪律

- 编排模式下必须确认 `drafting-context.gate_a.status` 为 `passed`、`confirmed` 或 `approved`；不得把 `selected_direction` 或 `prior_art_search.recommended_mainline` 当作已选主线
- 正式稿题目、保护客体、权要范围,以 `drafting-context.gate_a.drafting_decisions.*` 的 user 答案以及 `drafting-context.gate_a.selected_title` / `selected_protection_object` 字段为准,不再读 disclosure-draft.md 中的占位字段
- **专利部门强制意见优先级最高**：当 `drafting-context.handoff.drafting_initiator = patent_dept` 且 `drafting-context.handoff.notes_fill_mode ∈ {prompt, document, manual}` 时，必须读取并落地 `patent-dept-notes.md`；与 drafting-context.json 字段或本 skill 任意指引冲突时一律以 notes 为准；`notes_fill_mode = skip` 或字段缺失视为无意见。覆盖能力、追加项、登记格式等细则见 [references/drafting-rules.md](references/drafting-rules.md) §输入前提「专利部门强制意见」段
- **notes 强制条款落地与回溯**:每条 notes 条款(覆盖项 / 追加项 / 强调项 / 限制项 / 其他指示)必须在 evidence notes 中以"# patent-dept-notes 强制条款执行登记"小节按"条款类型(覆盖/追加/强调/限制/其他) | notes 出处行号或段落 | 落地正文位置 | 原值(若是覆盖)→ 新值"逐条登记;评审、修订与 Gate B 反馈中需保留这些条目。任何 notes 条款不得被遗漏或被审稿轮次反向回退
- **独权必要性筛查**：在保护发明点的前提下，独权只保留与区别特征直接因果相关的必要技术特征；非必要技术特征默认下放从属权利要求、实施方式或分案保留
- 方法类和结构类不得混用同一模板；装置、电子设备、存储介质和系统通常作为方法类配套保护，结构设备按结构类处理；必须按 `claim-type-classification.md` 判型并只读取命中的一个细分 reference
- 说明书不得用函数名/变量名/类名/枚举常量名替代技术特征描述
- 代码标识符仅首次出现时括号辅助说明
- `figure-manifest.json` 顶层必须是 `{"entries": [...]}` 对象，不得直接输出数组
- 正式稿交付前必须删除 `# 证据来源` 和 `# 风险点与待确认事项`
- 公式触发、变量定义和源格式以 `references/formula-and-math.md` 为唯一规则来源；独立公式用 `latex` 代码块，段内公式用 `\(...\)`
- 具体实施方式必须先有覆盖计划并完成密度自检；覆盖计划写入 evidence notes 或独立起草 notes，不得保留在最终 DOCX-ready 正文
- 资料不足时不得输出"看起来完整"的低质量稿
- 附图后端 reference 不存在或不可读 → 记录错误并停止
- **消费契约（N6，上游三份产物完全不读固化）**：主输入 = `disclosure-draft.md` + `pre-draft-review.md` + `drafting-context.json`（编排器在 step 4 派单前由 `extract-drafting-context.py` 从 state.json 抽取，含 Gate A 决策子树）；**起草 subagent 不读** mainline-analysis.md / prior-art-search-report.md / evidence-matrix.md，**也不读 state.json 全量**；上游关键内容已由 disclosure 第 2/3/4/5/6/7 节与 pre-draft `risk_inputs` 段完整吸收，缺失时记录为待确认事项由编排器在派单前补齐，不得 subagent 自行回查。subagent 不可派孙 agent（Claude Code 平台事实）；任何原文细节须由编排器在 step 4 派单 prompt 显式提供。详细 source mapping 见 [references/drafting-rules.md](references/drafting-rules.md)
- **决策不重复**：C1~C7 已在 `drafting-context.gate_a.drafting_decisions.*` 中确认（编排器派单前由 `extract-drafting-context.py` 从 state.json 抽取），正式稿起草不重复向用户提问；保护客体 / 保护范围 / 题目 / 发明点写法 / 引用方式 / 披露策略均按该子树用户答复执行
- **风险落地（N6 附属）**：pre-draft-review.md `## risk_inputs` 章节每条"起草侧处理建议"列必须在正式稿对应位置落地（如"在说明书明确成立前提"对应说明书相应段落、"加从权兜底"对应从权权要、"独权措辞规避"对应独权措辞）

## 语言风格纪律

详细 R1-R7 硬规则、起草前自检清单、审稿核对要点见 [references/language-style-rules.md](references/language-style-rules.md)；差例 / 好例对照见 [references/language-style-examples.md](references/language-style-examples.md)（起草按需读取）。

起草前必须按 `language-style-rules.md` 末尾的 10 项自检清单逐条核对；任一项 ✘ 不得进入下一阶段。

## 正式稿格式与 DOCX 导出契约

正式稿只负责生成 `cn-patent-docx-export` 可消费的 Markdown 源：精确使用 `## 摘要`、`## 摘要附图`、`## 权利要求书`、`## 说明书` 标题，权利要求编号连续，公式源规范，无内部工作章节，并单独提供 `figure-generation-plan.md` 和 `figure-manifest.json`。Word 版式由导出 skill 基于 `assets/reference.docx` 统一处理。落盘正式稿前必须按 cn-patent-docx-export 的 Markdown 源预检规则自查；不满足时不得声称 DOCX-ready。


## 输出物

- DOCX-ready Markdown 正式稿：`patent/<patent-slug>/drafts/markdown/<draft-name>.md`
- 正式稿配套 evidence notes：`patent/<patent-slug>/drafts/markdown/<draft-name>-evidence-notes.md`（记录证据来源、风险点、实施方式覆盖计划和密度自检结论，不进入 DOCX-ready 正文）
- 附图生成计划：`patent/<patent-slug>/drafts/figures/<draft-name>/figure-generation-plan.md`
- 附图 manifest：`patent/<patent-slug>/drafts/figures/<draft-name>/figure-manifest.json`

编排模式回写：

- `current_draft_path` → DOCX-ready Markdown 正式稿路径
- `draft_evidence_notes_path` → 正式稿配套 evidence notes 路径
- `embodiment_coverage_plan_path` → 实施方式覆盖计划路径（可与 evidence notes 相同，但必须可追踪）
- `figure_generation_plan_path` → 附图生成计划路径
- `figure_manifest_path` → 附图 manifest 路径
- `deliverable_readiness` → 正式稿预检状态、剩余风险和 DOCX 导出就绪度


## 参考资料

详细 references 见上文 §前置读取的阶段加载矩阵。阶段加载矩阵已表达所有必读 / 命中加载 / 按需加载的引用关系，不另列扁平链接列表。

可选关联 skill：`cn-patent-docx-export`（正式稿完成后导出 .docx）。
