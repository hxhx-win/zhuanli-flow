---
name: cn-patent-attorney-review
description: 当用户已有一份中文发明专利稿（Markdown 或文本），要求专利代理师视角逐项审查、输出分优先级（高 / 中 / 形式）的修改意见，或要求基于用户反馈做多轮修订迭代时使用。输入：现成专利稿；输出：修改意见 + 修订稿。仅审查既有稿的合规性、信息密度、保护层次，不重新选主线、不重新检索现有技术。触发词：审稿、代理师意见、专利稿修改、专利修订、attorney review、`reviews/attorney-review.md`。
---

# 代理师审稿

以专利代理师视角审阅专利稿，输出分优先级的修改意见，并支持用户反馈驱动的修订迭代。

## 双模式

判断逻辑：`patent/<patent-slug>/state/patent-iteration-state.json` 存在 → 编排模式；否则 → 独立模式。

- **独立模式**：用户提供一份专利稿（任意来源）即可运行，输出修改意见
- **编排模式**：由编排器调用，额外回写 `review_feedback.*`, `history.attorney_review_rounds`；意见追加到 `patent/<patent-slug>/reviews/attorney-review.md`

## 工作流

| 步骤 | 动作 | 产出 |
|------|------|------|
| 0 | 读取审查清单入口，按模式准备最小上下文 | 审查输入边界 |
| 1 | 通读专利稿，建立整体印象 | — |
| 1.5 | 让用户选择单 agent / 多 agent 审查模式 | 审查模式决策 |
| 2 | 按用户选择执行单 agent 或多 agent 审查 | 分维度问题清单 |
| 3 | 汇总、去重并分级所有审查发现 | 问题清单 |
| 4 | 分优先级输出修改意见 | 代理师修改意见 |
| 5 | 列出需用户选择/补证/授权的事项 | 待决事项 |
| 6 | 等待用户反馈 | **用户决策** |
| 7 | 按用户反馈修订 | 修订稿 |
| 8 | 呈现修订结果，等待用户复核 | **用户复核** |

## 审查模式选择

正式审查前，必须先让用户选择审查模式：

- **单 agent 审查**：速度快、成本低、意见统一，适合轻量复核；但审查视角单一，可能遗漏跨章节或深层问题。
- **多 agent 并行审查**：多维度并行覆盖、交叉校验更充分，适合正式交付前或高风险稿件；但耗时更长，输出问题也需要额外汇总去重。

用户未选择前，不得进入正式审查、写入 `reviews/attorney-review.md` 或修订稿件。

## 单 agent 审稿

当用户选择单 agent 审查时，主 agent 必须读取 `references/review-checklists.md` 中全部审查清单（含 `## 气质审查清单`、`## 权利要求审查清单`、`## 说明书支撑审查清单`、`## 形式与证据审查清单`、`## 语言风格审查清单（B 风格硬规则）`、`## 法条合规审查清单（审查员视角）`），并自行覆盖气质、权利要求、说明书支撑、形式与证据、语言风格和法条合规六大维度。语言风格按 `language-style-rules.md` 的 R1–R7 逐条扫描，命中差例特征（`以使`、`不可分割`、`第一方面` 等）必须按 `language-style-examples.md` 中差例重写示例输出建议。气质审查清单本身已列必读输入与 5 子项判定规则，主 agent 按清单执行即可。

## 多 agent 审稿

当用户选择多 agent 并行审查时，主 agent **不亲自审查**，按 [references/multi-agent-dispatch.md](references/multi-agent-dispatch.md) 派 6 方向 + 综合 + revision 共 8 个 subagent。6 方向命名 / 必读 references / 派单 prompt 模板 / 派单硬规则 / 异常重派规则均沉到 dispatch.md，主 agent 上下文不重复加载。

主 agent 职责：
- 单条 message 并行派 6 方向 subagent，等齐 6 份子审查，并在派综合前对 06 输出做 schema 嗅探（详见 dispatch.md 异常路径）
- 派综合 subagent 合并同根因问题、按 `references/review-methodology.md` 处理结论冲突
- 产出综合 `patent/<patent-slug>/reviews/attorney-review.md`
- **不重复执行各方向审查清单**

子 agent 只读纪律：不得修改草稿、状态文件或 review 文件；不得读取 PDF；未收齐 6 份子审查不得进入综合与修订。

> revision subagent 契约（mode=revision）见 [references/revision-mode.md](references/revision-mode.md)。

## 核心纪律

- 代理师意见独立成文，不写进权利要求书或说明书正文
- 子 agent 只能只读审稿，不得直接改稿或推进 Gate
- 修订后必须等用户复核，不得把"修完"当"用户接受"
- 用户否定修改 → 重新审稿（编排模式下状态回退到 attorney-review）
- 质量检查通过不能替代用户复核确认
- 不得一次审稿后直接进入最终交付
- 编排模式下：审稿前必须确认风险确认已通过 + 补改稿已落盘
- **patent-dept-notes 强制条款不得回退**：编排模式下，审稿前必须读 evidence notes 中"# patent-dept-notes 强制条款执行登记"小节，把所有条款（覆盖项 / 追加项 / 强调项 / 限制项 / 其他指示）视为业主级硬意见；审稿意见**不得**反向建议把覆盖值改回 drafting_decisions / selected_* 的原值，**也不得**建议删除/弱化 notes 追加的章节、实施例、从权、附图或术语限制，即使从专利法或质量样稿角度更优；若代理师认为某条 notes 条款会带来法律或撰写质量风险，只能列入"需要用户选择的事项"段说明权衡，等待用户回复，不得自行修订。`handoff.notes_fill_mode = skip` 或字段缺失时该条不生效
- 不得把质量检查脚本的 warning 当作语义审查结论；独权过密、说明书支撑不足和实施方式密度不足必须由审稿意见明确判断

## 修改意见结构

- 总体结论
- 高优先级问题
- 中优先级问题
- 形式与术语问题
- 气质审查发现（5 子项：独权肥度 / 抽象层 / 细节落点 / 节奏对照 / 密度匹配）
- 语言风格问题（按 `language-style-rules.md` 的 R1–R7 分组，引用 `language-style-examples.md` 差例重写示例）
- 法条合规问题（按 22.2 / 22.3 / 22.4 / 26.3 / 26.4 分组）
- 需要用户选择的事项
- 需要用户补充的材料
- 本轮修改计划

## 输出物

- 代理师修改意见（按上述结构）
- 风险点清单
- 修订稿（用户反馈后）

## 常见错误

- 把修改意见写进正式稿正文 → 必须独立成文
- 自己选择所有修改项直接修订 → 必须等用户决策
- 修完就进入交付 → 必须等用户复核

## 参考资料

- 审稿方法论：[references/review-methodology.md](references/review-methodology.md)
- 审查清单：[references/review-checklists.md](references/review-checklists.md)
- B 风格语言硬规则：[../cn-patent-formal-drafting/references/language-style-rules.md](../cn-patent-formal-drafting/references/language-style-rules.md)
- B 风格差例、好例与重写示范：[../cn-patent-formal-drafting/references/language-style-examples.md](../cn-patent-formal-drafting/references/language-style-examples.md)
- 迭代与回退规则：审稿前风险 / Gate B 硬门禁 / 修订复核见 `../cn-patent-workflow-orchestrator/references/orchestration-philosophy.md § 审稿前风险与 Gate B/修订复核哲学`；状态字段与阶段流转见 `../cn-patent-workflow-orchestrator/references/state-machine-reference.md § 审稿/修订迭代状态流`
- 可选关联 skill：`cn-patent-formal-drafting`（修订后可能需要重新起草部分内容）
