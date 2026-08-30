---
name: cn-patent-disclosure-draft
description: 当用户已完成 cn-patent-mainline-analysis 与 cn-patent-prior-art-search，需要在进入正式稿起草前做起草前评审、生成技术版交底书时使用。承载编排器 step 3 的两个子阶段：评审 + 技术交底书。用户分流决策与 Gate A 段（起草前决策 + 确认）由编排器执行。不挑主线、不重做检索、不起草权要。触发词：起草前评审、技术交底书、disclosure draft、pre-draft review。
---

# 起草前评审与技术交底书 skill

承载编排器 step 3 的两个子阶段：评审（review）+ 技术交底书（disclosure-generation）。两类 subagent 共用本 SKILL.md 骨架，按 stage 各自加载对应 references。

## 适用边界

- 仅在编排模式下使用；状态文件 `patent/<patent-slug>/state/patent-iteration-state.json` 必须已含 `prior_art_search.status = completed`
- 不重新挑主线（用 `cn-patent-mainline-analysis`）
- 不重新检索（用 `cn-patent-prior-art-search`）
- 不起草权要（评审通过后由 `cn-patent-formal-drafting` 起草）
- 不做起草前决策与 Gate A 确认（由编排器自执行，见 `cn-patent-workflow-orchestrator/references/drafting-decisions.md`）

## 子阶段工作流

| 子阶段 | 视角 | 动作 | 主要产物 | 写入字段 |
|---|---|---|---|---|
| review | 资深专利代理师 / 起草前评审者：以稳妥起草为目标，对发明点的合规性、因果链、区别特征反例、可面试度做闸前体检，宁可标 `revise-required` 也不放含糊点过闸 | 派 subagent 隔离执行：subagent 加载 `references/review-protocol.md` + 读 4 份输入 + 三道复审 + 判定 `decision_readiness` 软字段 + 生成 `proposal_summary_oneliner`（≤60 字）+ Write `pre-draft-review.md` + 回 ≤200 字 summary | `patent/<patent-slug>/reviews/pre-draft-review.md` | `step_3.pre_draft_review.*`（含 verdict + decision_readiness + chain_check + proposal_summary_oneliner） |
| disclosure-generation | 研发人员 + 专利工程师双视角：以研发口径把技术方案讲清楚（机制 / 数据流 / 实验），同时以专利工程师口径锚定权利要求范围与从权层次，不替代代理师抠条款 | 派 subagent 加载 `references/drafting-discipline.md` + `assets/disclosure-template.md` + 读 4 份输入 + 写技术版交底书主体八节；"题目"/"保护客体"/"权利要求范围"字段允许占位"(待用户确认)"（由编排器在起草前决策阶段填入 state） | `patent/<patent-slug>/disclosure/disclosure-draft.md` | `step_3.disclosure_draft.*` |

起草前决策（原 3b）与 Gate A 确认由编排器执行，见 `cn-patent-workflow-orchestrator/references/drafting-decisions.md`。用户分流决策（原 3d）在 step 3 末尾由编排器 AskUserQuestion 五选执行。

## 出口分支（disclosure-generation 完成后）

disclosure-generation 完成后，**不直接进 step-3.post-disclosure-decision**，而是先经 `step-3.inventor-review`：

| 出口 stage | 执行者 |
|---|---|
| `step-3.inventor-review` | `cn-patent-disclosure-review` skill（发明人 3 阶段审核） |
| `step-3.post-disclosure-decision` | 由编排器在 inventor-review `gate_passed=true` 后进入 |

**REQUIRED CONTEXT：** 见 `cn-patent-disclosure-review/SKILL.md`。

修订模式：当 `cn-patent-disclosure-review` 累积反馈触发整体修订时，编排器以 `revision_mode: true` + `prior_draft_path` + `inventor_feedback` 重新派单 disclosure-generation subagent。subagent 复用本 SKILL.md 的 drafting-discipline.md 准绳。

## 核心铁律

- 四档 verdict（go / revise-recommended / revise-required / stop-recommended）是软闸门，不存在硬阻断；最终决策权在用户（编排器侧处理）
- **唯一硬阻断（review subagent 侧）**：复审 4 五栏因果链一致性自检中任一 IP 命中 `chain_broken` → verdict 直接置为 `revise-required`，跳过软合成。`chain_check` 字段必须随 verdict 一并写入 state。详见 `references/review-protocol.md` 「预检阻断硬规则」段
- 评审 subagent 必须执行 IP 三句话可面试测：对每个独权核心 / 独权步骤 IP，写出"做什么 / 差异 / 因果"三句话；写不出标 `interview_failed`
- 评审 subagent 必须生成 `proposal_summary_oneliner`（≤60 字中文）并写入 state；若任一 IP `interview_failed`，oneliner 必须为 `null`，不得编造
- 评审 subagent 必须输出 `decision_readiness` 软字段（`ready` / `needs_supplement`），判定规则见 `references/review-protocol.md`
- 评审与技术交底书都派 subagent；subagent 直接 Write 落盘，主 agent 只收 ≤600 字摘要；铁律：写到磁盘的内容不返回给父 agent
- 技术交底书主体八节字段严格对齐公司官方模板，不得新增非官方字段、不得调整字段顺序；推荐项、决策依据、对照表、风险登记、特征分层等编排/分析层信息只在上游产物中存在，不进交底书
- 修订次数上限 3 次（用户在 step 3 用户分流决策选"修订交底书"超过 3 次时编排器提示考虑"调整主线"）
- subagent 不直接 Read PDF / docx / 源码文件 / 截图 / 实验数据 / 外链网页等大体量原始资料；所需信息必须由上游 subagent 在 evidence-matrix.md / mainline-analysis.md / prior-art-search-report.md 中预吸收，缺失项记为待确认事项由编排器在派单前补齐

## subagent 入口分路

subagent 启动后，根据主编排器派单 prompt 中的 `stage` 字段加载对应纪律，**不要读另一份**：

| stage | 必读纪律 | 必读输入产物 | 写入产物 |
|---|---|---|---|
| review | `references/review-protocol.md` | df-rationale-signals.yml + evidence-matrix.md + mainline-analysis.md + prior-art-search-report.md | `patent/<patent-slug>/reviews/pre-draft-review.md` |
| disclosure-generation | `references/drafting-discipline.md` + `assets/disclosure-template.md` | **必读列表 6 份**（按顺序 Read，前 2 份是模板与纪律，后 4 份是上游产物）：(1) `assets/disclosure-template.md` (2) `references/drafting-discipline.md` (3) pre-draft-review.md (4) mainline-analysis.md (5) evidence-matrix.md (6) prior-art-search-report.md | `patent/<patent-slug>/disclosure/disclosure-draft.md` |

所有输入与输出路径必须从主编排器派单 prompt 中"输入产物绝对路径列表"与"输出产物绝对路径"两个字段读取，**禁止 subagent 自行猜路径**。

review 与 disclosure-generation 共享 mainline-analysis.md / evidence-matrix.md / prior-art-search-report.md 三份输入，由两个隔离 subagent 各自 Read 一次（重复读取是隔离架构的清醒代价，token 成本只发生在 subagent 各自 context 内，不进主编排器 context）。

## 主编排器派 subagent prompt 契约

主编排器调用 `Agent(subagent_type=general-purpose)` 派 subagent 时，prompt 必须包含以下三段字段：

```
stage: review | disclosure-generation
skill_root: <skills_root>/cn-patent-disclosure-draft
patent_root: <patent root 绝对路径>
任务: subagent 内部通过 Skill 工具加载 cn-patent-disclosure-draft SKILL.md,按其「subagent 入口分路」段加载对应 stage 的纪律 references。
输入产物绝对路径列表（按列出顺序 Read，作为 Skill 加载失败时的硬路径兜底）:
  - <绝对路径 1>
  - <绝对路径 2>
  - ...
输出产物绝对路径: <绝对路径>
```

主编排器侧 `cn-patent-workflow-orchestrator/references/agent-tool-mapping.md` 中 disclosure-draft 派单条目须引用本 SKILL.md 的入口分路段与本契约段，避免两边漂移。

## 产物路径

- 评审报告：`patent/<patent-slug>/reviews/pre-draft-review.md`
- 技术交底书：`patent/<patent-slug>/disclosure/disclosure-draft.md`

## 状态字段回写

- `step_3.stage`：每个子阶段开始时更新（review / disclosure-generation / completed）
- `step_3.pre_draft_review.*`：评审完成后写入；含 `verdict`、`decision_readiness`、`chain_check`、`proposal_summary_oneliner`、`risk_inputs` 数组
- `step_3.disclosure_draft.*`：技术交底书完成；含 `draft_path`
- `step_3.status` ∈ {in-progress, completed, stopped}；用户分流决策完成后由编排器写 completed

## 参考资料

- 评审协议（评审 subagent 必读）：[references/review-protocol.md](references/review-protocol.md)
- 起草纪律（交底书 subagent 必读）：[references/drafting-discipline.md](references/drafting-discipline.md)
- 交底书模板：[assets/disclosure-template.md](assets/disclosure-template.md)
- 类目配置：已迁到 `cn-patent-workflow-orchestrator/assets/decision-categories.json`，本 skill 不再持有
- 证据可信度信号 schema：`../cn-patent-mainline-analysis/references/evidence-quality-signals-schema.md`
- DF 反例自检规则：`../cn-patent-prior-art-search/references/creativity-screening.md`（末尾段）

## 跨平台 fallback

Agent tool / 子 agent 机制是 Claude Code 特性。在 Cursor / Codex 等环境无子 agent 工具时：

- 评审：主 agent 自行加载 `references/review-protocol.md`，按其指导直读 4 份输入、直写 pre-draft-review.md
- 技术交底书：主 agent 自行加载 `references/drafting-discipline.md` + `assets/disclosure-template.md`，按其指导直读 4 份输入、直写 disclosure-draft.md；起草完成后用户手动 `/compact`
- verbatim 回查原始资料：主 agent 自行 Read 单文件 + 立即丢弃中间态（用户手动 `/compact`）
