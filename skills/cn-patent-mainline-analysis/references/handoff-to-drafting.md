# 对接 cn-patent-domain-runtime 规则

## 适用场景

主线分析在编排器步骤 1 中完成后，回写证据矩阵、主线分析报告、保护路径候选摘要、候选发明点用途表和技术特征分层摘要。若资料角色来自前置扫描，应由 `cn-patent-repo-scout` 先生成交接文件，再由 `cn-patent-domain-runtime` 初始化状态文件。

## 接收扫描结果

当用户从扫描 skill 选择进入完整编排器时，编排器可接收：

- `patent/repo-scout/directions/<direction-slug>/source-material-roles.json`
- `patent/<patent-slug>/source-material-roles.json`

主线分析只消费已确认的资料角色，不负责扫描项目或生成扫描报告。

若资料角色来自 `cn-patent-repo-scout`，`source-material-roles.json` 中的 `selected_direction` 必须已经由用户选择对应 `<direction-slug>` 后确认，且其 `source` 应为 `repo-scout-confirmed`。若用户直接声明技术方向，则由主线分析或编排器构造 `source: "user-declared"` 的 `selected_direction`。

## source-material-roles.json 交接文件结构

```json
{
  "selected_direction": {
    "source": "repo-scout-confirmed",
    "slug": "path-optimization",
    "title": "候选方向名称",
    "summary": "方向摘要",
    "confidence": "medium",
    "source_material_roles_path": "patent/repo-scout/directions/path-optimization/source-material-roles.json"
  },
  "items": [
    {
      "path": "src/pipeline/algo_core.cpp",
      "role": "核心资料",
      "description": "用户确认的核心算法实现",
      "requires_confirmation": false
    }
  ],
  "next_step": "cn-patent-mainline-analysis"
}
```

该结构是 repo scout 到主线分析/工作流编排器的交接文件结构。编排器初始化状态文件时，才将 `items` 归一化写入状态字段 `source_material_roles.items`，并把 `selected_direction` 写入同名状态字段。

状态文件中的 `source_material_roles.items` 结构为：

```json
[
  {
    "path": "src/pipeline/algo_core.cpp",
    "declared_role": "核心资料",
    "declared_by": "cn-patent-repo-scout/user-confirmed",
    "use_as": "invention_evidence",
    "invention_evidence": true,
    "prior_art_source": false,
    "requires_confirmation": false,
    "notes": "核心算法实现"
  }
]
```

角色映射规则：
- 核心算法实现 → "核心资料"
- 设计文档 → "技术交底"
- 实验数据/性能对比 → "核心资料"
- 参考样稿 → "参考样稿"

## 落盘文件（步骤 1 必出）

| 文件 | 内容 |
|------|------|
| `patent/<patent-slug>/evidence/evidence-matrix.md` | 证据矩阵 |
| `patent/<patent-slug>/analysis/mainline-analysis.md` | `## 已确认技术方向` + `## 保护路径候选` + `## 保护客体初步判断` + `## 技术特征分层` + `## 候选发明点用途表` + `## 检索输入摘要` + `## 待检索确认问题` |

`## 技术特征分层` 应包含可供下游起草消费的扩展列：特征编号、层级、技术特征、技术作用、技术效果、主体归属、适合写入位置、证据来源和待确认事项。若使用非表格形式，也必须能提取出同等信息。

本阶段只准备检索输入，不写推荐结论或创造性结论。真正可主张发明点由 `cn-patent-prior-art-search` 在外部检索后写入 `claimable_invention_points`。

## 编排模式回写字段

主线分析完成后写入状态文件：

- `evidence_matrix_path` → 证据矩阵路径
- `mainline_analysis_path` → 主线分析报告路径
- `selected_direction`：已确认技术方向，来源为 `repo-scout-confirmed` 或 `user-declared`
- `protection_path_candidates`：保护路径候选摘要数组（从 `mainline-analysis.md` 的 `## 保护路径候选` 解析）
- `protection_object`：保护客体初步判断
- `feature_layers`：技术特征分层摘要（从 `## 技术特征分层` 解析）
- `invention_points`：候选发明点用途摘要（从 `## 候选发明点用途表` 解析）

`feature_layers` 中的每个条目建议保留以下字段，供起草、审稿和质量检查弱校验使用：

```json
{
  "id": "F1",
  "level": "必要",
  "feature": "技术特征描述",
  "technical_role": "该特征在方案链路中的作用",
  "technical_effect": "该作用带来的技术效果",
  "subject": "方法步骤/第一设备/第二设备/装置模块/系统交互/结构部件/介质指令",
  "drafting_position": "独权候选/从权候选/实施例支撑/替代实施方式/分案保留/暂不写入",
  "evidence": "证据来源",
  "open_issue": ""
}
```

不得在主线分析阶段写入 `selected_mainline` 或 `selected_protection_object`。这两个字段只能在 Gate A 用户明确确认后由编排器写入。

## 下游消费规则

- `cn-patent-prior-art-search`：读取 `mainline-analysis.md` 的保护路径候选、技术特征分层、候选发明点用途表、检索输入摘要和待检索确认问题，并用 `evidence-matrix.md` 核对证据。
- Gate A：读取 `mainline-analysis.md`、`evidence-matrix.md` 和 `prior-art-search-report.md`，生成确认包并等待用户确认。
- `cn-patent-formal-drafting`：Gate A 通过后，独权核心只消费 `selected_mainline`、`claimable_invention_points` 和 `distinguishing_features`；主线分析阶段的候选发明点不得直接作为独权核心。`feature_layers` 扩展字段用于从属权利要求、实施例、替代实施方式、实施方式覆盖计划和审稿检查。

正式起草阶段还应读取 `claim-type-classification.md` 完成保护客体判型；主线分析输出的 `protection_object`、`selected_protection_object`、`feature_layers[].subject` 和 `feature_layers[].drafting_position` 用于决定是否读取 `method-claim-drafting.md` 或 `structural-claim-drafting.md`。

## 实施方式覆盖计划交接

正式起草 skill 应基于 `feature_layers`、`claimable_invention_points`、`distinguishing_features` 和证据矩阵生成实施方式覆盖计划。该计划写入正式稿配套 evidence notes 或独立起草 notes，不写入 DOCX-ready 正文。覆盖计划至少记录：

- 独权必要特征到实施例段落的对应关系。
- 重要从属权利要求到支撑段落的对应关系。
- 多主体方法、装置、系统、设备和介质的实施例覆盖情况。
- 替代实施方式、异常/回退路径、参数范围、结构替代和数据格式替代的覆盖情况。
- 关键附图与实施段落、图号或标号的对应关系。

覆盖计划只能基于已确认主线和证据材料生成；资料不足时应列为待确认或阻断，不得臆造参数、结构或技术效果。

若发现新的核心资料，应同步更新状态文件中的 `source_material_roles`；不得默认生成 `.agents/outputs/evidence/source-material-roles.md`。
