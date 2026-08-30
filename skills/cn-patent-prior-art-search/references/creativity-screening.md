## 推荐工作方式

1. 先确认 `mainline-analysis.md` 中的已确认技术方向和 1 条或多条保护路径候选。
2. 针对每条保护路径候选分别设计检索式。
3. 至少记录 3 件专利候选和 3 篇研究候选。
4. 选出最接近现有技术。
5. 对主线分析阶段的候选发明点逐项标注：`可主张`、`仅从属`、`仅实施例`、`分案保留`、`已被公开/暂不写入`。
6. 提取检索后真正可主张发明点、区别特征与技术效果。
7. 只把最能承载可主张发明点的一条保护路径推进到 Gate A 等待用户确认。

`mainline-analysis.md` 只提供保护路径候选、候选发明点用途表、检索输入摘要和待检索确认问题，不提供推荐结论。检索结束后才能形成 `claimable_invention_points` 和 `prior_art_search.recommended_mainline`；后者为兼容既有脚本保留，语义是检索后推荐保护路径。用户在 Gate A 明确确认后，才写入 `selected_mainline`。

## 输出要求

检索结束后，至少要产出以下内容：

- 检索式
- 专利候选表
- 研究候选表
- 最接近现有技术
- 检索后可主张发明点
- 区别特征与技术效果
- 保护路径候选创造性筛选表
- 推荐保护路径
- 需要用户确认的分叉点

唯一落盘文件：`patent/<patent-slug>/evidence/prior-art-search-report.md`（各逻辑产出对应章节见 `SKILL.md` 输出物表）。

模板：`cn-patent-domain-runtime/assets/prior-art-search-report.template.md`

编排模式初始化：N8 在首次落盘前直接以 `cn-patent-domain-runtime/assets/prior-art-search-report.template.md` 为模板 Write 到 `patent/<patent-slug>/evidence/prior-art-search-report.md`，无需独立初始化脚本。

## 主线筛选判断口径

优先选择满足以下条件的保护路径：

- 与最接近现有技术相比，区别特征更集中，不是零散拼接
- 技术效果能由当前项目证据支撑，而不是只靠推断
- 独立权利要求能保持抽象，但又不脱离已有实现
- 就算面对一篇很接近的参考文献，仍能说清楚"为什么不是简单替换"

不宜优先选择的保护路径：

- 仅在参数、阈值或打分方式上有微调
- 只体现应用场景变化，没有稳定技术手段差异
- 需要多个证据不足的点拼接后才显得新
- 当前仓库没有足够证据支撑其技术效果

若检索后推荐保护路径不能覆盖最强可主张发明点，必须在报告中说明原因。对未推荐保护路径，应标注降级用途：从属权利要求、实施例、替代实施方式、分案保留或放弃。

## 与状态文件的关系

检索后，优先把以下字段回写到状态文件：

- `closest_prior_art`
- `claimable_invention_points`
- `distinguishing_features`
- `prior_art_search.report_path`
- `prior_art_search.queries`
- `prior_art_search.closest_items`
- `prior_art_search.recommended_mainline`

不得在检索阶段写入 `selected_mainline`；该字段只能在 Gate A 用户确认题目、主线和保护客体后写入。

## DF 抽取标签规则

每项区别特征（DF）必须标注 `type` 字段：

| type | 含义 | 创造性贡献度 |
|---|---|---|
| `structural` | 结构性差异（新增/替换/重新组合关键结构、步骤、模块、数据流） | 高 |
| `parameter` | 参数差异（取值范围、阈值、比例、单位换算等数值层差异） | 中 |
| `engineering` | 工程实现差异（已知技术的不同实现路径、不同 API、不同库选择） | 低 |

下游 cn-patent-disclosure-draft 的 3a 创新性维度评估按 `type` 计权：

- 走档：DF 数量 ≥ 2 且 ≥ 1 项 `type=structural`
- 修档：DF 数量 = 1 或仅 `type=parameter`
- 停档：DF 全部已被检索命中或仅 `type=engineering`

## 风险列统一表头（供下游抽取迁移）

保护路径创造性筛选表必须含 `风险` 列，单行描述，便于下游 cn-patent-disclosure-draft 评审子 agent 抽取迁移到 pre-draft-review.md 的 `risk_inputs` 章节（含"起草侧处理建议"列）；无风险写"无"。

## DF 反例自检规则（必填）

prior-art 子 agent 在写完 prior-art-search-report.md 后，必须**同一次任务内**对每条 DF 做反例自检，并产出 `df-rationale-signals.yml`。

### 反例自检模板

每条 DF 必填四字段：

| 字段 | 说明 |
|---|---|
| counter_example_question | 固定问句"面对这个技术问题，一个该领域常规工程师会怎么写？" |
| counter_example_attempt | 必须真的写出一段答案（不少于 50 字）；完全写不出来标 "none" |
| counter_example_strength | 四档自评 strong / moderate / weak / none |
| proposed_type_after_check | 根据 strength 自动降档 |

### 反例三层模板

子 agent 写反例时按三层设想填：

- 设想 1（最朴素做法）：一个刚入行的工程师可能会怎么解决？
- 设想 2（成熟做法）：业界已有的标准库 / 已有专利 / 行业惯例怎么做？
- 设想 3（替代路径）：换一个完全不同的技术路线是否也能达到类似效果？

不要求三条全写，但至少写出 1 条能立住的，否则 strength 标 weak / none。

### 四档 strength 判据

| strength | 判据 |
|---|---|
| strong | 能写出符合常识的对照方案，且该方案的实现路径与本案 DF 高度相似 |
| moderate | 能写出对照方案，但与本案 DF 有一定差异 |
| weak | 能想到但说不清楚，或对照方案技术效果显著差于本案 |
| none | 完全写不出对照方案 |

### 自动降档规则（机械执行）

| strength | proposed_type_after_check |
|---|---|
| strong | 必须降到 parameter 或 engineering |
| moderate | 可保留 structural 或降到 parameter |
| weak | 保留原始 type |
| none | 保留原始 type，但记入 dfs_with_none_counter_example |

### 标签纪律

DF type 标签必须经反例自检确认。子 agent 禁止：

- 为了让 DF "看起来更牛" 把 strength 评低
- 跳过 counter_example_attempt 字段
- 在 strength = strong 时仍保留 structural

### df-rationale-signals.yml 字段示例

```yaml
generated_at: <YYYY-MM-DD>
schema_version: v1

df_rationale_map:
  - df_id: DF-1
    claimed_type: structural
    description_brief: <DF 简要描述>
    counter_example_question: "面对这个技术问题，一个该领域常规工程师会怎么写？"
    counter_example_attempt: |
      <子 agent 真的写出的反例描述，≥ 50 字>
    counter_example_strength: strong
    proposed_type_after_check: parameter
    rationale_for_downgrade: |
      <为何降档的一句话理由>

aggregate_signals:
  total_dfs: <整数>
  dfs_claimed_structural: <整数>
  dfs_with_strong_counter_example: <整数>
  dfs_with_none_counter_example: <整数>
  dfs_proposed_downgrade: <整数>
  dfs_after_check_structural: <整数>
  dfs_after_check_parameter: <整数>
  dfs_after_check_engineering: <整数>
```
