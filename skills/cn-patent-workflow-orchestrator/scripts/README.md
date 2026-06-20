# cn-patent-workflow-orchestrator / scripts

编排器使用的脚本索引。所有脚本由编排器在固定位置调用，不应由用户直接运行（除调试外）。

| 脚本 | 调用位置 | 作用 |
|---|---|---|
| `patent-env-check.py` | step 0 环境预检 | 检查可读取的资料格式 + 工具就绪度 |
| `new-iteration-state.py` | step 0 状态初始化 | 创建/重置 patent-iteration-state.json；旧 state 升级走 `--migrate-from <old.json>`，自动补新字段（`pre_review_risk_acknowledged*` / `step_6.review_mode*`），不种回 5 处 legacy 伪产物路径 |
| `validate-stage.py` | 进入/退出每个 stage 时 | 14 类 A 实质阶段 + 9 类 B 等待状态全覆盖；调用 `lib.preconditions.check_stage`；输出 JSON `{result, passed[], missing[], blocked[], warnings[], next_suggested_action}`；退出码 0 = 校验完成，非零 = 工具错误 |
| `get-next-step.py` | 每步完成后 | 计算下一步，识别 handoff 状态分支，5 个伪产物路径已删除 |
| `handoff-package.py` | step 3 用户分流决策选"交付专利部"时 | 渲染 handoff-package.md + 切 packaged 状态 |
| `handoff-pickup.py` | 启动后检测 handoff.status == packaged，用户确认接手时 | 切 picked_up + drafting_initiator=patent_dept |
| `extract-drafting-context.py` | step 4 派 formal-drafting subagent 前 | 从 state.json 抽 Gate A / handoff / pre_review 三个子树写 `drafting-context.json`（~3 KB），起草 subagent 不再读 state.json 全量 |
| `automated_quality_check.py` | step 9 Gate C | 质量检查 |
| `extract-reference-text.py` | 按需 | 取 reference 文档片段（辅助 agent） |
| `test-latex-formula-readiness.py` | step 0 环境预检 | LaTeX 渲染能力检查 |
| `test-pdf-extraction-readiness.py` | step 0 环境预检 | PDF 提取能力检查 |

## 共享库 `scripts/lib/`

| 模块 | 作用 |
|---|---|
| `lib/state_io.py` | state 文件读写 + `patent_root_from_state_path()` 推算 |
| `lib/paths.py` | `DELIVERABLES_BY_STEP` 产物路径表（真相源；5 处伪产物已删） |
| `lib/preconditions.py` | 14 类 A 实质阶段 + 9 类 B 等待状态前置/出口断言，`check_stage()` 主入口 |
| `lib/handoff.py` | handoff 状态机：`current_branch` / `legal_transitions` / `picked_up_substage`（S1~S4） |

新增 stage 或字段断言时改 `lib/preconditions.py`；产物路径变化改 `lib/paths.py`。prose（reference 文档）不再维护这些字段表。

## handoff 段脚本契约

`handoff-package.py` 和 `handoff-pickup.py` 都接受 `--slug <slug> --state-path <path>` 参数，执行前校验 state 前置状态，执行后更新 state 文件并打印 OK 行到 stdout。脚本不向 state 之外写入（handoff-package.py 额外写 handoff-package.md；handoff-pickup.py 只更新 state）。

退出码：
- 0 = 成功
- 1 = state 文件不存在 / 不可读 / JSON 解析失败
- 2 = state 前置状态不满足（如 disclosure_draft 未 completed / handoff.status != packaged）

错误信息打印到 stderr，不抛 Python traceback（契约：orchestrator 只看 exit code + 一行 stderr）。

