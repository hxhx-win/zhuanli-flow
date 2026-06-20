# 多 agent 审稿 Dispatch 契约

> 本文档由 `cn-patent-workflow-orchestrator` 编排器与 `cn-patent-attorney-review` 共同使用。编排器进入 step 6 multi 模式后按本契约派 6 + 1 个 subagent。

## 模式参数语义

`cn-patent-attorney-review` SKILL 调用时通过 prompt 传入 `mode` 参数：

| mode 值 | 用途 | 调用者 |
|---|---|---|
| `single` | 单 agent 审稿全流程 | 编排器派 1 个 subagent；或用户独立调用 |
| `direction-01` ~ `direction-06` | 多 agent 模式 6 个方向子审查 | 编排器主 agent 单条 message 并行派 6 个 subagent |
| `synthesize` | 多 agent 模式综合 6 份子审查 → 1 份总审稿 | 编排器派 1 个综合 subagent |
| `revision` | step 8 用户反馈修订 | 编排器派 1 个 revision subagent，见 [revision-mode.md](revision-mode.md) |

## 6 方向子 agent 职能与产物

| 方向编号 | mode 值 | 职能 | 必读 references | 输出产物（patent_root 相对路径） |
|---|---|---|---|---|
| 01 | direction-01 | 气质审查（独权肥度 / 抽象层 / 细节落点 / 节奏对照 / 密度匹配） | `references/review-checklists.md § 气质审查清单` + **按权 1 措辞判型选锚样稿**（方法类 → `references/CN113596424A_动态范围映射的方法和装置-结构化整理版.md` + `cn-patent-formal-drafting/references/method-claim-drafting.md`§独权骨架 + §从权梯队 + §红线 + §权要句式库 + §实施方式句式库；结构类 → `references/CN117336591A_摄像头模组和电子设备.md` + `cn-patent-formal-drafting/references/structural-claim-drafting.md`§独权骨架 + §从权梯队 + §红线 + §权要句式库 + §实施方式句式库） | `reviews/attorney-review/01-quality-aura.md` |
| 02 | direction-02 | 权利要求审查（独权必要性、从权层次、装置/整机配套保护对照） | `references/review-checklists.md § 权利要求审查清单` + **按权 1 措辞判型选起草侧骨架表**（方法类 → `cn-patent-formal-drafting/references/method-claim-drafting.md`，重点看 §A8 装置镜像 + §配套保护；结构类 → `cn-patent-formal-drafting/references/structural-claim-drafting.md`，重点看 §权要句式库 S6 整机配套） | `reviews/attorney-review/02-claims.md` |
| 03 | direction-03 | 说明书支撑审查 | `references/review-checklists.md § 说明书支撑审查清单` | `reviews/attorney-review/03-spec-support.md` |
| 04 | direction-04 | 形式与证据审查 | `references/review-checklists.md § 形式与证据审查清单` | `reviews/attorney-review/04-form-evidence.md` |
| 05 | direction-05 | 语言风格审查（B 风格 R1-R7） | `references/review-checklists.md § 语言风格审查清单` + `cn-patent-formal-drafting/references/language-style-guide.md` | `reviews/attorney-review/05-language-style.md` |
| 06 | direction-06 | 法条合规审查（审查员视角，22.2/22.3/22.4/26.3/26.4） | `references/review-checklists.md § 法条合规审查清单` + 编排模式下 `evidence/prior-art-search-report.md` | `reviews/attorney-review/06-legal-compliance.md` |

## 派单 prompt 硬规则（主 agent 必读）

主 agent 派 subagent 时写 prompt 必须遵守：

- **禁止**抄写、总结、改写、列举 references 中的硬规则内容（如 R1-R7 具体条款、各审查清单条目、判定标准）
- **允许**列：mode 名 / 方向职能名 / 输出产物路径 / 允许 Read 范围（路径）/ 禁止 Read 范围 / 返回格式
- 引用规则时只用「编号 + references 路径」，例 `按 language-style-guide.md R1-R7 逐条审查`，**不展开任何一条**

**根因**：主 agent 通常未读 references 原文，自编规则注解容易与原文漂移；subagent 收到 prompt 后会以 prompt 内已结构化的注解为依据判定，错误会被分发到所有方向，综合 subagent 不会重审。

## 子 agent 派单 prompt 模板（编排器使用）

```text
mode: direction-NN
正式稿路径: {正式稿绝对路径}
patent_root: {patent root 绝对路径}
输出产物绝对路径: {patent_root}/reviews/attorney-review/0N-{name}.md

任务: 内部调用 cn-patent-attorney-review SKILL,按 mode=direction-NN 仅执行本方向审查。
读取允许范围: 上表「必读 references」列出的文件 + 正式稿文件。
禁止读取: 其他 5 个方向的 references / 其他子审查产物。
落盘格式: 标准代理师审稿意见结构(高/中/形式/气质/语言风格分级),只写自己方向的发现。

返回主 agent 严格 ≤ 80 字,格式:
- verdict: {pass|revise-recommended|revise-required|stop-recommended}
- risk_count: {数字}
- file: reviews/attorney-review/0N-{name}.md

不得在回复中重复审查内容,审查全文已落盘。
```

### direction-01 气质审查 prompt 模板（专用）

```text
mode: direction-01
正式稿路径: {正式稿绝对路径}
patent_root: {patent root 绝对路径}
输出产物绝对路径: {patent_root}/reviews/attorney-review/01-quality-aura.md

判型(必做,在读样稿前):
  权 1 第一句以动词起(获取/根据/得到/确定/判断/获得...) → 方法类 → 锚样稿 = CN113596424A
  权 1 第一句以「一种 XX 装置/设备/模组/组件/系统」起,后接部件列表 → 结构类 → 锚样稿 = CN117336591A
  无法判定 → verdict=stop-recommended, risk_count=1, file 不生成, message 说明无法判型

任务: 内部调用 cn-patent-attorney-review SKILL,按 mode=direction-01 执行气质审查 5 子项(独权肥度 / 抽象层 / 细节落点 / 节奏对照 / 密度匹配)。

读取流程(严格 sequencing,不得跳步,不得并读):
  1. Read 待审正式稿,定位权 1 第一句
  2. 按上面判型规则确定类型(方法类 / 结构类),如无法判定立即按 stop-recommended 返回不再 Read
  3. Read 一份且仅一份锚样稿:
     - 方法类 → /root/.claude/skills/cn-patent-attorney-review/references/CN113596424A_动态范围映射的方法和装置-结构化整理版.md
     - 结构类 → /root/.claude/skills/cn-patent-attorney-review/references/CN117336591A_摄像头模组和电子设备.md
  4. Read 一份且仅一份起草侧骨架表(§独权骨架 + §从权梯队 + §红线 + §权要句式库 + §实施方式句式库):
     - 方法类 → /root/.claude/skills/cn-patent-formal-drafting/references/method-claim-drafting.md
     - 结构类 → /root/.claude/skills/cn-patent-formal-drafting/references/structural-claim-drafting.md
  5. Read references/review-checklists.md § 气质审查清单

硬规则:
  - 步骤 3 / 4 的两条路径互斥,**禁止两份都 Read**;若已 Read 不匹配判型的那份,视为派单违规,返回 verdict=stop-recommended + message 说明
  - 步骤 1-5 之外不得 Read 任何其他文件(包括其他 5 方向的 references / 其他子审查产物)
落盘格式: 每条意见严格遵循气质审查清单输出 schema: [气质-子项] 原文位置 + 问题类型 + 对照样稿位置 + 建议修改。对照样稿位置按判型用 CN113596424A 权 N 或 CN117336591A 权 N。

返回主 agent 严格 ≤ 80 字,格式:
- verdict: {pass|revise-recommended|revise-required|stop-recommended}
- risk_count: {数字}
- file: reviews/attorney-review/01-quality-aura.md

不得在回复中重复审查内容,审查全文已落盘。
```

## 综合 subagent 派单 prompt 模板

```text
mode: synthesize
6 份子审查文件绝对路径列表:
  - {patent_root}/reviews/attorney-review/01-quality-aura.md
  - {patent_root}/reviews/attorney-review/02-claims.md
  - {patent_root}/reviews/attorney-review/03-spec-support.md
  - {patent_root}/reviews/attorney-review/04-form-evidence.md
  - {patent_root}/reviews/attorney-review/05-language-style.md
  - {patent_root}/reviews/attorney-review/06-legal-compliance.md
输出产物绝对路径: {patent_root}/reviews/attorney-review.md

任务: 内部调用 cn-patent-attorney-review SKILL,按 mode=synthesize 读取 6 份子审查,
合并同根因问题,处理结论冲突,按 references/review-methodology.md 分级,
按 SKILL.md「修改意见结构」写出综合 attorney-review.md。

返回主 agent ≤ 200 字,格式:
- 综合 verdict
- 主要风险类目(≤ 5 条)
- 综合文件路径
```

## 并行 dispatch 实操

编排器主 agent 在**单条 message** 中并行派 6 个 Agent 工具调用：

```
- Agent 1: mode=direction-01 ...
- Agent 2: mode=direction-02 ...
- Agent 3: mode=direction-03 ...
- Agent 4: mode=direction-04 ...
- Agent 5: mode=direction-05 ...
- Agent 6: mode=direction-06 ...
```

6 个 subagent 同时启动，主 agent 等所有返回。然后再单独派 1 个综合 subagent。

写 state：
- `step_6.multi_agent_dispatch.dispatched_at = <ISO 时间>`
- `step_6.multi_agent_dispatch.subagent_count = 6`
- `step_6.multi_agent_dispatch.sub_review_paths = [6 个相对路径]`
- 综合完成后 `step_6.synthesis_subagent_dispatched_at = <ISO 时间>`

## 异常路径

- 某个方向子 agent 失败（返回内容不合规、未落盘文件）→ 主 agent 在派完综合 subagent 前**单独重派该方向**；不得静默跳过
- `get-next-step.py` 在 multi 模式下未齐 6 份子文件时返回 `missing_prior_deliverables` 阻断；编排器必须先补齐再推进 Gate B
- 综合 subagent 必须读到 6 份齐全的子文件，否则不得开始合并；缺哪份就先重派哪份
- **direction-06 schema 嗅探**：主 agent 在「等齐 6 份子审查」环节、派综合 subagent **之前**，对 `reviews/attorney-review/06-legal-compliance.md` 做字符串嗅探（`grep -cE "article[：:]"` 与 `grep -cE "defect_type[：:]"`，**正则须同时容忍半角 `:` 与全角 `：`**——子 agent 偶尔用全角冒号，用 `grep -c "article:"` 半角字面量会误判计数 0、触发无谓重派）；任一字段计数为 0 → 不让综合 subagent 接收破损输入，直接重派 direction-06；嗅探规则不向其他 5 方向适用（无 article/defect_type 字段约束）。
  - **direction-06 落盘要求**：机读字段 `article`/`defect_type` 后**统一用半角冒号 `:`**，避免下游按半角解析时漏读。

## 与编排器边界

- 编排器主 agent **不直接调** `cn-patent-attorney-review` SKILL；只通过 Agent 工具派 subagent
- subagent 内部读 SKILL.md 与 references（subagent 自带 Skill 工具），主 agent 上下文不加载子 SKILL 内容
- 主 agent 上下文增量：6 + 1 = 7 个 subagent 返回，合计 ≤ 7 × 200 ≈ 1.4 KB
