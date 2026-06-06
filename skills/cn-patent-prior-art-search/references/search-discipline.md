## 落盘文件

检索与创造性筛选的全部 Markdown 产物写入单一文件：

- `patent/<patent-slug>/evidence/prior-art-search-report.md`

检索式、专利/研究候选表、最接近现有技术、检索后可主张发明点、区别特征与技术效果、创造性筛选表、推荐保护路径与用户确认分叉点均作为该文件的章节，不得拆到未约定的其他路径。章节与状态字段映射见本 skill 的 `SKILL.md`。

## 中文专利优先强制规范

现有技术检索必须优先检索中文专利，并补充搜索 Google Patents。只要当前环境具备联网检索能力，每条保护路径候选都要先覆盖中文专利来源，再用 Google Patents 做补充专利检索，最后补充论文或其他研究资料；不得在未尝试中文专利检索的情况下直接用Google Patents ,检索论文或通用网页结果替代。

优先使用以下检索入口：中文专利入口至少尝试其中 2 个，Google Patents 作为补充入口；若入口不可用，必须在检索报告中记录失败入口、查询式和失败现象，然后改用其他入口继续检索：

- 国家知识产权局：https://www.cnipa.gov.cn/
- 专利检索及分析系统：https://pss-system.cponline.cnipa.gov.cn/
- 中国专利公布公告：https://epub.cnipa.gov.cn/
- 中国及多国专利审查信息查询：https://cpquery.cponline.cnipa.gov.cn/
- 佰腾网专利检索：https://www.baiten.cn/
- SooPAT 专利检索：http://www.soopat.com/

## 何时必须检索

出现以下任一情况时，不要只凭仓库内容直接拍板主线：

- 用户要求判断哪个主线更有创造性
- 需要写"最接近现有技术""区别特征""技术效果"
- 已准备进入独立权利要求起草
- 用户要求正式稿、申报稿或代理师风格稿

## 检索原则

- 中文专利是专利检索的第一优先级；Google Patents 是必须补充检索的第二入口，用于交叉验证中文专利结果、补充同族专利和外文公开文本。
- 专利优先使用专利公开文本页面作为主证据。
- 论文或研究优先使用论文原文、出版社页面、arXiv 或作者主页作为主证据。
- 每轮至少覆盖一组专利检索和一组研究检索。
- 不只看标题，要看摘要、独立权利要求或核心方法段。
- 不要只找"最像"的一篇，还要找"最容易卡住当前主线"的那几篇。
- 只要当前环境提供 WebSearch、WebFetch、浏览器、MCP 检索工具或可联网命令中的任一能力，即视为具备联网检索条件；不得使用"缺少联网检索条件"降级模板。
- CNIPA 无法访问不等于无法联网检索；应改用 WebSearch 定位 CNIPA、Google Patents、PatentScope、专利公布公告、论文页面或其他公开来源。

## 联网检索硬门禁

在 Gate A 前，必须先完成真实联网检索，除非已经证明当前回合没有可用联网能力。

不得把以下情况当作"无法联网"：

- 检索工作量大、时间紧或用户催进度
- 已经能基于项目材料做初筛
- CNIPA 首页或某个检索源暂时不可访问
- 未尝试 WebSearch/WebFetch/浏览器/MCP，就假定无法访问外部来源
- 只写了检索式但没有打开或读取外部结果

若环境中有 WebSearch 等联网工具，最低检索动作是：

- 每条保护路径候选至少执行 1 组中文专利检索式、1 组 Google Patents 补充专利检索式和 1 组研究检索式
- 中文专利检索式必须优先投向上方中文专利入口；入口失败时记录失败原因并切换其他中文专利入口
- 至少打开或读取足以判断摘要、权利要求或核心方法的外部结果
- 在检索报告中记录检索式、来源 URL、读取要点、与保护路径候选的相似点和区别点，以及该外部结果可支撑或削弱的候选发明点
- 若某个来源失败，记录失败来源和错误后改用其他公开来源；不得直接降级为初筛

## 缺少联网检索条件时

只有在已经检查并记录当前环境没有可用 WebSearch、WebFetch、浏览器、MCP 检索工具或可联网命令，或全部联网尝试均失败且已记录失败原因时，才允许使用本降级出口。

降级前必须在检索报告中写明：

- 已检查的联网工具或检索入口
- 每次尝试的查询式、来源、错误或失败现象
- 为什么不能改用其他公开来源继续检索

满足以上条件后，必须明确标注：

- 本轮仅完成"基于已有材料的创造性初筛"
- 最接近现有技术尚未经过外部检索确认
- 正式申报前仍需补做检索和代理师创造性评估

## IPC 前置纪律（A 类升级新增）

**检索前**必须先输出 IPC 分类号预测，写入 `state.prior_art_search.ipc_classifications`：

- **4 位主分类号**必填（如 `H04N`、`G06F`）
- **6 位**推荐（如 `H04N21`），**8 位**可选（如 `H04N21/8547`）
- **主/副分类号**区分：主分类号是核心权利保护方向，副分类号是相关技术域
- **信心来源**四档：`direct`（关键词直接命中 IPC 描述）/ `analogy`（类比已知技术域）/ `engineering`（工程经验推断）/ `fallback`（兜底，需在报告里说明低信心）

不依赖完整 IPC 字典（7 万条不落地）；N8 凭交底书内化判断，报告 `## IPC 预测与厂商定向` 子表 1 如实记录信心来源。

## 五轨标配（A 类升级新增）

每条保护路径候选必须覆盖以下 5 个轨道（**调用 OR 显式 Skip with reason**）：

| 轨道 | track 字段值 | 合法 source_type | 备注 |
|---|---|---|---|
| 中文专利 | `chinese-patent` | `cnipa-web`、`google-patents-web` | 中文关键词 + IPC |
| 英文专利 | `english-patent` | `google-patents-web` | 英文关键词 + CPC/IPC |
| 厂商定向 | `vendor` | `google-patents-web`（带 `assignee_filter`） | N8 自决头部 5-10 家厂商，写入 `target_assignees` |
| 学术论文 | `paper` | `arxiv-api`（首选）→ fallback `web-fallback` | 调 `scripts/api-search/arxiv_search.py` |
| 标准/规范 | `standard` | `standards-web` | ISO/IETF/IEEE mailing list + GitHub issues |

任意轨道当首选 API/源不可用时均可降级 `web-fallback`，按 `## 报告可读性纪律` 规则在备注中说明降级原因。

合法 source_type 集合 = `{cnipa-web, google-patents-web, arxiv-api, standards-web, web-fallback}`。

某轨道确实不适用时（如该领域无明确头部厂商）允许显式 Skip，必须填 `skipped=true` + `skip_reason` 非空。

## 检索路径记录纪律（A 类升级新增）

每次 API/Web 调用必须 append 一条到 `state.prior_art_search.paths_attempted`，字段 schema：

```json
{
  "track": "chinese-patent|english-patent|vendor|paper|standard",
  "source_type": "cnipa-web|google-patents-web|arxiv-api|standards-web|web-fallback",
  "query": "实际下发的检索式",
  "ipc_filter": "实际下发的 IPC（不支持的源记录用户传入值）",
  "assignee_filter": "实际下发的 assignee（不支持留 null）",
  "hits_count": 0,
  "error": null,
  "skipped": false,
  "skip_reason": null,
  "elapsed_ms": 0,
  "ts": "ISO-8601 带时区时间戳（取调用发起时刻；N8 写入时补）"
}
```

**Skip 条目特例**：当 `skipped=true` 时，`elapsed_ms` 和 `ts` 可留 `null`（无实际调用，时间无意义）；`error` 也应保持 `null`，错误原因写在 `skip_reason`。

五轨各**至少**一条记录；validate-stage `step-2.exit` 的 `CoversTracks` 谓词拒绝空轨道。

报告 `## 检索路径走过记录` 仅列**实际有调用 / 有明确 Skip 决策**的（不强求 5 个轨道全列）。

## 报告可读性纪律（A 类升级新增）

- **去掉**编号前缀：Q01-Q08 → 「检索式 1 / 2 / …」；P1-P10 → 「专利 1（公开号）」；R1-R6 → 「研究 1（出处）」；SG-1~5 → 「补检建议 1 / 2 / …」。
- **保留**且**首次出现展开**：DF-x（区别特征）、CIP-x（可主张发明点）。示例：「区别特征 DF-1（按 track 隔离的累加器与 base_duration）：……」。
- **不在本报告造**：TP-x（技术锚点）/ IP-x（创新点）引用其他文档，写法「证据锚点 TP-1（详见 evidence-matrix.md）」。
- **顶部强制**新增 `## 术语与编号说明` 小节，列出本报告会出现的编号约定（DF / CIP / 外引）。
