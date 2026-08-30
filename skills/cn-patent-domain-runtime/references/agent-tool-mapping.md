# Agent 工具映射

本 skill 使用通用动词描述操作。各 agent 工具对应关系：

| 操作 | Claude Code | Cursor | Codex |
|------|-------------|--------|-------|
| 读取文件内容 | Read tool | read_file | cat/read |
| 搜索代码/文件 | Grep/Glob | search_files | grep/find |
| 编辑已有文件 | Edit tool | edit_file | patch/edit |
| 创建新文件 | Write tool | create_file | write |
| 执行 shell 命令 | Bash tool | run_terminal_command | shell |
| 网络搜索 | WebSearch | browser | web_search |
| 获取网页内容 | WebFetch | browser | curl |
| 派子 agent 隔离执行 | `Agent(subagent_type=general-purpose)` | Composer Background Agent / Sub-Agent | Codex Sub-Agent / Task |

## N0 编排器分派纪律（硬纪律）

主编排器**禁止**直接读子 skill 输入资料或直接 Write 子 skill 大体量产物（evidence-matrix.md、mainline-analysis.md、prior-art-search-report.md、pre-draft-review.md、disclosure-draft.md、formal draft、attorney-review.md 等）。**所有产出型子 skill 阶段（step 1、step 2、step 3 评审、step 3 技术交底书、step 4 正式稿、step 6 代理师审稿）必须通过 "派子 agent 隔离执行" 这一行对应的工具派 subagent 执行**，子 skill 的 SKILL.md 由 subagent 通过 `Skill` 工具或手工 Read 加载。铁律：

- 主编排器只做：状态文件读写、用户交互（Claude Code 用 AskUserQuestion；Cursor/Codex 等价）、脚本调用（patent-env-check / new-iteration-state / handoff-package / handoff-pickup / quality-check）、Gate 拍板、verdict 分支、风险登记同步
- subagent 直接 Write 落盘到用户项目根目录；写到磁盘的内容**不返回**给主编排器
- subagent 返回主编排器的摘要严格 ≤ 600 字（step 1/2/3 评审/3 交底书）或按子 skill SKILL.md 字数上限
- 主编排器派 subagent 前必须把已确认事实（用户决策、verdict、关键技术口径校正、上游产物路径）**显式写进 prompt**，subagent 不得自行猜测
- 直读直写大体量产物属于跳步反模式，见 `orchestration-philosophy.md § 跳步红旗`

例外（主编排器直接做，不派 subagent）：

- 状态文件 `patent-iteration-state.json` 字段读写（小、原子）
- 脚本调用与 stderr/stdout 回显
- 用户交互、Gate 确认包条目展示
- 产物存在性与行数核对（Bash `ls` / `wc -l`）
- 用户已明确单点修订（如只让改 1~2 处措辞），可主编排器直接 Edit

## 脚本执行规则

1. 运行 `patent-env-check` 获取能力矩阵
2. **只使用 .py 版本**（跨平台，功能完整）
3. Python 不可用 → 阻断并报告

## 脚本对照

| 脚本功能 | 使用脚本 | 备注 |
|----------|----------|------|
| 环境预检 | patent-env-check.py | `--output-path` |
| 参考文本提取 | extract-reference-text.py | 支持 `--pdf-tool-path`/`--project-root`/`--pdf-tool-config-path` |
| PDF 提取就绪 | test-pdf-extraction-readiness.py | 委托 extract-reference-text.py |
| 质量检查 | automated_quality_check.py | 完整 evidence-notes/术语/pending/Gate 校验 |
| LaTeX 校验 | test-latex-formula-readiness.py | 含空 fence/未关闭 fence 检测 |
| 状态初始化 | new-iteration-state.py | 含 material roles 和 evidence 文件；旧 state 升级用 `--migrate-from` |
| Stage 前置/出口断言 | validate-stage.py | 主编排器在进入/退出 stage 时调，输出 JSON（ok/blocked/warned + missing） |
| 下一步路由 | get-next-step.py | 每步完成后跑，14 类 A + 9 类 B stage 全覆盖 |
| 起草上下文提取 | extract-drafting-context.py | step 4 派单前必跑;输出 drafting-context.json(~3 KB) |
| DOCX 导出 | export-patent-draft-docx.py | 见 cn-patent-docx-export skill |

## Python 版 Windows 特有功能

.py 版本通过 `platform.system() == "Windows"` 条件分支保留了以下 Windows 特有能力：

- **Word COM**：`extract-reference-text.py` 通过 `win32com.client` 读取 .doc/.docx
- **多编码读取**：UTF-8 → GBK/CP936 → latin-1 fallback（适配中文 Windows 环境）

## 全阶段执行者映射（N0 落地表）

> 真相源 `scripts/lib/stage_executors.py`，本表为人读 doc。运行时由 `validate-stage` / `get-next-step` 调 `lookup(stage)` 输出 `executor_info`。新增 stage / 改执行者改 `lib/stage_executors.py` 与 `lib/preconditions.py`，module load 时自检对齐。

按 N0 硬纪律统一映射，所有产出型子 skill 阶段一律派 subagent：

| 阶段 | 执行者 | 工具 |
|---|---|---|
| step 0 环境预检 + 状态初始化 | 编排器(主 agent) | Bash 调 `patent-env-check.py` / `new-iteration-state.py` |
| step 0.3 资料角色确认 | 编排器(主 agent) | AskUserQuestion + Edit 状态文件 |
| **step 1 主线分析** | **`cn-patent-mainline-analysis` 派 subagent** | **Agent (subagent_type=general-purpose)** |
| **step 2 现有技术检索** | **`cn-patent-prior-art-search` 派 subagent** | **Agent (subagent_type=general-purpose)** |
| **step 3 评审** | **`cn-patent-disclosure-draft` 派 subagent** | **Agent (subagent_type=general-purpose)** |
| **step 3 技术交底书** | **`cn-patent-disclosure-draft` 派 subagent** | **Agent (subagent_type=general-purpose)** |
| step 3 用户分流决策 | 编排器(主 agent) | AskUserQuestion |
| Gate A 起草前决策 | 编排器(主 agent) | AskUserQuestion + Read (decision-categories.json + state 文件) |
| Gate A 确认 | 编排器(主 agent) | AskUserQuestion |
| handoff 段(packaged 切换) | 编排器(主 agent) | Bash 调 `scripts/handoff-package.py` |
| handoff 段(picked_up 切换) | 编排器(主 agent) | Bash 调 `scripts/handoff-pickup.py` |
| handoff 段(notes 准备状态) | 编排器(主 agent) | AskUserQuestion + Bash 验证文件存在 |
| handoff 段(local 切换) | 编排器(主 agent) | 直接写 state(不调脚本) |
| **step 4 正式稿起草** | **`cn-patent-formal-drafting` 派 subagent;派单前必先跑 `extract-drafting-context.py` 生成 `drafting-context.json`** | **Agent (subagent_type=general-purpose)** |
| step 5 审稿前风险确认 | 编排器(主 agent) | AskUserQuestion + Edit 状态文件 |
| **step 6 代理师审稿（前置：模式选择）** | **编排器 AskUserQuestion 选 single/multi + 写入 `state.step_6.review_mode` + `state.step_6.review_mode_selected_at`（伪产物 `reviews/review-mode-selection.md` 已废，改 state 字段，通过派单 prompt 传给 subagent）** | **AskUserQuestion + Edit state** |
| **step 6 代理师审稿（single 模式）** | **`cn-patent-attorney-review` 派 1 个 subagent (mode=single)** | **Agent (subagent_type=general-purpose)** |
| **step 6 代理师审稿（multi 模式）** | **`cn-patent-attorney-review` 主 agent 单条 message 并行派 6 个方向 subagent + 后续派 1 个综合 subagent** | **Agent ×6 并行 + Agent ×1 综合** |
| step 7 Gate B 用户确认 | 编排器(主 agent) | AskUserQuestion |
| step 8 反馈修订 | **`cn-patent-attorney-review` 派 revision subagent (mode=revision)** | **Agent (subagent_type=general-purpose)** |
| step 9 Gate C 质量检查 + 交付 | 编排器(主 agent) | Bash 调 `automated_quality_check.py` + AskUserQuestion |

### disclosure-draft 派 subagent 契约（防漂移）

step 3 评审与 step 3 技术交底书两个阶段使用同一个 skill `cn-patent-disclosure-draft`，由派单 prompt 中的 `stage` 字段区分。编排器派单时 prompt 必须包含三段字段：

```
stage: review | disclosure-generation
skill_root: <skills_root>/cn-patent-disclosure-draft
patent_root: <patent root 绝对路径>
任务: subagent 内部通过 Skill 工具加载 cn-patent-disclosure-draft SKILL.md,按其「subagent 入口分路」段加载对应 stage 的纪律 references。
输入产物绝对路径列表（按列出顺序 Read，作为 Skill 加载失败时的硬路径兜底）:
  - review 时 4 份：df-rationale-signals.yml + evidence-matrix.md + mainline-analysis.md + prior-art-search-report.md
  - disclosure-generation 时 6 份：<skill_root>/assets/disclosure-template.md + <skill_root>/references/drafting-discipline.md + pre-draft-review.md + mainline-analysis.md + evidence-matrix.md + prior-art-search-report.md
输出产物绝对路径:
  - review → patent/<slug>/reviews/pre-draft-review.md
  - disclosure-generation → patent/<slug>/disclosure/disclosure-draft.md
```

字段口径以 `cn-patent-disclosure-draft/SKILL.md` 的「subagent 入口分路」与「主编排器派 subagent prompt 契约」两段为权威；本表与 SKILL.md 任一处修改必须同步另一处。

### mainline-analysis 派 subagent 契约（防漂移）

```
skill_root: <skills_root>/cn-patent-mainline-analysis
patent_root: <patent root 绝对路径>
任务: subagent 内部通过 Skill 工具加载 cn-patent-mainline-analysis SKILL.md,按其工作流执行主线分析。
输入产物绝对路径列表:
  - <patent_root>/source-material-roles.json
  - <用户声明的核心资料绝对路径列表（来自 source_material_roles.items）>
输出产物绝对路径:
  - <patent_root>/analysis/mainline-analysis.md
  - <patent_root>/evidence/evidence-matrix.md
  - <patent_root>/evidence/evidence-quality-signals.yml
```

### prior-art-search 派 subagent 契约（防漂移）

```
skill_root: <skills_root>/cn-patent-prior-art-search
patent_root: <patent root 绝对路径>
任务: subagent 内部通过 Skill 工具加载 cn-patent-prior-art-search SKILL.md,按其工作流执行现有技术检索。
输入产物绝对路径列表:
  - <patent_root>/analysis/mainline-analysis.md
  - <patent_root>/evidence/evidence-matrix.md
输出产物绝对路径:
  - <patent_root>/evidence/prior-art-search-report.md
  - <patent_root>/evidence/df-rationale-signals.yml
```

### formal-drafting 派 subagent 契约（防漂移）

step 4 正式稿起草由 `cn-patent-formal-drafting` SKILL 承载,编排器派 1 个 subagent 执行（独立模式 / 编排模式共用同一 SKILL）。

派单前**必须**先跑 `scripts/extract-drafting-context.py` 生成 `drafting-context.json`（~3 KB）;起草 subagent 通过此 context 文件读 Gate A 决策子树,**不再 Read state.json 全量**。schema 与字段口径见 `docs/superpowers/specs/2026-05-26-formal-drafting-skill-refactor-design.md` 附录 C。

派单 prompt 必须包含以下字段:

```
mode: drafting
skill_root: <skills_root>/cn-patent-formal-drafting
patent_root: <patent root 绝对路径,形如 <project_root>/patent/<patent-slug>>
输入产物绝对路径列表:
  - <patent_root>/disclosure/disclosure-draft.md
  - <patent_root>/reviews/pre-draft-review.md
  - <patent_root>/state/drafting-context.json
  - (条件) <patent_root>/reviews/patent-dept-notes.md
      仅当 drafting-context.handoff.patent_dept_notes_path 非 null
      且 drafting-context.handoff.notes_fill_mode ∈ {prompt, document, manual}
输出产物绝对路径（由 subagent 落盘）:
  - <patent_root>/drafts/markdown/<draft-name>.md
  - <patent_root>/drafts/markdown/<draft-name>-evidence-notes.md
  - <patent_root>/drafts/figures/<draft-name>/figure-generation-plan.md
  - <patent_root>/drafts/figures/<draft-name>/figure-manifest.json

任务: 内部通过 Skill 工具加载 cn-patent-formal-drafting SKILL,
      按其 §前置读取阶段加载矩阵起草正式稿。
读取允许范围: 上列输入产物 + skill_root 内任意 references（按阶段加载矩阵命中）。
**禁止读取**: patent_root 下 evidence/ 与 analysis/ 目录中的三份上游产物
  (mainline-analysis.md / prior-art-search-report.md / evidence-matrix.md),
  已固化为 N6 消费契约。
返回主编排器 ≤ 600 字摘要 + 输出产物相对路径列表;
正文本身已经落盘,不在返回值中重复。
```

字段口径以本契约为权威;`cn-patent-formal-drafting/SKILL.md` §前置读取「阶段 0」段与 §核心纪律 N6 消费契约段须与本契约同步,任一处修改必须同步另一处。

**为什么 skill_root 必须显式给**:SKILL.md 内所有 references 链接形如 `[references/drafting-rules.md](references/drafting-rules.md)`（相对路径）。subagent 通过 Skill 工具加载 SKILL.md 时,Skill 平台自动处理路径基址;通过 Read 加载 SKILL.md 绝对路径时,subagent 须基于 skill_root 把相对路径推到绝对路径。skill_root 缺失时 subagent 容易猜路径,故 prompt 强制提供。

**为什么必须显式列输入产物绝对路径列表**:与 disclosure-draft / attorney-review 契约一致——subagent 不得自行猜路径,所有输入由编排器在派单 prompt 中显式枚举。

### attorney-review 派 subagent 契约（防漂移）

step 6 与 step 8 均使用 `cn-patent-attorney-review` SKILL；由 dispatch prompt 中的 `mode` 字段区分语义。

| stage | mode 值 | dispatch 数量 |
|---|---|---|
| step 6 single | `single` | 1 |
| step 6 multi (方向) | `direction-01` ~ `direction-06` | 6 并行 |
| step 6 multi (综合) | `synthesize` | 1（在 6 个方向都返回后派） |
| step 8 revision | `revision` | 1 |

详细 prompt 模板、产物路径、返回长度硬约束见：
- 6 方向 + 综合：`cn-patent-attorney-review/references/multi-agent-dispatch.md`
- revision：`cn-patent-attorney-review/references/revision-mode.md`（含输入契约「默认 4 核心 + 按需 Read」、起草侧 references trigger 表、派单前 R 规则注解一致性预审、上下文压力预算）

字段口径以两份 references 为权威；本表与 references 任一处修改必须同步另一处。
