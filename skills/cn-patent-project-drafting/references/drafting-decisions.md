# Gate A 段 起草前决策子阶段 执行规则

执行者:编排器主 agent。不调任何 sub-skill。

## 数据源

- `patent/<patent-slug>/analysis/mainline-analysis.md`
- `patent/<patent-slug>/evidence/prior-art-search-report.md`
- `patent/<patent-slug>/reviews/pre-draft-review.md`
- `patent/<patent-slug>/disclosure/disclosure-draft.md`
- `patent/<patent-slug>/reviews/patent-dept-notes.md`(可选,作为额外提示传给候选项 description)

## 配置文件

类目元数据 + 命中规则 + 候选项来源 + state 写入字段,集中在:

`cn-patent-project-drafting/assets/decision-categories.json`

类目扩展(如 C8、C9)只改 json,不改本文件。

## 循环逻辑

1. 读 `decision-categories.json`
2. 读 state 与数据源 markdown
3. 对每个类目 entry,按 `hit_rule.type` 评估是否命中:
   - `always_hit`:始终命中
   - `evidence_pattern_present`:`source_file` 含 `patterns` 任一关键词
   - `count_grouped_by_field_gte`:按 `list_field` 字段总数 >= threshold
   - `list_field_contains_value`:列表字段 contains values 任一值
4. 命中的类目,按 `candidate_source` 抽候选项(从 state 字段或文档章节)
5. 候选项不足 `candidate_min_count` 时,按 `candidate_fallback` 补足
6. 逐题用 AskUserQuestion 问;候选项已抽好,作为 options 传入
7. 若 `patent-dept-notes.md` 存在,把相关偏好作为该题的 description 补充
8. 答案写入 `gate_a.drafting_decisions.categories.<Cn>.answer`(或 `.answers` 多值)
9. 按 `write_to_state` 字段路径回写顶层(如 `selected_title`、`selected_protection_object`、`selected_mainline`)

## 出口

所有命中类目全答完 → `gate_a.drafting_decisions.status = completed` → 进入 Gate A 确认子阶段。

不提供"退回研发补料"出口(见 spec § 3.2.2 说明)。

## 入口检查(从 Gate A 段入口规则借用)

- 若 `step_3.pre_draft_review.decision_readiness = needs_supplement`,输出 warning 但不阻断
- 若 `step_3.pre_draft_review.verdict ∈ {revise-recommended, revise-required, stop-recommended}` 且 `risk_acknowledged ≠ true`,先要求用户明示授权语句(按 orchestration-philosophy.md § verdict 四档分支)
- 若 `step_3.post_disclosure_decision.choice ∈ {revise_disclosure, adjust_mainline, pause}`,禁止进入
