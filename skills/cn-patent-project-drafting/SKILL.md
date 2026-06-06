---
name: cn-patent-project-drafting
description: 当用户明确要求生成/起草/写/出中文发明专利、进入完整专利流程，或希望基于既有 `patent/<patent-slug>/state/patent-iteration-state.json` 继续未完成迭代时使用。也可在 `cn-patent-repo-scout` 已确认方向和核心资料后由用户选择进入。本 skill 是编排器，调度主线分析、现有技术检索、起草前评审、技术交底、发明人审核、正式稿起草、代理师审稿、DOCX 导出全流程；不直接挑方向（用 `cn-patent-repo-scout`），也不替代单步执行（已有方向只想跑某一步时用对应单 skill：`cn-patent-mainline-analysis` / `cn-patent-prior-art-search` / `cn-patent-formal-drafting` / `cn-patent-attorney-review` / `cn-patent-docx-export`）。触发词：完整专利流程、起草中文发明专利、`patent-iteration-state.json`、编排器、project drafting。
---

# 中文发明专利通用起草（编排器）

编排完整专利起草流程。本 skill 是路由器，具体规则见下方 reference + scripts。

## 入口边界

- 不扫描项目；无明确方向先用 `cn-patent-repo-scout`
- 只做保护路径设计或特征分层用 `cn-patent-mainline-analysis`
- 已选主线只起草正式稿用 `cn-patent-formal-drafting`

## 阶段总图

```mermaid
flowchart LR
    s0[step 0 环境/状态] --> s1[step 1 主线] --> s2[step 2 检索]
    s2 --> s3r[step 3 评审] --> s3d[step 3 交底书] --> s3i[step 3 发明人审核] --> s3p[step 3 分流]
    s3i -.rollback.-> s1
    s3i -.rollback.-> s2
    s3p -.handoff.-> hp[专利部接手] --> ga[Gate A 段]
    s3p -.local.-> ga
    ga --> s4[step 4 正式稿] --> s5[step 5 风险] --> s6[step 6 审稿]
    s6 --> gb[Gate B] --> s8[step 8 修订] --> gc[Gate C] --> done[完成]
```

## 阶段执行者

| 阶段 | 执行者 | 派 subagent |
|---|---|---|
| 1/2/3 评审/3 交底/4/6 | 对应子 skill | 是 (N0 纪律) |
| 3 发明人审核 | `cn-patent-disclosure-review` | 否（主跑型） |
| 0/Gate A/handoff/分流/5/7/8/9 | 主编排器 | 否 |

详见 [references/agent-tool-mapping.md](references/agent-tool-mapping.md)。

## 必读 reference (3 份)

- [references/orchestration-philosophy.md](references/orchestration-philosophy.md)：协作哲学（为什么）
- [references/state-machine-reference.md](references/state-machine-reference.md)：状态机入口（怎么查）
- [references/agent-tool-mapping.md](references/agent-tool-mapping.md)：N0 派单契约

## 脚本入口

- `scripts/validate-stage.py --state-path X --stage S --mode enter|exit`：断言前置/出口
- `scripts/get-next-step.py --state-path X`：计算下一步
- `scripts/handoff-package.py` / `handoff-pickup.py`：交接

## 脚本调用纪律（硬约束）

- 进入新 stage 前 → 跑 `validate-stage.py --mode enter`，result=blocked 则**必须**停下 AskUserQuestion
- subagent 返回 / stage 完成后 → 跑 `validate-stage.py --mode exit`，result=blocked 则**必须**补派或追问
- **`validate-stage --mode exit` result=ok 后**：编排器必须主动把 `state.current_stage` 写到下一 stage 名（如 `step-1` / `step-2` / `step-3.pre-draft-review` …）。`get-next-step.py` 内部取 `min(declared, derived)` 防越界，**不前移 `current_stage` 会让路由永远卡在当前 stage**。
- 写完 `current_stage` 后再跑 `get-next-step.py` 拿"下一步"
- **不得凭用户原始请求范围（如"只生成交底书"）提前结束循环**：状态机推进由 `get-next-step.py` 的 `next_action` 决定，返回 `"completed"` 才算终止
- **按 `next_step.executor_info` 决定下一步动作**：`type=main_run_skill` 必须先 Read `must_load` 列表里的文件再继续；`do_not_merge_user_questions=true` 时禁止合并多档 AskUserQuestion
- **step 0 出口附加**：把 `env-check.json` 的 `warnings` 数组逐条在对话中 echo 给用户（字体缺失、缺工具等），避免下游 docx 阶段才暴露
- 两脚本**串行调用，不嵌套**

## Gate

- Gate A：起草前决策完成 + 用户确认进起草
- Gate B：审稿意见 + 用户反馈双方就位
- Gate C：质量检查通过 + 用户授权交付

## 状态与脚本

- 状态文件：`patent/<patent-slug>/state/patent-iteration-state.json`
- 模板：[assets/patent-iteration-state.template.json](assets/patent-iteration-state.template.json)
- 历史兼容（旧 state 缺新字段）：`scripts/new-iteration-state.py --migrate-from <old.json>`

## 子 skill 引用

- 前置可选：`cn-patent-repo-scout`
- 必要前置：`cn-patent-mainline-analysis` / `cn-patent-prior-art-search` / `cn-patent-disclosure-draft` / `cn-patent-disclosure-review` / `cn-patent-formal-drafting` / `cn-patent-attorney-review`
- 关联可选：`cn-patent-docx-export`（Gate C 通过后导出）
