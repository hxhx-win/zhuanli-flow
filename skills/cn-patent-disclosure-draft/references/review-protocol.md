# 3a 审核评估细则（信号驱动版）

3a 由 subagent 隔离执行。subagent 读 4 份输入：

1. `patent/<patent-slug>/evidence/df-rationale-signals.yml`（来自 prior-art）
2. `patent/<patent-slug>/evidence/evidence-matrix.md`（按需 grep 锚点节）
3. `patent/<patent-slug>/analysis/mainline-analysis.md`（读保护路径候选 + 候选发明点用途表）
4. `patent/<patent-slug>/evidence/prior-art-search-report.md`（读最接近现有技术 + 检索后可主张发明点）

落盘到 `pre-draft-review.md` 时，正文中的 IP / DF 等内部编号应按 `cn-patent-disclosure-draft/references/drafting-discipline.md § 1 编号语言` 展开为中文（"发明点一" / "区别特征一"）。`risk_inputs` 表的"编号"列为机读契约（下游 formal-drafting subagent 依赖），保留 IP-N / DF-N 原样。

## 三道复审

### 复审 1：DF 反例复核（创新性维度）

读 df-rationale-signals.yml.aggregate_signals：

| 触发条件 | 维度判定 |
|---|---|
| `dfs_after_check_structural == 0` 且 `dfs_after_check_engineering > dfs_after_check_parameter` | stop-recommended |
| `dfs_after_check_structural == 0`（其他情况） | revise-recommended |
| `dfs_after_check_structural ≥ 1` 且 `total_dfs ≥ 2` | go |
| `dfs_with_strong_counter_example > dfs_claimed_structural / 2`（通胀检测） | revise-recommended，并在报告里点名 |
| `dfs_with_none_counter_example > total_dfs / 2`（应付检测） | revise-required |
| 其他 | revise-recommended |

直接使用 dfs_after_check_* 字段，避开通胀的初判 structural。

### 复审 2：IP 三句话可面试测

对每个 use = independent_claim_core 或 independent_claim_step 的 IP，subagent 必须用三句话写出：

1. 它做什么（一句话技术动作）
2. 比常规做法不同在哪（一句话差异）
3. 为什么这个差异有技术效果（一句话因果）

写不出三句话 → 该 IP 标记 interview_failed。

| 触发条件 | 维度判定 |
|---|---|
| `interview_failed_count == 0` | go |
| `interview_failed_count == 1` 且其他 IP 健全 | revise-recommended |
| `interview_failed_count ≥ 2` 或失败 IP 是独权核心 | revise-required |

### 复审 3：五栏因果链一致性自检（横向一致性维度）

按公司官方交底书模板要求，五个栏目必须横向可追溯：

1. 现有技术方案
2. 现有技术方案的缺陷
3. 本发明所要解决的技术问题
4. 本发明完整的技术方案
5. 本发明的有益效果

subagent 必须写出"缺陷 → 技术问题 → 完整方案 → 有益效果"的对应关系（用箭头串成一条句子，跨四栏）。每条独权候选 IP 都要写出一条；写不出对应关系标 `chain_broken`，并把缺失栏写入 `broken_items`。

| 触发条件 | 维度判定 |
|---|---|
| 所有 IP 均能写出完整四栏链 | go |
| 任一 IP 缺单栏（如缺有益效果） | revise-recommended |
| 任一 IP 缺 ≥ 2 栏，或缺陷与技术方案对不上 | revise-required |

`chain_broken` 是**预检阻断**：任一 IP 出现 chain_broken 时 verdict 直接为 `revise-required`，跳过下面的"裁决合成规则"软合成。这是硬规则（即复审 3 出现 chain_broken 即触发）。

## IP 一句话发明点概括（oneliner）

复审 3 通过后，subagent 必须为整篇交底书写一句 ≤ 60 字的中文概括，回答"这份提案的核心发明点 / 保护点是什么"，写入 state `step_3.pre_draft_review.proposal_summary_oneliner`。该字段用于 handoff-package.md 摘要位（专利部门一眼看到核心）。

写不出 oneliner 与 IP 三句话写不出同因——若复审 3 出现 ≥ 1 个 interview_failed，oneliner 必须为 null，不得编造。

## 主线收敛维度（沿用原 rubric）

protection_object 明确、保护范围有边界 → go；范围模糊 → revise-recommended；多条不相关主线混杂 → revise-required。

## 裁决合成规则（四档软闸门）

**预检阻断（硬规则）**：复审 3 出现 `chain_broken` → verdict 直接 `revise-required`，不进入下面的软合成。

软合成（无预检阻断时）：

| 维度组合 | 整体 verdict |
|---|---|
| 三维度全 go | go |
| 任一维度 revise-recommended，其他 go | revise-recommended |
| ≥ 2 维度 revise-recommended，或任一 revise-required | revise-required |
| 任一维度 stop-recommended | stop-recommended |

除"预检阻断"外不存在硬阻断；最终决策权在用户。

### 落盘 verdict 中文化（pre-draft-review.md 写法）

写入 state.step_3.pre_draft_review.verdict 时保留英文枚举（供脚本读取）；落盘到 `pre-draft-review.md` 正文时按下表中文陈述：

| 英文枚举 | 落盘中文写法 |
|---|---|
| go | 评审通过 |
| revise-recommended | 建议修订（非阻断） |
| revise-required | 需要修订后再起草 |
| stop-recommended | 建议中止该方向 |

`decision_readiness` 同理：state 字段保留 `ready` / `needs_supplement`，落盘 md 写"起草前决策准备度：已就绪"或"起草前决策准备度：需补充材料"。

`interview_failed` / `chain_broken` 同理：state 字段保留英文枚举，落盘 md 写"该发明点未能通过三句话验证"（interview_failed）/"该发明点缺少 X 栏对应内容（X 列出具体缺栏）"（chain_broken）。

## 风险输入汇集（喂给评估）

| 来源 | 字段 |
|---|---|
| df-rationale-signals.yml | aggregate_signals.* + dfs_with_strong_counter_example 命中条目 |
| mainline-analysis.md | 各保护路径的"风险"字段 |
| mainline-analysis.md | 技术特征分层中各项的"待确认事项" |
| prior-art-search-report.md | 保护路径创造性筛选表的"风险"列 |

## pre-draft-review.md 输出结构

必含章节（章节名为落盘 md 写法；正文遵循"内部枚举只留 state、md 写中文陈述"原则）：

- `## 输入摘要`（含 aggregate_signals 关键字段）
- `## 三维度评估说明`（含信号文件引用；逐维度用中文陈述结论与依据）
- `## 区别特征反例复核`（节选 dfs_with_strong_counter_example 命中条目；落盘正文将 DF-N 展开为"区别特征一/二…"）
- `## 发明点三句话验证`（每个独权核心发明点一段；未通过的写"该发明点未能通过三句话验证"）
- `## 五栏因果链一致性自检`（每个独权发明点一条链；缺栏者写"该发明点缺少 X 栏对应内容"）
- `## 发明点一句话概括`（≤ 60 字中文一句；预检阻断或三句话验证未通过时为空，不编造）
- `## 评审结论与理由`（按"裁决合成规则 § 落盘 verdict 中文化"表写中文陈述；若预检阻断必须注明）
- `## 补证清单`（修档时）
- `## 待澄清问题`（修档时）
- `## 风险登记`（汇集所有来源 + 复审新发现；**表头与列名为机读契约，保留原样**：`| 编号 | 来源 | 描述 | severity | 影响范围 | 起草侧处理建议 |`，"编号"列保留 IP-N / DF-N 等原始标记；"起草侧处理建议"列由评审 subagent 按风险类型给出（说明书前提声明 / 从权兜底 / 独权措辞规避 / 实施例丰满 / 上位措辞等），formal-drafting 起草正式稿时直读该列把建议落到正式稿对应位置）

## 3a subagent 不做的事

- 不重新做 prior-art 检索
- 不重新评 DF type 标签（直接用信号文件）
- 不与用户对话（subagent 是隔离的，互动在编排器侧）
- 不写交底书或决策附录（那是 3c 的事）

## 反通胀自检句

subagent 在输出 verdict 前必须自问一遍：

> 如果你的判定让所有维度都 go，再问自己一次：上游产物是否被通胀了？dfs_with_strong_counter_example 占比是否 > 0？

## decision_readiness 软字段评分(新增)

评审 subagent 在出 verdict 同时,必须输出 `decision_readiness` 软字段(`ready` / `needs_supplement`),用于提示 Gate A 段起草前决策子阶段是否需要先回退补料。

### 判定规则

按以下三个条件评估,任一不满足 → `needs_supplement`:

| 条件 | 检查项 |
|---|---|
| 题目候选清晰 | `prior_art_search.recommended_mainline` 非空 **且** `selected_direction.title` 非空 |
| 保护客体候选清晰 | `mainline-analysis.md#保护客体初步判断` 给出明确候选(方法 / 装置 / 介质 / 系统 等命名出现) |
| 写入范围清晰 | `claimable_invention_points` 至少 1 条 **且** 每条标注 `use ∈ {独权候选, 从权候选, 实施例支撑, 替代实施方式, 分案保留, 暂不写入}` |

三项全满足 → `ready`。

### 影响

`needs_supplement` 不触发硬阻断,仅在 Gate A 段入口由编排器输出 warning + 候选补料项。详细见 `cn-patent-project-drafting/references/orchestration-philosophy.md § Gate 哲学` 与 `scripts/lib/preconditions.py` 中 `gate-a.drafting-decisions` enter 条件。
