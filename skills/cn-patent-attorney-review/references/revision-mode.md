# revision Mode 契约

> step 8「用户反馈修订」由 `cn-patent-project-drafting` 编排器派 revision subagent 执行，subagent 内部调用本 SKILL 的 step 7「按用户反馈修订」流程。归属本 SKILL 而非 `cn-patent-formal-drafting`，理由：本 SKILL.md 步骤 7 本就承载修订职能（详见 SKILL.md 工作流表）。

## subagent 输入契约

编排器派 revision subagent 时按以下分级显式列路径。**默认输入仅 4 个核心**；7 份方向子审查与起草侧 references **不预加载**（subagent 上下文压力管理，见本文档「上下文压力预算」段）。

### 默认必读（4 个核心）

| 输入 | 用途 |
|---|---|
| 当前正式稿（最新版 markdown 绝对路径） | 修订基底 |
| 当前 evidence notes（最新版） | 修订基底 + 支撑矩阵更新 |
| `reviews/attorney-review.md`（综合审稿） | 修订总目标——已含跨方向同根因合并 + 冲突取整 |
| `reviews/user-feedback.md` | 用户决策（哪些 review 项接受 / 否定 / 推迟）；结构契约见 `../cn-patent-project-drafting/assets/user-feedback-decision.template.md`；高 / 中优先级两节内**允许**用 `by_article: { "22.3": [...], "26.3": [...] }` 索引承载法条维度的逐条决策 |

### 按需 Read（不预加载）

- `reviews/attorney-review/01-06-*.md`（6 份方向子审查，multi 模式产物）：**仅在 changelog 需标注「来源方向」或需追溯某条具体改动的方向细节时**，按 changelog 反向追溯链接读单份。综合稿已含合并去重信息，**禁止全部预加载**。
- `state/patent-iteration-state.json`：仅当需要 patent_root 路径解析、版本号推断、drafting_decisions 查询时按需 Read。
- 起草侧 references：见下方 trigger 表。

## 气质审查段处理逻辑

revision subagent 收到气质审查 5 子项意见（来自 `reviews/attorney-review.md` 「气质审查发现」段 或 `reviews/attorney-review/01-quality-aura.md`）后，按以下规则落地——每个子项对应一种特定的修订动作，**不能机械改写表层字句**：

| 子项 | 修订动作 |
|---|---|
| 独权肥度问题 | 修改独权：删除越界特征（参数公式 / 阈值 / 字段名 / 步骤号 / 装置单元名 / 多分支条件展开）+ 下放到对应从权 / 实施例。删除项必须找到落点；下放位置参考 method-claim-drafting.md §从权梯队（A4/A5/A6/A7 句式） |
| 抽象层问题 | 把代码符号（函数名 / 变量名 / 类名 / 字段名 / 枚举常量名）改为语义概念；首次出现允许保留括号辅助（如「优先级队列（priority_queue）」），后续仅使用语义术语 |
| 细节落点问题 | 调整特征所在层级：独权 ↔ 从权 ↔ 实施例 ↔ 分案；落点取决于审查意见中「对照样稿位置」与从权梯队句式归属（方法类 A 类 / 结构类 S 类）|
| 节奏对照问题 | 调整独权 / 从权层级数到对应类型实证基线：方法类（CN113596424A：独权 5 动作 / 从权 11 条覆盖 A4×1 + A5×4 + A6×2 + A7×3）；结构类（CN117336591A：独权 2-4 部件块 / 从权 13 条覆盖 S1×1 + S2×1 + S3×3 + S4×2 + S5×6 + S6×1）；缺失句式按对应骨架表补齐 |
| 密度匹配问题 | 调整实施方式密度：删除伪代码 / 流程图节点引用 / 详细类设计 / API 签名；按 B2/B3/B4/B5 五类句式补齐参数取值 / 计算示例 / 可选实施方式 / 效果回扣；段落组织改用自然段，禁止 S1/S2 步骤号或 1.2.3. 编号列表 |

每条气质改动必须在 changelog 中标注子项归属（独权肥度 / 抽象层 / 细节落点 / 节奏对照 / 密度匹配），并指明原文位置 + 落点位置 + 对照样稿引用。

## subagent 输出契约

| 输出 | 路径 |
|---|---|
| 新版正式稿（递增 v 编号，例如 v3 → v4） | `drafts/markdown/{slug}-formal-v{N}.md` |
| 修订 changelog | `reviews/revision-r{N}-changelog.md` |
| 新版 evidence notes（若需要） | `drafts/markdown/{slug}-formal-v{N}-evidence-notes.md` |

## subagent 返回主 agent 摘要（≤ 200 字）

```text
version: v{N}
key_changes:
  - {改动类目 1}: {影响范围简述}
  - {改动类目 2}: {影响范围简述}
  ...
verify_summary: pass | partial-fail
changelog: reviews/revision-r{N}-changelog.md
new_draft: drafts/markdown/{slug}-formal-v{N}.md
```

不得在回复中复述具体修订内容，详细 diff 与 changelog 都已落盘。

## changelog.md 标准结构

```markdown
# Revision r{N} Changelog — {patent-slug}

- 修订时间: {ISO 8601}
- 基底版本: v{N-1}
- 目标版本: v{N}
- 修订来源:
  - reviews/attorney-review.md 第 X 节: ...
  - reviews/user-feedback.md 决议: ...

## 改动类目

### 1. 权利要求改动
- {改动项} ← 由 attorney-review 第 X 条触发,用户决议: ...

### 2. 说明书改动
- ...

### 3. 摘要 / 附图 / 形式 改动
- ...

### 4. 法条合规改动（若 user-feedback.md 含 by_article 决策）

- {改动项} ← 由 attorney-review 07-legal-compliance.md 第 X 条触发,article: 22.3,defect_type: 逻辑,用户决议: ...

## 自检结果（在 subagent 内部跑完后填）

- 字数变化: v{N-1} {字数} → v{N} {字数}
- 权要数: {数字}
- B 风格 R1-R7: pass / 命中 X 处
- 必要性筛查: pass / 命中 X 项下放

## 推迟项

- {延迟到下一轮的项,引用对应 review 索引}
```

## by_article 决策处理（C 类扩展）

revision subagent 收到 user-feedback.md 时按以下规则处理 `by_article`：

- 若高/中优先级两节存在 `by_article: { "22.3": [...] }` 索引，subagent **必须**为每条法条决策项在 changelog `### 4. 法条合规改动` 小节列出 article / defect_type / 用户决议
- 若 user-feedback.md 未用 `by_article` 索引（用户偏好按既有维度分类），subagent 按既有路径处理，**不强制**生成「### 4. 法条合规改动」小节
- 法条合规改动若与既有 1/2/3 类目重叠（例 26.4 ⇄ 权要措辞修改），主类目归属由 user-feedback.md 显式指定；缺指定时 subagent 默认归 4 类目（法条合规）并在条目末尾标注「同涉权要」

## 起草侧 references trigger 表

revision subagent **按修订内容触发条件** Read（不切换 SKILL、不预加载、不全读）。落到 changelog 时若某条改动未触发任何 trigger，**不应**读取对应 reference：

| 修订涉及内容（trigger） | Read 文件 |
|---|---|
| 气质审查改动（独权肥度 / 抽象层 / 细节落点 / 节奏对照 / 密度匹配） | 按权 1 判型选其一：方法类 → `cn-patent-attorney-review/references/CN113596424A_动态范围映射的方法和装置-结构化整理版.md` + `cn-patent-formal-drafting/references/method-claim-drafting.md`（§独权骨架 + §从权梯队 + §红线 + §权要句式库 + §实施方式句式库）；结构类 → `cn-patent-attorney-review/references/CN117336591A_摄像头模组和电子设备.md` + `cn-patent-formal-drafting/references/structural-claim-drafting.md`（§独权骨架 + §从权梯队 + §红线 + §权要句式库 + §实施方式句式库）|
| 独权必要性筛查 / 方法权拆分 / 子步骤层级 | `cn-patent-formal-drafting/references/method-claim-drafting.md` |
| 装置 / 结构权撰写 / 装置-方法镜像 | `cn-patent-formal-drafting/references/structural-claim-drafting.md`（结构类装置 / 系统 / 电子设备 / 介质均汇入此文件）+ `method-claim-drafting.md`（方法类配套装置按 A8 装置镜像段处理） |
| 判型分类 / 电子设备权 / 介质权 / 应用场景权引用范围 | `cn-patent-formal-drafting/references/claim-type-classification.md` |
| B 风格 R1-R7（句长、目的性短语、缩写双注、术语统一、八股段落） | `cn-patent-formal-drafting/references/language-style-guide.md` |
| 公式编号 / 公式块格式 / 符号定义 | `cn-patent-formal-drafting/references/formula-and-math.md` |
| 附图引用 / 附图与说明书对应 | `cn-patent-formal-drafting/references/figure-handoff.md` |
| 通用起草段落体例 | `cn-patent-formal-drafting/references/drafting-rules.md` |

## 派单前的 R 规则注解一致性预审（编排器主 agent 责任）

为避免「派单 prompt 中 R 规则注解 ≠ language-style-guide.md 原文」类 prompt 误注事件（pts-bresenham r5 复盘：方向 06 派单 prompt 误把「本发明 → 本申请」写为 R3 硬规则，与 R3 真硬规则「禁目的性短语」不符），编排器主 agent 派 revision subagent 前必须：

- 若 user-feedback.md 或综合 attorney-review.md 中包含 R1-R7 类决策 / 改动，主 agent 对照 `cn-patent-formal-drafting/references/language-style-guide.md` 原文核验每条 R 规则注解
- 发现 mismatch 时，在 user-feedback.md 中显式追加「prompt 误注澄清」段，列明 review 注解 vs reference 原文的差异 + 处置（拒绝 / 部分接受 / 全接受），revision subagent 据此跳过或调整该项
- revision subagent **禁止仅依据 review 派单注解机械执行 R 规则修订**，所有 R 类改动必须以 language-style-guide.md 原文为最终权威

## 上下文压力预算

revision subagent 上下文增量预算（按 1 KB 文本 ≈ 250 token 估算，新契约 vs 旧契约对比）：

| 内容 | 新契约（默认 + 按需） | 旧契约（全预加载） |
|---|---|---|
| SKILL.md + revision-mode.md | ≈ 3K | ≈ 3K |
| v{N-1} 正式稿 | ≈ 12K | ≈ 12K |
| v{N-1} evidence notes | ≈ 8K | ≈ 8K |
| 综合 attorney-review.md | ≈ 8K | ≈ 8K |
| user-feedback.md | ≈ 2K | ≈ 2K |
| 6 份方向子审查 | 0 - 5K（按需读 0-2 份） | 24K（全读） |
| 起草侧 references | 3 - 8K（trigger 表命中 1-3 份） | 30-50K（全读） |
| 输出（新版正式稿 + evidence + changelog） | ≈ 25K | ≈ 25K |
| **合计** | **≈ 60-70K** | **≈ 110-130K** |

实测案例（pts-bresenham r5，旧契约）：subagent total_tokens = 216K，1M 窗口占 22%；若改用 200K 标准窗口将溢出。新契约预计节省 30-60K token / 单次修订，使 revision 在 200K 标准窗口下也能稳定运行。

## 与编排器边界

- 编排器主 agent 不读 7 份子审查文件，全部由 revision subagent 内部读
- 修订完成后 subagent 写 state：
  - `step_8.revision_subagent_dispatched = true`
  - `step_8.revision_subagent_dispatched_at = <ISO 时间>`
  - `step_8.revision_changelog_path = "reviews/revision-r{N}-changelog.md"`
  - `current_draft_path = "drafts/markdown/{slug}-formal-v{N}.md"`
- 主 agent 上下文增量 ≤ 200 字 + state 字段读写
