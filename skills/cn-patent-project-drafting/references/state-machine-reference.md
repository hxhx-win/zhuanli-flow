# 状态机参考（怎么查）

> Windows 原生环境：命令中的 `python3` 请用 `python` 或 `py` 代替。

状态机已下沉到 `scripts/lib/` + `scripts/validate-stage.py` + `scripts/get-next-step.py`。本文档**不维护字段表**，只指引怎么查。

## 调用速查

| 我想做的 | 调什么 |
|---|---|
| 看现在该做什么 | `python3 scripts/get-next-step.py --state-path patent/<slug>/state/patent-iteration-state.json` |
| 看 stage X 前置/出口条件是否满足 | `python3 scripts/validate-stage.py --state-path X --stage S --mode enter\|exit` |
| 拿 Gate A 通过条件清单 | `validate-stage --stage gate-a.confirmation --mode exit` |
| 拿 Gate B 通过条件清单 | `validate-stage --stage gate-b --mode exit` |
| 拿 Gate C 通过条件清单 | `validate-stage --stage gate-c --mode exit` |
| 看 handoff 当前位置 | 读 `state.handoff.status` + （若 picked_up）调 `lib.handoff.picked_up_substage(state)` |
| 旧 state 升级到新字段 | `python3 scripts/new-iteration-state.py --migrate-from <old.json> --output-path <new.json> --project-root .` |

## 15 类 A 实质阶段 + 9 类 B 等待状态

`scripts/lib/preconditions.py` 内 `STAGE_PRECONDITIONS_A`（15 项，含 `step-3.inventor-review`）+ `STAGE_AWAITING_CHECKS_B`（9 项）= 24 stage 全覆盖。新增 stage 或字段断言时改这两份 dict，prose 不重复。

## handoff 状态机示意

```
not_initiated ─→ packaged ─→ picked_up ──┐
     │                                    ├→ Gate A 段（drafting_initiator=patent_dept | rd）
     └─→ local ───────────────────────────┘
```

详细 substage（S1 风险 / S2 决策 / S3 notes / S4 Gate A）由 `lib/handoff.py` `picked_up_substage(state)` 决定。

## 真产物路径（仅可信清单）

5 处伪产物（`gates/gate-{a,b,c}-confirmation-package.md` / `gates/step-5-pre-review-risk-package.md` / `reviews/review-mode-selection.md`）已全部废除，相关 Gate 拍板状态改由 state 子树记录。**真产物**清单见 `lib/paths.py` 的 `DELIVERABLES_BY_STEP`：

| step | 真产物 |
|---|---|
| 1 | `analysis/mainline-analysis.md` + `evidence/evidence-matrix.md` |
| 2 | `evidence/prior-art-search-report.md` |
| 3 | `reviews/pre-draft-review.md` + `disclosure/disclosure-draft.md` |
| 4 | 由 `state.current_draft_path` / `state.figure_manifest_path` 字段维护 |
| 6 | `reviews/attorney-review.md`（+ multi 模式下 7 份方向子审查） |
| 8 | `reviews/user-feedback.md` |
| 9 | `quality/`（质量检查报告目录） |

handoff packaged 时 `handoff/handoff-package.md` 真产物；picked_up 时可选 `reviews/patent-dept-notes.md`。

`step-3.inventor-review` 走 `accept_with_dissent` 时**不再生成单独的产物文件**。未解决项保留在 `state.step_3.inventor_review.stage_X_feedback` 字段（1/2/3）。下游消费路径：

- **handoff 分支**：`handoff.status == picked_up` 后进入 S1 风险确认（`ask_risk_review`），编排器须读 `state.step_3.inventor_review.stage_X_feedback` 中非 null 的项，并入「上游风险清单」展示给专利部，AskUserQuestion 三选给专利部决定是否「风险不可接受回 step 3」
- **local 分支**：发明人/研发自己选择 accept_with_dissent 后继续本地起草，已知情自负，不再额外确认

### 编排器须知：`step-3.awaiting_gate_a_passed` 的双义

当 `get-next-step.py` 返回 `next_action: step-3.awaiting_gate_a_passed` 时，编排器**必须**先读 `state.step_3.inventor_review.exit_status` 字段判分支：

- `exit_status == "approved"` 或 `"accepted_with_dissent"` → 正向推进，等 `gate_a.status` 写入 passed
- `exit_status == "rolled_back_step_1"` → 执行 reset：清 `state.step_2.*` / `state.step_3.pre_draft_review.*` / `state.step_3.disclosure_draft.*` / `state.step_3.post_disclosure_decision.*`，`current_stage = "step-1"`
- `exit_status == "rolled_back_step_2"` → 执行 reset：清 `state.step_3.pre_draft_review.*` / `state.step_3.disclosure_draft.*` / `state.step_3.post_disclosure_decision.*`，`current_stage = "step-2"`（inventor_review 历史保留供回溯）

完整流程见 `cn-patent-disclosure-review/references/protocols.md` 「rollback 处理」段。

## 审稿/修订迭代状态流

每轮审稿反馈后，写入 state 的字段：

- `review_feedback.status` / `latest_review_notes_path` / `latest_user_feedback_path` / `latest_revised_draft_path`
- `review_feedback.revision_review_status` / `unresolved_items` / `rollback_reason`（按需）
- `history.attorney_review_rounds`（每轮追加）

推荐 `current_stage` 流转：

```
attorney-review → gate-b-pending → feedback-revision → feedback-revision-review → ready-for-gate-c
                                                     │
                                                     └─（用户否决）→ attorney-review（新一轮）
```

字段断言的真相源是 `lib/preconditions.py`（`step-6` / `gate-b` / `step-8` / `gate-c` 的 enter/exit 条件）。prose 不重复维护。

## 何时该读 prose 而非调脚本

仅在以下情况：
- 开发新 stage（此时改 `lib/preconditions.py`）
- 调试 schema（此时改 `assets/patent-iteration-state.template.json`）
- 改字段映射或新增伪产物废除（同步改 `new-iteration-state.py` setdefault + `--migrate-from` 逻辑）

日常运行时编排器不应 Read 本文，直接调脚本即可。
