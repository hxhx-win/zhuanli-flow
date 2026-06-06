---
name: cn-patent-prior-art-search
description: 当用户已有已确认技术方向下的保护路径候选和候选发明点，要求做现有技术检索、提取检索后真正可主张发明点、找出最接近现有技术、提取区别特征时使用。覆盖中文专利（CNIPA）、Google Patents、研究文献的联网检索与可追溯结果记录。不挑方向（用 `cn-patent-repo-scout` / `cn-patent-mainline-analysis`）、不起草正式稿（用 `cn-patent-formal-drafting`）。触发词：现有技术检索、专利检索、CNIPA 检索、Google Patents、最接近现有技术、区别特征提取、可主张发明点、`prior-art-search-report.md`、prior art search。
---

# 现有技术检索与创造性筛选

> Windows 原生环境：命令中的 `python3` 请用 `python` 或 `py` 代替。

针对保护路径候选和候选发明点执行可追溯的现有技术检索，提取检索后真正可主张发明点，并据此筛选出最稳妥的 Gate A 推荐保护路径。

## 双模式

判断逻辑：`patent/<patent-slug>/state/patent-iteration-state.json` 存在 → 编排模式；否则 → 独立模式。

- **独立模式**：用户提供 1 条或多条保护路径候选描述即可运行
- **编排模式**：由编排器调用，额外回写 `prior_art_search.*`, `closest_prior_art`, `distinguishing_features`, `claimable_invention_points`

## 工作流

| 步骤 | 动作 | 产出 |
|------|------|------|
| 1 | 确认保护路径候选和检索范围 | — |
| 2 | **IPC 预测**（4 位主必填 + 6/8 位推荐 + 主/副 + 信心来源） | `state.prior_art_search.ipc_classifications` + 报告 `## IPC 预测与厂商定向` 子表 1 |
| 3 | **厂商识别**（N8 凭技术域定 top 5-10 家头部厂商；无则显式 Skip） | `state.prior_art_search.target_assignees` + 报告 `## IPC 预测与厂商定向` 子表 2 |
| 4 | 设计**五轨**检索式（中文专利 / 英文专利 / 厂商定向 / 学术论文 / 标准规范） | 报告 `## 检索式` |
| 5 | 执行联网检索（论文轨**首选 arxiv_search.py API**，失败降级 WebSearch），每次调用 append `paths_attempted[]` 并回填 `## 检索式` 命中列 | 报告 `## 检索式`（命中列）`## 专利候选` `## 研究候选` `## 检索路径走过记录` + `state.prior_art_search.paths_attempted` |
| 6 | 选出最接近现有技术 | 报告 `## 最接近现有技术` |
| 7 | 提取 DF / CIP（首次出现处展开括注） | 报告 `## 区别特征与技术效果` + `## 检索后可主张发明点` |
| 8 | 基于 CIP 推荐保护路径 + 分叉点 | 报告 `## 推荐进入 Gate A 的保护路径` |

## 核心纪律（硬门禁）

- 中文专利优先，至少尝试 2 个中文入口
- 有联网能力就必须真实检索，不得降级为"仅完成初筛"
- CNIPA 不可用 ≠ 无法联网，必须切换其他入口继续
- 每条保护路径候选至少 1 组中文专利 + 1 组 Google Patents + 1 组研究检索
- 只写了检索式但没打开或读取结果 = 未完成检索
- 降级前必须逐项记录已尝试的工具和失败原因
- **N8 子 agent 自判纪律**:每条保护路径候选的 3 组检索(中文专利 + Google Patents + 学术)**优先各派一个子 agent**;当多条保护路径候选技术内容相同/相近（如方法/装置/介质三轨同核心）且总检索源 ≥ 6 个、命中 ≥ 20 件，或检索源含跨平台/多语言时**必须**嵌套派子 agent 分担;当总工作量小（如单一保护路径 + 单一中文源 + ≤ 5 件命中）时,当前 agent 可一次性完成所有检索并直接 Write 到 `prior-art-search-report.md` 对应章节(`## 检索式` 表追加一行 + 命中候选追加对应表行 + 在线读取的关键专利/学术摘要落盘到对应章节)。无论是否嵌套,**必须等同满足**:写到磁盘的内容不返回父 agent；返回 summary ≤ 200 字；主 agent 不持有 WebSearch / WebFetch 命中详情。铁律以产物质量为准——若检索报告章节命中件数偏少（专利 < 5、学术 < 3）或缺关键最接近现有技术对比,自判选择应回退为嵌套派子 agent 重做
- **DF 抽取标签(N8 附属)**:每项 DF 必须标注 `type` 字段,取值 `structural | parameter | engineering`(结构性差异 / 参数差异 / 工程实现差异);下游 cn-patent-disclosure-draft 的 3a 创新性维度评估依赖此标签
- 每条 DF 必须经反例自检：子 agent 必须真的写出 counter_example_attempt 字段（≥ 50 字），不允许跳过；strength 与 proposed_type_after_check 按机械规则自动降档
- 反例自检与检索报告必须由同一个子 agent 一次性产出 df-rationale-signals.yml；strong 反例 ≥ 50% 时 3a 会判通胀，none 反例 > 50% 时 3a 会判应付
- **IPC 前置硬强制**：未输出 `ipc_classifications.primary`（4 位主分类号）前禁止开始检索；validate-stage `step-2.exit` 拒绝空 primary
- **五轨硬强制**：五轨（chinese-patent / english-patent / vendor / paper / standard）必须各有至少一条 `paths_attempted` 记录（调用 OR Skip with reason）；validate-stage `step-2.exit` 的 `CoversTracks` 谓词拒绝空轨道
- **论文轨首选 API**：调用 `python3 cn-patent-prior-art-search/scripts/api-search/arxiv_search.py --keywords "..." --output-json <path>` 而非 WebSearch + PDF 二进制读取；失败再降级 WebSearch `site:arxiv.org`
- **厂商定向轨道**：用 Google Patents Advanced 的 `assignee:` filter；`paths_attempted` 中 `track=vendor` 且 `assignee_filter` 非空区分于无 filter 的英文专利轨
- **报告可读性硬规定**：去除 Q/P/R/SG 编号前缀；DF/CIP 首次出现处必须括号展开短中文描述；报告顶部强制 `## 术语与编号说明` 小节。具体规则见 `references/search-discipline.md` 「报告可读性纪律」

## 输入（前置）

| 来源 | 路径 |
|------|------|
| 主线分析报告（编排模式） | `patent/<patent-slug>/analysis/mainline-analysis.md` |
| 证据矩阵（编排模式） | `patent/<patent-slug>/evidence/evidence-matrix.md` |
| 保护路径候选（独立模式） | 用户在对话中提供的 1 条或多条描述；若有 `mainline-analysis.md` 则优先读取 |

编排模式下，先读取状态文件中的 `mainline_analysis_path`，再读取 `evidence_matrix_path`。`mainline-analysis.md` 的 `## 检索输入摘要` 和 `## 待检索确认问题` 用于生成检索式和比对维度，不是创造性推荐。

## 输出物

所有路径相对于用户项目根目录，禁止写入 skill 目录。

**本 skill 的 Markdown 产物收敛为单一检索报告**（与 `cn-patent-project-drafting/assets/prior-art-search-report.template.md` 结构一致）：

| 逻辑产出 | 文件与章节 |
|----------|------------|
| 检索报告（总载体） | `patent/<patent-slug>/evidence/prior-art-search-report.md` |
| 检索式 | 同上，`## 检索式` |
| 专利候选表 | 同上，`## 专利候选` |
| 研究候选表 | 同上，`## 研究候选` |
| 最接近现有技术 | 同上，`## 最接近现有技术` |
| 检索后可主张发明点 | 同上，`## 检索后可主张发明点` |
| 区别特征与技术效果 | 同上，`## 区别特征与技术效果` |
| 保护路径创造性筛选表 | 同上，`## 保护路径创造性筛选` |
| 推荐保护路径、区别特征、技术效果 | 同上，`## 推荐进入 Gate A 的保护路径` + 筛选表各列 + `## 可直接回写到状态文件的信息` |
| 需用户确认的分叉点 | 同上，`## 推荐进入 Gate A 的保护路径` 下「需要用户确认」 |
| 引用链接清单 | 同上，`## 引用链接`（**硬强制**：节必须存在且非空；每条进入候选表的专利/论文/标准/产品资料、`## 最接近现有技术` 与 DF 反例自检引用过的来源、`## 检索式` 中声明命中的目标页，都各占一行；格式 `- <编号或简称>（<角色标注，如 最接近现有技术 / DF-X 反例公知来源 / 行业背景>）：<可解析 URL>`；联网受限来源保留链接并标注「（受限：<现象>）」；缺失或全部为占位视为检索未完成） |
| DF 反例自检信号 | `patent/<patent-slug>/evidence/df-rationale-signals.yml` | prior-art 子 agent 在写完检索报告同一次任务内产出；每条 DF 必填 counter_example_attempt + counter_example_strength；字段结构和规则见 `references/creativity-screening.md` 末尾"DF 反例自检规则" |

编排模式初始化：N8 在首次落盘前直接以 `cn-patent-project-drafting/assets/prior-art-search-report.template.md` 为模板 Write 到 `patent/<patent-slug>/evidence/prior-art-search-report.md`，无需独立初始化脚本。

独立模式：只生成/更新 `prior-art-search-report.md`，不写状态文件。

## 编排模式回写字段

回写 `patent/<patent-slug>/state/patent-iteration-state.json`：

- `prior_art_search.report_path` → `patent/<patent-slug>/evidence/prior-art-search-report.md`
- `prior_art_search.status` → `completed`（或降级时为 `screening-only`）
- `prior_art_search.search_date`：检索开始日期（YYYY-MM-DD）；N8 在 step-2 落盘报告时写入
- `prior_art_search.queries`、`patent_sources`、`paper_sources`、`closest_items`
- `prior_art_search.ipc_classifications`：来自报告 `## IPC 预测与厂商定向` 子表 1
- `prior_art_search.target_assignees`：来自报告 `## IPC 预测与厂商定向` 子表 2
- `prior_art_search.paths_attempted`：来自报告 `## 检索路径走过记录`（每次 API/Web 调用 append 一条）
- `prior_art_search.recommended_mainline`：来自报告 `## 推荐进入 Gate A 的保护路径`；为兼容既有脚本保留字段名，语义是”检索后推荐进入 Gate A 的保护路径”
- `claimable_invention_points`：来自报告 `## 检索后可主张发明点`
- `closest_prior_art`：来自报告 `## 最接近现有技术`
- `distinguishing_features`：来自筛选表或报告回写区（数组；必须绑定保护路径候选或检索后推荐保护路径）

检索阶段不得写入 `selected_mainline` 或 `selected_protection_object`。`selected_*` 字段只能在 Gate A 用户明确确认后由编排器写入。

多轮检索时：更新同一报告文件并在 `history.prior_art_rounds` 追加记录；不得覆盖未确认的上一轮报告路径而不留痕。

## 常见错误

- 用"检索工作量大"跳过检索 → 硬门禁，不允许
- 只用 Google 通用搜索替代专利检索 → 必须用专利入口
- 只看标题不看摘要/权利要求 → 必须读核心内容
- 找到一篇相似就停 → 还要找"最容易卡住主线"的

## 参考资料

- 检索纪律与入口列表：[references/search-discipline.md](references/search-discipline.md)
- 创造性筛选判断口径：[references/creativity-screening.md](references/creativity-screening.md)
- 必要前置 skill：`cn-patent-mainline-analysis`（提供保护路径候选输入）
