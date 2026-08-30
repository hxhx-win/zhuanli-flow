"""stage_executors.py — 24 个 stage 的执行者元数据集中表。

真相源迁移自 `references/agent-tool-mapping.md § 全阶段执行者映射表`。该 md 现退为人读 doc。

字段说明（统一映射后的 schema，所有 entry 共用）:
  executor:                          执行者标识(skill slug / "orchestrator")
  type:                              "subagent" | "main_run_skill" | "main_agent_ask_user" |
                                     "main_agent_bash" | "main_agent_bash_then_ask_user" | "main_agent_route"
  must_load:                         数组,主 agent 进入该 stage 前必读的文件绝对路径
  ask_user_question_template_count:  应跑几次 AskUserQuestion(默认 1,主跑型多档协议会 >1)
  do_not_merge_user_questions:       True 时编排器禁止把多档合并成一道综合题
  must_write_state_on_load:          主跑型 skill 加载时必写的 state 字段(由 exit 校验回扣)
  stage_param:                       同一 skill 多 stage 时,派单 prompt 的 stage 字段值
  must_run_before_dispatch:          派 subagent 前必跑的脚本名
  choices:                           AskUserQuestion 合法答案枚举(供编排器/校验对照)
  do_not_skip_after_inventor_review: 防止"凭直觉判流程结束"漏掉该 stage
  must_write_state_on_confirm:       AskUserQuestion 答完后必写的 timestamp 字段
  tools:                             "main_agent_bash" 类型主跑时必调的脚本清单

未列字段视为默认值(False / [] / None / 1)。lookup() 返回时会合并默认值。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


ORCHESTRATOR_SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ORCHESTRATOR_SKILL_ROOT.parent


def _skill_path(skill_name: str, *parts: str) -> str:
    """返回基于当前安装位置解析的 Skill 内绝对路径。"""
    return str(SKILLS_ROOT.joinpath(skill_name, *parts))


# ---------------------------------------------------------------------------
# 默认值合并(只对未填字段补默认,不覆盖已填字段)
# ---------------------------------------------------------------------------
_DEFAULTS: Dict[str, Any] = {
    "must_load": [],
    "ask_user_question_template_count": 1,
    "do_not_merge_user_questions": False,
    "must_write_state_on_load": None,
    "must_write_state_on_confirm": None,
    "stage_param": None,
    "must_run_before_dispatch": None,
    "choices": [],
    "do_not_skip_after_inventor_review": False,
    "tools": [],
}


# ---------------------------------------------------------------------------
# 24 个 stage(15 类 A + 9 类 B,字段命名锁定 2026-05-25 + 2026-05-27 补强)
# ---------------------------------------------------------------------------
STAGE_EXECUTORS: Dict[str, Dict[str, Any]] = {
    # ===== 类 A 15 项 =====
    "step-0": {
        "executor": "orchestrator",
        "type": "main_agent_bash",
        "tools": ["patent-env-check.py", "new-iteration-state.py"],
    },
    "step-1": {
        "executor": "cn-patent-mainline-analysis",
        "type": "subagent",
    },
    "step-2": {
        "executor": "cn-patent-prior-art-search",
        "type": "subagent",
    },
    "step-3.review": {
        "executor": "cn-patent-disclosure-draft",
        "type": "subagent",
        "stage_param": "review",
    },
    "step-3.disclosure-generation": {
        "executor": "cn-patent-disclosure-draft",
        "type": "subagent",
        "stage_param": "disclosure-generation",
    },
    "step-3.inventor-review": {
        "executor": "cn-patent-disclosure-review",
        "type": "main_run_skill",
        "must_load": [
            _skill_path("cn-patent-disclosure-review", "SKILL.md"),
            _skill_path("cn-patent-disclosure-review", "references", "protocols.md"),
        ],
        "ask_user_question_template_count": 3,
        "do_not_merge_user_questions": True,
        "must_write_state_on_load": "step_3.inventor_review.skill_loaded_at",
    },
    "step-3.post-disclosure-decision": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
        "do_not_skip_after_inventor_review": True,
        "choices": [
            "continue_locally",
            "hand_off_to_patent_dept",
            "revise_disclosure",
            "adjust_mainline",
            "pause",
        ],
    },
    "gate-a.drafting-decisions": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
        "must_load": [
            _skill_path("cn-patent-workflow-orchestrator", "assets", "decision-categories.json"),
            _skill_path("cn-patent-workflow-orchestrator", "references", "drafting-decisions.md"),
        ],
        "do_not_merge_user_questions": True,
    },
    "gate-a.confirmation": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
    },
    "step-4": {
        "executor": "cn-patent-formal-drafting",
        "type": "subagent",
        "must_run_before_dispatch": "extract-drafting-context.py",
    },
    "step-5": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
    },
    "step-6": {
        "executor": "cn-patent-attorney-review",
        "type": "subagent",
    },
    "gate-b": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
    },
    "step-8": {
        "executor": "cn-patent-attorney-review",
        "type": "subagent",
        "stage_param": "revision",
    },
    "gate-c": {
        "executor": "orchestrator",
        "type": "main_agent_bash_then_ask_user",
        "tools": ["automated_quality_check.py"],
    },
    # ===== 类 B 9 项 =====
    "step-3.awaiting_user_verdict_ack": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
    },
    "step-3.awaiting_gate_a_passed": {
        "executor": "orchestrator",
        "type": "main_agent_route",
    },
    "step-6.awaiting_review_mode": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
        "choices": ["single", "multi"],
    },
    "step-8.awaiting_revision_subagent": {
        "executor": "orchestrator",
        "type": "main_agent_route",
    },
    "ask_patent_dept_pickup": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
        "choices": ["accept", "request_revise", "readonly"],
    },
    "ask_risk_review": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
        # 真相源与 lib/handoff.py picked_up_substage 一致
        "must_write_state_on_confirm": "gate_a.risk_review.acknowledged_at",
        "choices": ["proceed", "review_offline", "rollback_step_3"],
    },
    "ask_notes_fill_mode": {
        "executor": "orchestrator",
        "type": "main_agent_ask_user",
        "choices": ["prompt", "document", "manual", "none"],
    },
    "enter_gate_a_drafting_decisions": {
        "executor": "orchestrator",
        "type": "main_agent_route",
    },
    "enter_gate_a_confirmation": {
        "executor": "orchestrator",
        "type": "main_agent_route",
    },
}


def lookup(stage: str) -> Dict[str, Any]:
    """查 stage 的执行者元数据,未列字段补默认值。

    返回:
      含 stage / executor / type / must_load / ... 等完整字段的 dict;
      未知 stage 返回 {"stage": stage, "executor": "unknown", "type": "unknown"}
    """
    if stage not in STAGE_EXECUTORS:
        return {"stage": stage, "executor": "unknown", "type": "unknown"}
    entry = STAGE_EXECUTORS[stage]
    merged = {"stage": stage}
    merged.update(_DEFAULTS)
    merged.update(entry)
    return merged


# ---------------------------------------------------------------------------
# 与 preconditions.py 对齐自检(module load 时跑)
# ---------------------------------------------------------------------------
def _assert_aligned_with_preconditions() -> None:
    """STAGE_EXECUTORS 必须覆盖 preconditions.py 的 24 项,不多不少。

    新增 stage 时改两处(preconditions.py + 本文件),自检会立即报错防止漂移。
    """
    from preconditions import STAGE_PRECONDITIONS_A, STAGE_AWAITING_CHECKS_B  # noqa: WPS433
    all_stages = set(STAGE_PRECONDITIONS_A.keys()) | set(STAGE_AWAITING_CHECKS_B.keys())
    executor_stages = set(STAGE_EXECUTORS.keys())
    missing_in_executors = all_stages - executor_stages
    extra_in_executors = executor_stages - all_stages
    msgs = []
    if missing_in_executors:
        msgs.append(f"STAGE_EXECUTORS 缺少 stage: {sorted(missing_in_executors)}")
    if extra_in_executors:
        msgs.append(f"STAGE_EXECUTORS 多余 stage(不在 preconditions 中): {sorted(extra_in_executors)}")
    if msgs:
        raise AssertionError("[stage_executors.py] 与 preconditions.py 不对齐:\n  " + "\n  ".join(msgs))


_assert_aligned_with_preconditions()
