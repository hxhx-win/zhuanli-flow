# 现有技术检索与创造性筛选报告

- Project root: `{{PROJECT_ROOT}}`
- Generated at: `{{GENERATED_AT}}`
- Search status: `draft`
- Recommended mainline: `[待填写]`
- Creativity conclusion: `[待填写]`

## 术语与编号说明

本报告中的编号约定（首次出现处必须括号展开含义）：

- **DF-x**：区别特征（Distinguishing Feature）。示例：「区别特征 DF-1（短中文描述）」。
- **CIP-x**：检索后可主张发明点（Claimable Invention Point）。示例：「检索后发明点 CIP-1（短中文描述）」。
- 其他章节直接用中文名 + 阿拉伯数字编号（如「检索式 1」「专利 1」「研究 1」「补检建议 1」），不再使用 Q/P/R/SG 类前缀。
- 外部引用：「证据锚点 TP-1（详见 evidence-matrix.md）」、「原始创新点 IP-1（详见交底书）」——不在本报告内造此类编号。

## 检索范围

- 专利数据库：
- 论文/研究来源：
- 时间范围：
- 语言范围：
- 检索目的：

## IPC 预测与厂商定向

### 子表 1：IPC 分类号

| 分类号 | 颗粒度 | 主/副 | 信心来源 |
|---|---|---|---|
| [待填写，如 H04N21/8547] | [4/6/8] | [主/副] | [direct/analogy/engineering/fallback] |

### 子表 2：厂商定向清单

| 厂商名 | 选定理由 |
|---|---|
| [待填写] | [待填写] |

若该领域无明确头部厂商，子表 2 留单行：「该领域无明确头部厂商（target_assignees.skipped=true）」。

## 检索式

| 序号 | 检索式 | 轨道 | source_type | 申请人限定 | 入口/工具 | 命中 | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | `[待填写]` | [chinese-patent/english-patent/vendor/paper/standard] | [cnipa-web/google-patents-web/arxiv-api/standards-web/web-fallback] | [GoPro / -] | [待填写] | [N 件] | [待填写] |

## 专利候选

| 序号 | 标题 | 公开号 | source_type | 链接 | 与本方案接近点 | 初步风险 |
|---|---|---|---|---|---|---|
| 1 | [待填写] | [待填写] | [cnipa-web/google-patents-web/web-fallback] | [待填写] | [待填写] | [待填写] |
| 2 | [待填写] | [待填写] | [cnipa-web/google-patents-web/web-fallback] | [待填写] | [待填写] | [待填写] |

## 研究候选

| 序号 | 标题 | DOI/来源 | source_type | 链接 | 与本方案接近点 | 初步风险 |
|---|---|---|---|---|---|---|
| 1 | [待填写] | [待填写] | [arxiv-api/web-fallback] | [待填写] | [待填写] | [待填写] |

## 最接近现有技术

- 候选编号：
- 选择原因：
- 对独立权利要求的限制点：

## 检索后可主张发明点

首次提及 CIP-x 时务必括号展开。示例：「检索后发明点 CIP-1（按 track 隔离的 int64 累加器写入 stts）：……」。

| 发明点 | 对应候选发明点 | 未被公开的区别特征 | 技术效果 | 支撑证据 | 权利要求用途 | 风险 |
|---|---|---|---|---|---|---|
| CIP-1（[短描述]） | [待填写] | [待填写] | [待填写] | [待填写] | [独权核心/从权候选/实施例支撑/分案保留/暂不写入] | [待填写] |

## 区别特征与技术效果

首次提及 DF-x 时务必括号展开。示例：「区别特征 DF-1（双向 base_duration 单位吸收）：……」。

| 区别特征 | 出处 | 技术效果 | type | 标记 |
|----------|------|----------|------|------|
| DF-1（[短描述]） | [待填写] | [待填写] | [structural/parameter/engineering] | [待填写] |

## 保护路径创造性筛选

| 路径 | 与最接近现有技术的区别集中度 | 项目证据强度 | 独立权利要求抽象度 | 风险(单行描述,无风险写"无") | 筛选结论 |
|------|------------------------|------------|--------------------|------|----------|
| 候选 1 | [待填写] | [待填写] | [待填写] | [待填写] | [待填写] |

## 推荐进入 Gate A 的保护路径

- 推荐保护路径：
- 推荐保护客体：
- 放弃或降级的保护路径：
- 需要用户确认：

## 检索路径走过记录

仅列**实际有调用 / 有明确 Skip 决策**的轨道（与 state.prior_art_search.paths_attempted 同步）：

| 轨道 | source_type | 调用次数 | 总命中（hits_count） | 失败/Skip 原因 |
|---|---|---|---|---|
| [chinese-patent] | [cnipa-web] | [N 件] | [M 件] | [无 / 错误描述 / Skip 原因] |
| [standard] | -                       | 0      | 0     | [Skip: 该领域无标准] |

## 补检建议

| 序号 | 描述 | 影响 | 建议行动 |
|---|---|---|---|
| 1 | [待填写] | [待填写] | [待填写] |

## 可直接回写到状态文件的信息

- `prior_art_search.ipc_classifications`：（结构见 state schema）
- `prior_art_search.target_assignees`：（结构见 state schema）
- `prior_art_search.paths_attempted`：（结构见 state schema）
- `closest_prior_art`：
- `claimable_invention_points`：
- `distinguishing_features`：
- `prior_art_search.recommended_mainline`：（兼容字段，语义为检索后推荐保护路径）

注意：检索阶段不得写入 `selected_mainline` 或 `selected_protection_object`。该两个字段只能在 Gate A 用户确认后由编排器写入。

## 引用链接

- [待填写]
