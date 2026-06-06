#!/usr/bin/env python3
"""get-next-step.py — 编排器每步完成后调用,计算下一步路由 + 识别 handoff 分支。

调用位置:cn-patent-project-drafting 编排器每完成一步后,读 state 决定下一步。

输入:
  --state-path <path>       state 文件路径(必填,绝对或相对路径)

输出(stdout 单段 JSON):
  - 含 handoff 强制分支时:{"next_action": ..., "handoff_status": ..., "message": ...}
  - step 3 子阶段内:{"next_action": "step-3.<sub>", "step": 3}
  - 常规 step 路由:{"next_action": "step-<n>", "step": <n>, "reason": ...}
  - 已完成:{"next_action": "completed"}

退出码:
  0 = 成功
  1 = state 文件不存在 / 不可读 / JSON 解析失败

错误信息打印到 stderr,不抛 Python traceback。
"""

import argparse
import json
import sys
from pathlib import Path

# 共享 lib(spec §3.1)。lib 与本脚本同 commit 维护,真相源在 lib 中。
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from handoff import current_branch, picked_up_substage  # noqa: E402
from stage_executors import lookup as lookup_executor  # noqa: E402


# ---------- handoff 分支检测(优先级最高) ----------

def detect_handoff_branch(state: dict):
    """检测 handoff 段的强制分支。优先于普通 step 路由。

    事实层(分支判定 / picked_up 子阶段)由 lib.handoff 维护;
    本函数仅负责 next_action 名 + message 文案的编排器契约层。

    返回:
      None — 无 handoff 分支,走常规路由
      dict — 含 next_action / handoff_status / message,编排器应直接响应该分支
    """
    handoff = state.get("handoff", {}) or {}
    status = current_branch(state)

    if status == "packaged":
        return {
            "next_action": "ask_patent_dept_pickup",
            "handoff_status": status,
            "message": "检测到研发已交付(handoff-package.md 已落盘)。AskUserQuestion 三选:接手 / 研发修订 / 只读退出。",
        }

    if status == "picked_up":
        # picked_up 段四子阶段由 lib.handoff.picked_up_substage 判定
        sub = picked_up_substage(state)
        if sub == "S1_risk":
            return {
                "next_action": "ask_risk_review",
                "handoff_status": status,
                "message": "S1 风险确认。编排器列出上游产物路径 + 摘录 high/medium 风险条目,AskUserQuestion 三选:已查看进入决策 / 先离线看产物 / 风险不可接受回 step 3。",
            }
        if sub == "S2_decisions":
            return {
                "next_action": "enter_gate_a_drafting_decisions",
                "handoff_status": status,
                "message": "S2 起草前决策。读 decision-categories.json,对命中类目逐题 AskUserQuestion。",
            }
        if sub == "S3_notes":
            return {
                "next_action": "ask_notes_fill_mode",
                "handoff_status": status,
                "message": "S3 notes 填写。AskUserQuestion 四选:输入提示词 / 输入参考文档 / 手动编辑 / 暂无意见。完成后必须同时写两个 state 字段:handoff.notes_fill_mode(取值 prompt|document|manual|none,供 extract-drafting-context 决定是否把 patent-dept-notes 传给起草 subagent)+ handoff.notes_decision_at(ISO 时间,供 picked_up_substage 推进到 S4)。只写 notes_decision_at 会导致专利部强制意见漏传起草侧。",
            }
        if sub == "S4_gate_a":
            return {
                "next_action": "enter_gate_a_confirmation",
                "handoff_status": status,
                "message": "S4 Gate A 拍板。AskUserQuestion 用户拍板'确认进入起草',写入 state.gate_a.gate_a_confirmation.passed_at + state.gate_a.status=passed。",
            }
        return None  # completed → Gate A 已 passed,走常规 step 4-9 路由

    if status == "local":
        # 研发本地继续,直接进 Gate A 段(S2~S4,跳过 S1 风险确认与 S3 notes)
        gate_a = state.get("gate_a", {}) or {}
        drafting_decisions = gate_a.get("drafting_decisions", {}) or {}
        if drafting_decisions.get("status") != "completed":
            return {
                "next_action": "enter_gate_a_drafting_decisions",
                "handoff_status": status,
                "message": "研发本地继续。进 Gate A 段起草前决策。drafting_initiator = rd。",
            }
        if gate_a.get("status") != "passed":
            return {
                "next_action": "enter_gate_a_confirmation",
                "handoff_status": status,
                "message": "研发本地继续。进 Gate A 确认子阶段。",
            }
        return None

    # not_initiated / 其他 → 不干预,走常规 step 路由
    return None


# ---------- step 3 子阶段路由 ----------

def next_step_3_substage(state: dict):
    """step 3 内部四子阶段路由。返回:
    'step-3.review' / 'step-3.awaiting_user_verdict_ack' /
    'step-3.disclosure-generation' / 'step-3.inventor-review' /
    'step-3.post-disclosure-decision' / None

    None 有两种语义,调用方必须区分:
    (a) step 3 全部完成(post_disclosure_decision.choice 已设)→ 走 step-4 / Gate A
    (b) inventor_review.exit_status 已设但 gate_passed=False(rollback 路径)
        → 调用方读 inventor_review.exit_status 字段路由到 step-1 / step-2
        详见 cn-patent-disclosure-review/references/protocols.md 「rollback 处理」段
    """
    s3 = state.get("step_3", {}) or {}
    pre_draft = s3.get("pre_draft_review", {}) or {}
    disclosure = s3.get("disclosure_draft", {}) or {}
    inv = s3.get("inventor_review", {}) or {}
    post = s3.get("post_disclosure_decision", {}) or {}

    verdict = pre_draft.get("verdict")
    if not verdict:
        return "step-3.review"

    # 软门禁硬阻断:verdict ≠ go 时必须用户拍板(risk_acknowledged_source = user-confirmed)
    # 才能进入 disclosure-generation 子阶段;否则永远卡在 awaiting_user_verdict_ack
    if verdict in ("revise-recommended", "revise-required", "stop-recommended"):
        ack = pre_draft.get("risk_acknowledged", False) is True
        ack_source = pre_draft.get("risk_acknowledged_source", "")
        if not (ack and ack_source == "user-confirmed"):
            # 已完成 disclosure 不回退,只在 disclosure 未完成时阻断
            if disclosure.get("status") != "completed":
                return "step-3.awaiting_user_verdict_ack"

    if disclosure.get("status") != "completed":
        return "step-3.disclosure-generation"

    # 新增:disclosure 完成后必经 inventor_review,直到 exit_status 写入
    if not inv.get("exit_status"):
        return "step-3.inventor-review"

    # inventor_review 出口 = rollback 时,gate_passed=False,不进 post-disclosure-decision
    # 由编排器读 exit_status 字段做回滚路由(rolled_back_step_1 / rolled_back_step_2)
    if not inv.get("gate_passed"):
        return None

    if not post.get("choice"):
        return "step-3.post-disclosure-decision"
    return None  # step 3 内部全完成


# ---------- 常规 step 路由 ----------

def _has_nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def derive_current_step(state: dict) -> int:
    """从 state 字段反推当前应处于的步骤号(0–9)。

    用于在 current_stage 缺失或不规范时给出兜底判断。
    返回最早未完成步骤编号。
    """
    # step 0:env_check_path + source_material_roles 已写
    env_check = state.get("env_check_path", "")
    smr = (state.get("source_material_roles") or {}).get("items") or []
    if not _has_nonempty(env_check) or not _has_nonempty(smr):
        return 0

    # step 1:主线分析 / evidence_matrix / feature_layers / invention_points
    if not _has_nonempty(state.get("mainline_analysis_path")):
        return 1
    if not _has_nonempty(state.get("feature_layers")):
        return 1
    if not _has_nonempty(state.get("invention_points")):
        return 1

    # step 2:现有技术检索
    pas = state.get("prior_art_search") or {}
    if pas.get("status") != "completed" or not _has_nonempty(pas.get("report_path")):
        return 2
    if not _has_nonempty(state.get("claimable_invention_points")):
        return 2
    if not _has_nonempty(state.get("closest_prior_art")):
        return 2
    if not _has_nonempty(state.get("distinguishing_features")):
        return 2

    # step 3:起草前评审段 / Gate A
    gate_a = state.get("gate_a") or {}
    if gate_a.get("status") != "passed":
        return 3

    # step 4:正式稿起草
    if not _has_nonempty(state.get("current_draft_path")):
        return 4

    # step 5:风险确认
    if not _has_nonempty(state.get("figure_manifest_path")):
        return 5

    # step 6:代理师审稿
    rf = state.get("review_feedback") or {}
    if not _has_nonempty(rf.get("latest_review_notes_path")):
        return 6

    # step 7:Gate B
    if (state.get("gate_b") or {}).get("status") != "passed":
        return 7

    # step 8:修订
    if not _has_nonempty(rf.get("latest_revised_draft_path")):
        return 8

    # step 9:Gate C
    if (state.get("gate_c") or {}).get("status") != "passed":
        return 9

    return 10  # 全部完成


def parse_stage_to_step(stage: str) -> int:
    """把 current_stage 字符串解析成 step 编号;无法解析返回 -1。"""
    if not stage or not isinstance(stage, str):
        return -1
    s = stage.strip().lower()
    # 兼容 'step-0' / 'step-3.review' / 'step-3'
    if s.startswith("step-"):
        rest = s[len("step-"):]
        head = rest.split(".", 1)[0].split("-", 1)[0]
        try:
            return int(head)
        except ValueError:
            return -1
    return -1


def regular_route(state: dict) -> dict:
    """常规 step 路由(handoff 分支未命中后调用)。"""
    declared = parse_stage_to_step(state.get("current_stage", ""))
    derived = derive_current_step(state)
    # 取两者较小的作为下一步(即:实际未完成的最早步骤)
    if declared >= 0:
        cur = min(declared, derived)
    else:
        cur = derived

    if cur >= 10:
        return {"next_action": "completed", "step": 10, "reason": "全部步骤已完成"}

    # step 3 内细化子阶段
    if cur == 3:
        sub = next_step_3_substage(state)
        if sub is not None:
            return {"next_action": sub, "step": 3}
        # 注意:next_step_3_substage 返回 None 有双义:
        # (a) step-3 全完成 → 等 gate_a.status 写入 passed,正向推进
        # (b) inventor_review 选择回滚 → 编排器须读 inventor_review.exit_status 字段
        #     ('rolled_back_step_1' / 'rolled_back_step_2'),按 cn-patent-disclosure-review
        #     references/protocols.md 「rollback 处理」段执行 reset,改 current_stage 后回退
        return {
            "next_action": "step-3.awaiting_gate_a_passed",
            "step": 3,
            "reason": "step_3 内部四子阶段已完成,等待 gate_a.status 写入 passed",
        }

    return {"next_action": f"step-{cur}", "step": cur}


# ---------- step 6 review_mode 选择阻断 ----------

def check_review_mode_decided(state: dict):
    """step 6 进入前必须先选 review_mode (single/multi)。

    返回 None 表示已选定 mode,可正常路由;否则返回阻断 dict。
    仅当 next_step == 6(尚未审稿)时需要检查;step 6 已完成(review_feedback 已写)则跳过。
    """
    rf = state.get("review_feedback", {}) or {}
    if _has_nonempty(rf.get("latest_review_notes_path")):
        return None  # step 6 已完成,不阻断
    s6 = state.get("step_6", {}) or {}
    mode = s6.get("review_mode")
    if mode in ("single", "multi"):
        return None
    return {
        "next_action": "step-6.awaiting_review_mode",
        "step": 6,
        "message": "进入代理师审稿前必须选 review_mode (single/multi)。编排器 AskUserQuestion + 写入 state.step_6.review_mode + state.step_6.review_mode_selected_at(伪产物 reviews/review-mode-selection.md 已废,改 state 字段)。",
    }


# ---------- step 产物完整性校验 ----------

# 每步完成后必产物路径(相对 patent_root,即 state.json 父目录的父目录);
# step→files 映射真相源在 lib/paths.py 的 DELIVERABLES_BY_STEP（state-machine-reference.md 摘要）。
# {slug} 占位符会替换成 state_path 推算出的 patent-slug。
# STEP_DELIVERABLES 真相源已迁至 lib/paths.py(spec §3.1 + Task 2)。
# 此处保留兼容层:沿用旧 mixed key 结构,但 5 个伪产物 key 全废:
#   - "gate_a" / "gate_b" / "gate_c" (Gate 包伪产物)
#   - 5 (step-5-pre-review-risk-package 伪产物)
#   - "step_6_review_mode_selection" (review-mode-selection.md 伪产物)
# 这些场景改由 state.gate_{a,b,c}.* / state.review_feedback.pre_review_risk_acknowledged /
# state.step_6.review_mode 字段判定。
from paths import DELIVERABLES_BY_STEP, STEP_6_MULTI_DELIVERABLES  # noqa: E402

STEP_DELIVERABLES = {
    1: DELIVERABLES_BY_STEP[1],
    2: DELIVERABLES_BY_STEP[2],
    3: DELIVERABLES_BY_STEP[3],
    4: DELIVERABLES_BY_STEP[4],
    6: DELIVERABLES_BY_STEP[6],
    "step_6_multi": STEP_6_MULTI_DELIVERABLES,
    8: DELIVERABLES_BY_STEP[8],
}


def validate_prior_step_deliverables(state: dict, state_path: Path, next_step: int):
    """检查 next_step 之前的所有 step 必产物是否齐全;缺失则返回阻断 dict,否则 None。
    只检查 step < next_step 的产物;Gate A/B/C 在对应 status=passed 后才校验。
    """
    patent_root = state_path.parent.parent  # state.json 在 patent/<slug>/state/ 下
    missing = []

    # 普通 step 产物
    for step_no in range(1, next_step):
        for rel in STEP_DELIVERABLES.get(step_no, []):
            if not (patent_root / rel).exists():
                missing.append(f"step {step_no}: {rel}")

    # Gate A/B/C 拍板状态改由 state.gate_*.status 字段记录(伪产物已废,spec §3.7)
    # 此处不再校验 gates/gate-{a,b,c}-confirmation-package.md 文件存在性。

    # step 8 user-feedback.md 仍是真产物,仅在 gate_b passed 后必产
    if (state.get("gate_b") or {}).get("status") == "passed" and next_step > 8:
        for rel in STEP_DELIVERABLES[8]:
            if not (patent_root / rel).exists():
                missing.append(f"step 8: {rel}")

    # step 6 review-mode-selection.md 已废(spec §3.7),mode 选择由 state.step_6.review_mode 校验
    # (旧 legacy skip 逻辑同步删除,改走 state 字段)

    # step 6 multi 模式 7 份方向子文件必齐全(真产物,保留)
    s6 = state.get("step_6") or {}
    if s6.get("review_mode") == "multi" and next_step > 6:
        for rel in STEP_DELIVERABLES["step_6_multi"]:
            if not (patent_root / rel).exists():
                missing.append(f"step 6 (multi): {rel}")

    if not missing:
        return None
    return {
        "next_action": "missing_prior_deliverables",
        "blocking": True,
        "missing": missing,
        "message": "上游 step 必产物缺失,不得推进下一步;真产物路径表见 lib/paths.py。",
    }


# ---------- 核心计算(被 main() 和 validate-stage exit chain 共用) ----------

def compute_next_action(state: dict, state_path: Path) -> dict:
    """计算 next_action,返回完整 result dict(含 executor / must_load 注入)。

    本函数被两处调用:
    - get-next-step.py CLI 入口(main 函数)
    - validate-stage.py exit chain(避免编排器跑完 exit 就漏掉下一步)

    返回 dict 一定含 next_action 字段;如能查到 executor 元数据(从 stage_executors.py),
    会在 dict 中合并 executor / type / must_load / do_not_merge_user_questions / ... 字段。
    """
    # 检测 handoff 强制分支(优先)
    branch = detect_handoff_branch(state)
    if branch is not None:
        return _inject_executor(branch)

    # 走常规 step 路由
    result = regular_route(state)

    # step 6 进入前必须先选 review_mode (single/multi)
    if result.get("step") == 6 and result.get("next_action") == "step-6":
        mode_block = check_review_mode_decided(state)
        if mode_block is not None:
            return _inject_executor(mode_block)

    # step 8 进入前必须确认 revision subagent 已派单 (gate_b passed 后才生效)
    if result.get("step") == 8 and (state.get("gate_b") or {}).get("status") == "passed":
        s8 = state.get("step_8", {}) or {}
        if not s8.get("revision_subagent_dispatched", False):
            return _inject_executor({
                "next_action": "step-8.awaiting_revision_subagent",
                "step": 8,
                "message": "step 8 修订必须派 revision subagent 执行 (mode=revision),主 agent 不得直接 Edit。派单后在 state 写入 step_8.revision_subagent_dispatched=true。",
            })

    # 产物完整性校验:阻断式;若上游缺产物则覆盖 result 为 missing 分支
    next_step = result.get("step", 99) if isinstance(result, dict) else 99
    block = validate_prior_step_deliverables(state, state_path, next_step)
    if block is not None:
        block["original_route"] = result  # 保留原路由,便于排错
        return _inject_executor(block)

    return _inject_executor(result)


def _inject_executor(result: dict) -> dict:
    """按 result["next_action"] 注入 executor 元数据。"""
    if not isinstance(result, dict):
        return result
    action = result.get("next_action")
    if not action or action == "completed":
        return result
    info = lookup_executor(action)
    # 只注入 executor / type / must_load / do_not_merge / ask_template_count 等核心字段,
    # stage_executors 内部的"choices/tools/stage_param"等保留以便编排器查
    result["executor_info"] = info
    return result


# ---------- main ----------

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--state-path", required=True, help="state 文件路径")
    args = p.parse_args()

    state_path = Path(args.state_path)
    if not state_path.exists():
        print(f"ERROR: state file not found: {state_path}", file=sys.stderr)
        return 1
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError as e:
        print(f"ERROR: cannot read state file {state_path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: state file unparseable {state_path}: {e}", file=sys.stderr)
        return 1

    result = compute_next_action(state, state_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
