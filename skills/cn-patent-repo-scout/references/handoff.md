# 扫描结果交接规则

> Windows 原生环境：命令中的 `python3` 请用 `python` 或 `py` 代替。

## 交接目标

扫描 skill 只准备方向和核心资料，不直接进入后续流程。用户在 S6 必须通过 `AskUserQuestion` 控件二选一：

- `cn-patent-workflow-orchestrator`：启动完整起草编排器（覆盖主线分析、现有技术检索、技术交底、正式稿起草、代理师审稿、DOCX 导出）。
- 暂停：只保存扫描产物，不创建任何状态文件。

## 交接文件

Top-N 中所有推荐方向都必须生成独立目录：

`patent/repo-scout/directions/<direction-slug>/`

每个方向至少包含：

- `direction-record.json`：方向记录，包含方向摘要、评分、证据线索、候选核心资料和确认状态。
- `source-material-roles.json`：该方向的资料角色清单。未被用户选中时可记录候选核心资料，但必须标记为待确认；用户确认后才可作为后续输入。

后续流程使用的交接文件路径是：

`patent/repo-scout/directions/<direction-slug>/source-material-roles.json`

每个方向必须单独保存交接文件，禁止用“当前选中方向”覆盖旧方向。这样用户第二次查看 `recommendation-report.md` 并选择另一个方向时，可以直接用该方向对应的交接文件启动编排器。

`<direction-slug>` 规则：

- 基于方向名称生成，使用小写字母、数字和连字符。
- 中文方向可使用简短英文含义或拼音。
- 若同名目录已存在，追加 `-2`、`-3` 等后缀。

`direction-record.json` 推荐结构：

```json
{
  "slug": "path-optimization",
  "title": "候选方向名称",
  "summary": "方向摘要",
  "confidence": "medium",
  "scores": {
    "innovation": 0.4,
    "evidence_strength": 0.3,
    "protection_value": 0.2,
    "clarity": 0.1
  },
  "candidate_core_materials": [
    {
      "path": "src/pipeline/algo_core.cpp",
      "reason": "核心算法实现"
    }
  ],
  "confirmation_status": "candidate"
}
```

`source-material-roles.json` 推荐结构：

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
  "next_step": ""
}
```

如果方向尚未被用户选中，`requires_confirmation` 必须为 `true`，`selected_direction.source` 不得标记为 `repo-scout-confirmed`，且 `next_step` 留空。用户选择该方向后，才能将确认后的文件复制或导入到 `patent/<patent-slug>/source-material-roles.json`。

注意：`source-material-roles.json` 是交接文件，结构为顶层 `selected_direction` 与 `items`。进入完整编排器后，初始化脚本会做两件事：(1) 把 `items` 归一化为 `state.source_material_roles.items`；(2) 把 `selected_direction` 原样写入 **`state.selected_direction`（state 顶层，而非 `state.source_material_roles.selected_direction`）**。下游脚本（如 `lib/preconditions.py` 中 `step-1` enter 断言）按顶层路径读取，不要在交接文件中提前包一层 `source_material_roles`。

## 角色映射

- 核心算法实现 → `核心资料`
- 设计文档、需求说明、技术说明 → `技术交底`
- 实验数据、性能对比、仿真结果 → `核心资料`
- 参考样稿、格式样稿 → `参考样稿`
- 现有技术、论文、对比材料 → `现有技术`

## 进入主线分析

主线分析不再作为 S6 单独的下一步入口。已确认方向下的保护路径设计、特征分层和发明点用途表整理由 `cn-patent-workflow-orchestrator` 编排器内部调度 `cn-patent-mainline-analysis` 完成。用户在 S6 选择「进入完整编排器」后，编排器会读取 `selected_direction` 与 `items`，并以此为输入启动主线分析。本 skill 不直接调用主线分析。

## 进入完整编排器

若用户在 S6 选择 `cn-patent-workflow-orchestrator`：

**重要：选择此选项后，本 skill 不得直接调用 `cn-patent-workflow-orchestrator`。** 必须先输出以下提示并停住，由用户手动 `/compact` 后重新触发编排器：

> 已选择进入完整起草编排器。当前会话上下文已较重，建议先执行 `/compact` 压缩上下文，然后重新调用 `cn-patent-workflow-orchestrator` 继续完整起草。编排器会从 `patent/repo-scout/directions/<direction-slug>/source-material-roles.json` 读取方向和资料，不依赖扫描过程中的对话上下文，所以压缩不会丢失已确认的选择。

用户重新触发编排器后，编排器按以下顺序执行：

1. 询问或确认 `patent-slug`。
2. 在用户项目根目录下创建 `patent/<patent-slug>/`。
3. 将 `patent/repo-scout/directions/<direction-slug>/source-material-roles.json` 导入或复制为 `patent/<patent-slug>/source-material-roles.json`。
4. 初始化状态文件时使用：

```bash
python3 scripts/new-iteration-state.py --project-root . --output-path patent/<patent-slug>/state/patent-iteration-state.json --material-roles-path patent/<patent-slug>/source-material-roles.json
```

## 不生成编排状态的情况

- 用户只想看扫描报告。
- 用户在 S6 选择「暂停」。
- 所有推荐方向置信度均为 low，且用户未确认继续。
- 用户尚未明确选择下一步。
- 用户已在 S6 选择「进入编排器」但尚未 `/compact` 并重新触发 `cn-patent-workflow-orchestrator`。本 skill 不得绕过 compact 提示直接初始化状态文件。
