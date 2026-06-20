---
name: cn-patent-disclosure-review
description: 当用户已有技术版交底书初稿（通常由 `cn-patent-disclosure-draft` 产出），需要引导发明人在终稿决策前逐阶段审核并反馈实质性偏差（组件遗漏、因果链不成立、解决思路工程不可行等）时使用。仅做发明人审核与反馈收集，不重做评审、不改写交底书；累积反馈触发整体修订时由编排器派回 `cn-patent-disclosure-draft` 重写。触发词：发明人审核、交底书审核、inventor review、disclosure review、step-3.inventor-review。
---

# 发明人交底初稿审核 skill

主跑型 skill，在 `step-3.inventor-review` 阶段由 `cn-patent-workflow-orchestrator` 编排器加载，引导用户对交底初稿做 3 阶段审核。

## 入口前置

- `state.current_stage == "step-3.inventor-review"`
- `patent/<patent-slug>/disclosure/disclosure-draft.md` 已落盘
- `state.step_3.disclosure_draft.status == "completed"`

由 `scripts/validate-stage.py --stage step-3.inventor-review --mode enter` 自动校验。

## 行为前置

- 编排器禁止把 3 段 AskUserQuestion 合并成综合题；每段按 `references/protocols.md` 独立调用，提示词与写入字段不可省略
- 加载后第一动作：把当前 ISO 时间写入 `state.step_3.inventor_review.skill_loaded_at`（exit 校验依赖该字段）

## 3 阶段审核流程

| 阶段 | 看交底书章节 | AskUserQuestion 三档 |
|---|---|---|
| Stage 1 组件拆解核对 | §4.1 + §4.2-§4.X | 无遗漏 / 需补充修正 / 整段重写 |
| Stage 2 因果链与创新点合理性 | §3 + §4.X 五栏表 + §5 | 合理成立 / 部分调整 / 关键站不住 |
| Stage 3 解决思路可行性 | §4 + §6.1 + §6.2 | 全可行 / 部分不可行 / 主方案不可行 |

详细提示词、选项文案、状态字段写入见 [references/protocols.md](references/protocols.md)。

## 反馈处理

- Stage 任一档不是「通过」 → 反馈累积进 `state.step_3.inventor_review.stage_X_feedback`，3 阶段全跑完再一次性整体修订
- 修订时调 `cn-patent-disclosure-draft` 重生成 disclosure-draft.md，复用其起草纪律
- 硬限 3 轮 → 触发 escalation 三档（见 protocols.md）

**REQUIRED SUB-SKILL：** 修订调用 `cn-patent-disclosure-draft` 时复用其 `references/drafting-discipline.md` 作准绳。
**REQUIRED CONTEXT：** 状态字段约定见 `cn-patent-workflow-orchestrator/references/state-machine-reference.md`。

## 出口分支

写入 `state.step_3.inventor_review.exit_status` + `gate_passed`，由编排器读取后路由：

| exit_status | gate_passed | 编排器路由 |
|---|---|---|
| `approved` | true | `step-3.post-disclosure-decision` |
| `accepted_with_dissent` | true | `step-3.post-disclosure-decision`（未解决项由 handoff S1 读 `stage_X_feedback` 展示）|
| `rolled_back_step_1` | false | `current_stage = step-1`，reset step_2/step_3 下游字段 |
| `rolled_back_step_2` | false | `current_stage = step-2`，reset step_3 下游字段 |

## 跨平台 fallback

主跑型 skill，不派 subagent，所有交互通过主 agent 的 AskUserQuestion 完成；Claude Code / Cursor / Codex 行为一致。
