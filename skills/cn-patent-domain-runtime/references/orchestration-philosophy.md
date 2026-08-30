# 编排器协作哲学（为什么）

> Windows 原生环境：命令中的 `python3` 请用 `python` 或 `py` 代替。

本文件回答"为什么这样编排"。字段表 / Gate 通过条件 / handoff 子阶段判定 等机械规则全部下沉到 `scripts/lib/`，并由 `scripts/domain-runtime.py` 统一暴露，本文档不重复。

需要查"现在是否满足某 stage 的前置/出口" → 调脚本。本文档只解释"为什么有这些 stage、Gate、handoff 段"。

## 启动顺序

1. 确认用户项目工作目录。`patent/<patent-slug>/` 必须创建在用户项目工作目录下，禁止创建在 skill 目录下。
2. 若用户从 `cn-patent-repo-scout` 进入，先确认扫描交接文件路径（通常为 `patent/repo-scout/directions/<direction-slug>/source-material-roles.json`）；该文件已是交接结构，不得手工二次转换。
3. 查找 `patent/<patent-slug>/state/patent-iteration-state.json`。
4. 状态文件不存在时，从 step 0 开始；可将已确认的扫描交接文件复制为 `patent/<patent-slug>/source-material-roles.json`，再交给初始化脚本导入 `source_material_roles`。step 0.3 资料角色确认细则详见 [source-materials.md](source-materials.md)。
5. 状态文件存在时，只能从状态文件中最近通过的 Gate 或 `current_stage` 对应的合法 stage 继续。
6. 进入任一 stage 前，宿主 Agent 必须跑 `scripts/domain-runtime.py validate --stage <S> --mode enter`，`ok=false` 即停下来补料或 AskUserQuestion。
7. 每个 stage 的出口动作必须**按顺序**完成：
   - 跑 `scripts/domain-runtime.py validate --stage <S> --mode exit`，`ok=false` 则补派或追问；
   - **exit 通过后**：宿主 Agent 调 `scripts/domain-runtime.py transition --from-stage <S> --to-stage <T>`，由 Runtime 在锁内复核并原子更新 `state.current_stage`；禁止宿主直接改该字段；
   - `step-0` 出口额外把 `env-check.json` 的 `warnings` 数组在对话中 echo 一次（字体、缺工具等下游阶段才会触发的提示，让用户提前知情）；
   - 按 Runtime 响应中的 `next_action` / `executor_info` 推进下一 stage。

**为什么先 env-check 再 state-init**：env-check 决定 PDF/Word/LaTeX 工具是否就绪；state-init 必须把这些能力写入 `env_check_path` 字段，否则后续 subagent 拿不到能力矩阵。两者**串行不并行**——能力快照是状态文件的前置事实。

## 全局防护规则

- **资料纪律**：项目目录先只读；资料不足不得输出正式稿或"看起来完整"的低质量稿；用户声明的原创/核心/论文/代码/交底内容只作为发明证据；参考样稿只借风格不作来源判断；自主补强不得伪装成项目证据
- **环境纪律**：脚本失败不得静默跳过；step 1 前必须初始化状态文件；PDF 存在时必先跑提取能力检查；`../cn-patent-docx-export/references/专利附图生成后端.md` 不可读时阻断
- **门禁纪律**：前置确认包 ≠ 用户确认；用户说"继续"但没确认具体事项 ≠ Gate 通过；保护路径候选只完整发散一次，冻结后仅筛选收紧
- **入口纪律**：编排器不扫描项目或推荐方向，无方向时停下并提示 `cn-patent-repo-scout`；从扫描进入时只复制 `source-material-roles.json`，不得二次改写角色映射，也不得视扫描结果为 Gate A 通过

## N0 子 agent 分派纪律（为什么硬纪律）

所有产出型阶段（step 1 / step 2 / step 3 评审 / step 3 技术交底书 / step 4 正式稿 / step 6 代理师审稿）必须经由 `Agent(subagent_type=general-purpose)` 派 subagent 执行。**为什么**：

- **上下文隔离**：子 skill SKILL.md + references 总长可达 ~1000 行，宿主 Agent只关心状态机和 Gate 拍板。混在主上下文里读子 skill 资料是上下文污染，导致状态机判断漂移。
- **产物纪律**：subagent 直接 Write 落盘到用户项目根目录，写到磁盘的内容**不返回**给宿主 Agent。返回的是 ≤600 字摘要 + 路径。
- **可追溯性**：派单 prompt 显式列出已确认事实（用户决策、verdict、关键技术口径、上游产物路径），subagent 不得自行猜测。

宿主 Agent 只做：专业结果回写、用户交互、脚本调用、Gate 拍板、verdict 分支、风险登记同步；流程控制字段通过 Runtime 迁移接口提交。具体派单契约见 [agent-tool-mapping.md](agent-tool-mapping.md)。

### 为什么 step 4 起草派单前必跑 `extract-drafting-context.py`

state.json 全量约 26 KB（含 history / open_questions / glossary 等大量起草无关字段），但 step 4 正式稿起草只需 Gate A 决策子树 + handoff 标志子树 + pre-review oneliner。把这些预提取为 `drafting-context.json`（~3 KB）后，起草 subagent 入场上下文从约 205 KB 降到约 110 KB（spec 2026-05-26 D9 决策）。

派单前 hook 是**编排器的硬纪律**，不是起草侧的可选项：

- 编排器在调 Agent 工具派 subagent **之前**必跑 `scripts/extract-drafting-context.py`，将 `drafting-context.json` 输出路径作为 4 份必读输入之一显式写进 prompt
- subagent 收到 prompt 后只读 4 份必读（含 `drafting-context.json`），不得自行 Read state.json 全量
- 把 state.json 中"未来字段会扩张"的部分（如 history / glossary / open_questions）隔离在 context 之外，避免起草 subagent 因看了无关字段而产生噪声

具体派单契约见 [agent-tool-mapping.md § formal-drafting 派 subagent 契约（防漂移）](agent-tool-mapping.md#formal-drafting-派-subagent-契约防漂移)。

## Gate 哲学

### 为什么 Gate A 段独立于 step 3 和 step 4

step 3 完成时，技术交底书只是技术版描述；起草前还需用户拍板 7 类策略决策（C1~C7）+ 主线 + 保护客体 + 题目。这些**写在权要核心里、写错只能整稿重来**。Gate A 段（起草前决策子阶段 + 确认子阶段）就是这个拍板窗口。

入口 A：专利部接手 → handoff.status=picked_up 后进入，drafting_initiator=patent_dept
入口 B：研发本地继续 → step_3.post_disclosure_decision.choice=continue_locally 后进入，drafting_initiator=rd

Gate A 到达后禁止：生成正式稿、冻结推荐保护路径、写独立权利要求定稿。`selected_mainline` / `selected_protection_object` 只能在 Gate A 确认子阶段由用户拍板后写入。

### Gate B 哲学

代理师审稿意见 + 用户反馈必须双方就位才能修订。**为什么**：避免 agent 看到审稿意见就自主修订，绕过用户授权范围；用户反馈文件（`reviews/user-feedback.md`）就是授权契约。

### Gate C 哲学

质量检查通过 + 用户授权交付才允许导出 DOCX。**为什么**：质量检查是机器的事实判断，用户授权是商业决策。两者不能合并。

## Gate 停点展示规则

到达 Gate 停下来等待用户确认前，必须在对话中条列输出每个相关产物的一句话说明和完整相对路径。不得只写"请确认"而不列路径。**为什么**：用户拍板前看不到上下文等于盲签字，是审计风险。

## verdict 四档分支（软闸门）

step 3 评审完成后，编排器读 `step_3.pre_draft_review.verdict` 按四档分支：

| verdict | 默认建议 | 用户可选项 |
|---|---|---|
| go | 自动进入技术交底书子阶段 | 无需用户确认 |
| revise-recommended | 列出补证清单 + 风险摘要；建议补料 | (a) 补料后回 step 1 / step 2 重跑；(b) 明示授权带风险走 |
| revise-required | 列出多维度问题；强烈建议补料 | (a) 补料；(b) 明示授权带风险走，需用户额外回复确认句"我已知悉风险并坚持继续" |
| stop-recommended | 显示"不建议起草"报告；建议放弃或转分案 | (a) 放弃当前 slug；(b) 调整主线回 step 1；(c) 二次确认后强行继续，需填 override_stop_reason |

用户授权语句模板（**为什么严格**：revise-required / stop-recommended 是评审认为"创新性可能不成立"，严格的授权语句让用户每次都重新意识到风险）：

- revise-recommended → 任意肯定回复（"继续"、"知道了走吧" 等）
- revise-required → 严格匹配"我已知悉风险并坚持继续"
- stop-recommended → 严格匹配"我已知悉创新性风险，理由是 <reason>"；reason 写入 `override_stop_reason`

授权后编排器把 `risk_acknowledged = true` / `_at` / `_source = "user-confirmed"` 写入 state；非合法语句视为用户选择补料。

## handoff 段组织语义

handoff 段是**研发→专利部门交接**的硬隔离。研发输出技术交底书 + 上游产物，专利部门接手后做 Gate A 段决策。两边人员、口径、决策权完全不同。

handoff_status 状态机 + S1~S4 子阶段判定全部封装在 `scripts/lib/handoff.py`，编排器调脚本不内嵌逻辑。**为什么下沉**：原 prose 描述四五处分散，状态机改一处要找四五处同步，漂移高发。

handoff 段三类 user 入口（按 status 分支 AskUserQuestion）：

- `not_initiated`：常规 step 0~3
- `packaged`：AskUserQuestion 三选（接手/研发修订/只读）
- `picked_up`：按 `lib.handoff.picked_up_substage(state)` 返回的 S1~S4 子阶段接续
- `local`：研发本地继续，直接进 Gate A 段（不问 notes）

### picked_up 段 S1~S4 子阶段语义

- **S1 风险确认**：编排器列上游产物相对路径 + risk_inputs 中 severity ∈ {high, medium} 条目，AskUserQuestion 三选。**为什么**：专利部门接手第一动作是"看完上游产物再决策"，不是直接编辑。
- **S2 C1~C7 决策**：按 `assets/decision-categories.json` 命中即问。决策类目元数据 + 写入字段都在 JSON 里，prose 不重复。
- **S3 notes 填写**：四选 + 暂停。**为什么**：patent-dept-notes.md 是专利部门强制意见，下游正式稿起草可覆盖 drafting_decisions / 风险处理建议、追加章节/实施例/从权/附图/术语。它是 Gate A 后修订的最强意见来源。
- **S4 Gate A 确认**：AskUserQuestion 拍板"确认进入起草" → `gate_a.status = passed`。

## 审稿前风险与 Gate B/修订复核哲学

### 审稿前风险确认（step 5）

审稿前补改只处理用户已确认或授权的明显缺口；不得当作代理师意见驱动的正式修订。**为什么**：把"审稿后才该解决的问题"提前在审稿前修，会绕开代理师审查这一环节，等于自审。

不算已确认的情形（红旗）：

- agent 认为风险点不严重 → 用户必须明示
- 用户只回复"继续"但未对风险点逐项表态
- 风险点只在正式稿末尾列了，state 未写入 `review_feedback.pre_review_risk_acknowledged*`

### Gate B 硬门禁哲学

代理师修改意见只是 **输入**，不是 **通过凭证**。**为什么**：审稿意见是事实判断（哪里有问题），用户反馈是商业决策（哪些必须改、哪些可不改、哪些带风险走）。两者分离才有 Gate B 的意义。

不算 Gate B 通过的情形：

- 只完成代理师自评审或子 agent 审查（没用户反馈）
- 用户只说"继续"但未确认审稿方向、补证范围、授权修改范围
- agent 自己选所有修改项直接修订（绕过用户决策）
- 一次审稿后直接进 Gate C（跳过 step 8 修订环节）
- 修改完成后没给用户复核就进 Gate C

### 修订后复核与回退哲学

每轮反馈驱动的修订完成后**必须**先进入用户复核；不得把"已经修完"当作"用户已接受"。**为什么**：修订是 agent 解释用户反馈后的产物，可能误解了用户意图，必须给用户兜底验收的机会。

复核后状态处理：

- 用户明确认可 → 由 Runtime transition 推进到 `gate-c`
- 用户要求局部继续修改 → 保持 `step-8`，进入下一轮
- 用户否定关键修改或要求重审 → 当前修订稿**不得**作为交付基础，回退 `attorney-review`，记 `rollback_reason`，重新开 `history.attorney_review_rounds` 轮次

**质量检查通过不能替代用户复核**。这是两个正交维度：质量检查看的是结构与硬规则，用户复核看的是"修对了没"。

## 跳步红旗

出现以下想法时必须停止并回滚：

- "先生成一版正式稿，后面再补检索/证据/Gate。"
- "reference 大概知道内容，不读也能写。"
- "有联网能力，但先按仅初筛进入 Gate A。"
- "Gate 前置包写完了，可以不等用户确认继续。"
- "step 1/2/3/4/6 直接主 agent 读源码+直接 Write 产物就好，不用派 subagent。" → 违反 N0 子 agent 分派纪律
- "主 agent 顺手把 evidence-matrix.md / mainline-analysis.md / prior-art-search-report.md / disclosure-draft.md / formal draft 几行几行 Edit 补一下。" → 违反 N0；除非用户明示是单点修订（1~2 处措辞）

## 历史兼容策略

旧 state（缺新字段）走 `new-iteration-state.py --migrate-from <old.json>`：

- 旧 5 处伪产物路径字段（`gate_*.confirmation_package_path` / `review_feedback.pre_review_*_path` / `step_6.review_mode_selection`）**保留**字段名兼容旧 state 读取，但 prose / scripts 不再描述落盘语义。
- 新字段（`pre_review_risk_acknowledged{,_at,_items[]}` / `step_6.review_mode{,_selected_at}`）由 `--migrate-from` 自动补 null/默认值，由编排器逐步写入。
- 自动质量检查脚本（`automated_quality_check.py`）仍读旧字段以兼容，新字段优先。

## 质量检查入口

仅在 step 9 运行：

```bash
python3 scripts/automated_quality_check.py --draft-path patent/<patent-slug>/drafts/markdown/<draft-name>.md --state-path patent/<patent-slug>/state/patent-iteration-state.json
```

## 自主迭代闭环

step 7 Gate B 通过后，agent 自动循环：按代理师意见和用户授权范围修订 → 更新状态 → 运行质量检查 → 能自修的修 → 不能自决的写入 blocking_questions → 达标时准备 Gate C。
