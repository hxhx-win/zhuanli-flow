# 发明人交底初稿审核协议

本文件被 `cn-patent-disclosure-review/SKILL.md` 引用。包含 3 阶段提示词全文、AskUserQuestion 选项文案、状态字段写入规则、修订循环、escalation 菜单。

## 总览流程

```
Stage 1 组件拆解核对
  ↓
Stage 2 因果链与创新点合理性
  ↓
Stage 3 解决思路可行性
  ↓
3 阶段全 approved?
  是 → 写 exit_status=approved, gate_passed=true → step-3.post-disclosure-decision
  否 → 累积反馈 → 整体修订 → round_count+=1 → 从 Stage 1 重审
        round_count == 3 仍未通过 → escalation 三档
```

## Stage 1：组件拆解核对

**Agent 行为**：

1. 提示用户翻阅 disclosure-draft.md 的 §4.1（总体架构）+ §4.2-§4.X（各模块章节）
2. 提示文案：「请核对：① 模块清单是否有遗漏；② 模块间关系（并发、汇合、回滚等）推断是否准确。如发现偏差，请在「其他」处具体说明。」
3. 调 AskUserQuestion

**AskUserQuestion**：

| 中文选项 | 内部值 | 写入字段 |
|---|---|---|
| 无遗漏，关系准确 | `approved` | `stage_1_status = "approved"` |
| 需要补充或修正 | `partial` | `stage_1_status = "partial"`，`stage_1_feedback = <用户填写>` |
| 整段需重写 | `rejected` | `stage_1_status = "rejected"`，`stage_1_feedback = <用户填写>` |

## Stage 2：因果链与创新点合理性

**Agent 行为**：

1. 提示用户翻阅 disclosure-draft.md 的 §3（技术问题）+ §4.X 五栏因果链对照表 + §5（有益效果）
2. 提示文案：「请凭实际经验判断：① 关键创新点是否合理（专利性 / 工程必要性）；② 因果链 §4.X 五栏表是否成立。」
3. 调 AskUserQuestion

**AskUserQuestion**：

| 中文选项 | 内部值 | 写入字段 |
|---|---|---|
| 创新点合理、因果链成立 | `approved` | `stage_2_status = "approved"` |
| 部分需要调整 | `partial` | `stage_2_status = "partial"`，`stage_2_feedback = <用户填写>` |
| 关键创新点站不住，需重写 | `rejected` | `stage_2_status = "rejected"`，`stage_2_feedback = <用户填写>` |

## Stage 3：解决思路可行性

**Agent 行为**：

1. 提示用户翻阅 disclosure-draft.md 的 §4（主技术方案）+ §6.1（替代方案）+ §6.2（分案候选）
2. 提示文案：「请评估各解决思路的工程 / 商业可行性。若部分不可行，请在「其他」**必写「哪条不可行 + 原因」**，供 agent 调整。」
3. 调 AskUserQuestion

**AskUserQuestion**：

| 中文选项 | 内部值 | 写入字段 |
|---|---|---|
| 所有思路均可行 | `approved` | `stage_3_status = "approved"` |
| 部分思路不可行（**必填哪条 + 原因**） | `partial` | `stage_3_status = "partial"`，`stage_3_feedback = <用户填写>` |
| 主方案思路不可行，需重写 | `rejected` | `stage_3_status = "rejected"`，`stage_3_feedback = <用户填写>` |

**强校验**：当用户选 `partial` 但未在「其他」写明「哪条 + 原因」时，agent **必须坚持要求补填**，不得用占位文本（如「待补充」）写入 state。

## 轮次推进

3 阶段全跑完后：

- **全 approved** → 写 `exit_status="approved"`、`gate_passed=true`，结束 skill，回到编排器
- **任一 partial / rejected** → `round_count += 1`，触发整体修订（见下文）

## 整体修订调用

**REQUIRED SUB-SKILL：** `cn-patent-disclosure-draft`

1. 把 3 阶段累积的 `stage_X_feedback` 合并成修订提示
2. 调 `cn-patent-disclosure-draft` 的 `disclosure-generation` 子阶段（派 subagent），prompt 中明确：
   - `stage: disclosure-generation`
   - `revision_mode: true`
   - `prior_draft_path: <旧 disclosure-draft.md 绝对路径>`
   - `inventor_feedback: <合并后的反馈文本>`
   - 输入 / 输出绝对路径仍按 `cn-patent-disclosure-draft` 的契约填写
3. subagent 复用 `cn-patent-disclosure-draft/references/drafting-discipline.md` 作修订准绳
4. 修订完成后：重置 `stage_1_status` / `stage_2_status` / `stage_3_status` 为 `null`（`stage_X_feedback` 保留供历史参考），然后从 Stage 1 重审

## 硬限 3 轮 + Escalation

当 `round_count == 3` 且 3 阶段仍有非 approved 时，触发 escalation 三档（**禁止启动第 4 轮自动修订**）。

**AskUserQuestion**（中文）：

| 中文选项 | exit_status | gate_passed | 后续动作 |
|---|---|---|---|
| 带异议接收，进入后续流程 | `accepted_with_dissent` | `true` | 未解决项保留在 `stage_X_feedback` 字段；handoff 分支由编排器在 S1 风险确认时读取并入风险清单展示；local 分支发明人自起草已知情自负，编排器仅记录 `exit_status` |
| 回滚到 step-1 重做主线分析 | `rolled_back_step_1` | `false` | reset `step_2.*` / `step_3.*` 下游字段；`current_stage = "step-1"` |
| 回滚到 step-2 重做检索 | `rolled_back_step_2` | `false` | reset `step_3.*` 下游字段（保留 inventor_review 记录）；`current_stage = "step-2"` |

### rollback 处理（`rolled_back_step_1` / `rolled_back_step_2`）

主跑 skill 写完 `exit_status` 后退出；由编排器 `cn-patent-domain-runtime` 读 `exit_status` 字段执行 reset：

- `rolled_back_step_1`：清空 `state.step_2.*` / `state.step_3.pre_draft_review.*` / `state.step_3.disclosure_draft.*` / `state.step_3.post_disclosure_decision.*`；保留 `state.step_3.inventor_review` 历史记录供回溯
- `rolled_back_step_2`：清空 `state.step_3.pre_draft_review.*` / `state.step_3.disclosure_draft.*` / `state.step_3.post_disclosure_decision.*`；保留 inventor_review 历史

具体 reset 字段清单由编排器侧实现（不在本 skill 范围内）。

## 反例 / 红线

- ❌ 在用户「其他」未填写时用「待补充」占位 → 必须 AskUserQuestion 追问
- ❌ `round_count >= 3` 仍自动触发修订 → 必须进 escalation 菜单
- ❌ rollback 时不写 `exit_status` → 编排器无法判路由
- ❌ 修订后不重置各 stage_X_status 字段 → 旧轮次结果污染新轮
