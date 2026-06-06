"""preconditions.py — stage 前置/出口条件断言。

类 A 15 项走 enter/exit,类 B 9 项走简化校验(只看上一阶段产物 + 用户响应已写 state)。
spec §3.5/§3.6 为唯一真相源。字段命名锁定 2026-05-25。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple


@dataclass
class StateField:
    """state 字段谓词。
    - non_empty: bool → 对应 JSON Schema type:string + minLength:1
    - min_items: int → 对应 JSON Schema minItems
    - equals:    Any → 对应 JSON Schema const
    """
    field: str  # 点号路径,如 "step_3.pre_draft_review.verdict"
    non_empty: bool = False
    min_items: int = 0
    equals: Any = None

    def check(self, state: dict) -> Tuple[bool, str]:
        val = _get_dotted(state, self.field)
        if self.non_empty and not _is_nonempty(val):
            return False, f"state.{self.field} empty"
        if self.min_items and (not isinstance(val, (list, dict)) or len(val) < self.min_items):
            return False, f"state.{self.field} < {self.min_items} items"
        if self.equals is not None and val != self.equals:
            return False, f"state.{self.field} != {self.equals!r}"
        return True, ""


@dataclass
class DeliverableExists:
    """文件存在性谓词。对应 JSON Schema 自定义 format:path_exists。"""
    relpath: str

    def check(self, patent_root: Path) -> Tuple[bool, str]:
        if not (Path(patent_root) / self.relpath).exists():
            return False, f"missing file {self.relpath}"
        return True, ""


@dataclass
class CoversTracks:
    """检查 list-of-dicts 字段覆盖给定 track 集合。

    每条记录视为「覆盖某 track」的判定：
    - 实际成功调用：track 命中 + error 为空（hits_count 不限，0 命中也算 OK）
    - 显式 Skip：track 命中 + skipped=True + skip_reason 非空
    """
    field: str          # list-of-dicts 的点号路径，如 "prior_art_search.paths_attempted"
    required_tracks: list[str]  # 必须覆盖的 track 名称列表

    def check(self, state: dict) -> Tuple[bool, str]:
        entries = _get_dotted(state, self.field) or []
        if not isinstance(entries, list):
            return False, f"state.{self.field} not a list"
        for tr in self.required_tracks:
            ok = False
            for e in entries:
                if not isinstance(e, dict) or e.get("track") != tr:
                    continue
                if e.get("skipped"):
                    if e.get("skip_reason"):
                        ok = True
                        break
                else:
                    if not e.get("error"):
                        ok = True
                        break
            if not ok:
                return False, f"track '{tr}' not covered in {self.field}"
        return True, ""


def _get_dotted(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _is_nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    if isinstance(v, bool):
        return v
    return True


# ---------------------------------------------------------------------------
# 类 A:15 个实质阶段(enter / exit 条件)
# ---------------------------------------------------------------------------
STAGE_PRECONDITIONS_A = {
    "step-0": {
        "enter": [],
        "exit": [
            StateField("env_check_path", non_empty=True),
            StateField("source_material_roles.items", min_items=1),
        ],
    },
    "step-1": {
        "enter": [
            StateField("env_check_path", non_empty=True),
            StateField("source_material_roles.items", min_items=1),
        ],
        "exit": [
            DeliverableExists("evidence/evidence-matrix.md"),
            DeliverableExists("analysis/mainline-analysis.md"),
            StateField("invention_points", min_items=1),
            StateField("feature_layers", min_items=1),
        ],
    },
    "step-2": {
        "enter": [
            StateField("source_material_roles.items", min_items=1),
            StateField("selected_direction.title", non_empty=True),
            DeliverableExists("evidence/evidence-matrix.md"),
            DeliverableExists("analysis/mainline-analysis.md"),
            StateField("protection_path_candidates", min_items=1),
            StateField("invention_points", min_items=1),
            StateField("protection_object", non_empty=True),
            StateField("feature_layers", min_items=1),
        ],
        "exit": [
            DeliverableExists("evidence/prior-art-search-report.md"),
            StateField("prior_art_search.status", equals="completed"),
            StateField("claimable_invention_points", min_items=1),
            StateField("closest_prior_art", non_empty=True),
            StateField("distinguishing_features", min_items=1),
            # 新增断言（A 类升级 Task 3）
            StateField("prior_art_search.ipc_classifications.primary", min_items=1),
            StateField("prior_art_search.target_assignees", min_items=1),
            CoversTracks("prior_art_search.paths_attempted",
                         required_tracks=["chinese-patent", "english-patent", "vendor", "paper", "standard"]),
        ],
    },
    "step-3.review": {
        "enter": [
            StateField("prior_art_search.status", equals="completed"),
        ],
        "exit": [
            DeliverableExists("reviews/pre-draft-review.md"),
            StateField("step_3.pre_draft_review.verdict", non_empty=True),
        ],
    },
    "step-3.disclosure-generation": {
        "enter": [
            StateField("step_3.pre_draft_review.verdict", non_empty=True),
        ],
        "exit": [
            DeliverableExists("disclosure/disclosure-draft.md"),
            StateField("step_3.disclosure_draft.status", equals="completed"),
        ],
    },
    "step-3.inventor-review": {
        "enter": [
            DeliverableExists("disclosure/disclosure-draft.md"),
            StateField("step_3.disclosure_draft.status", equals="completed"),
        ],
        "exit": [
            # 改动 8(2026-05-27): skill_loaded_at 由 cn-patent-disclosure-review SKILL.md
            # 入口动作写入,exit 校验依赖该字段防止编排器自编合并问题绕过 3 段独立 AskUserQuestion。
            StateField("step_3.inventor_review.skill_loaded_at", non_empty=True),
            StateField("step_3.inventor_review.exit_status", non_empty=True),
            StateField("step_3.inventor_review.stage_1_status", non_empty=True),
            StateField("step_3.inventor_review.stage_2_status", non_empty=True),
            StateField("step_3.inventor_review.stage_3_status", non_empty=True),
        ],
    },
    "step-3.post-disclosure-decision": {
        "enter": [
            StateField("step_3.disclosure_draft.status", equals="completed"),
            StateField("step_3.inventor_review.gate_passed", equals=True),
        ],
        "exit": [
            StateField("step_3.post_disclosure_decision.choice", non_empty=True),
        ],
    },
    "gate-a.drafting-decisions": {
        "enter": [
            StateField("step_3.status", equals="completed"),
        ],
        "exit": [
            StateField("gate_a.drafting_decisions.status", equals="completed"),
            # 改动 10(2026-05-27): categories_asked 记录走过 AskUserQuestion 的类目 ID 列表;
            # 编排器每答完一题 append 一项,空 list 视为"凭直觉跳过所有类目题",exit 拒绝。
            StateField("gate_a.drafting_decisions.categories_asked", min_items=1),
            StateField("selected_title", non_empty=True),
            StateField("selected_mainline", non_empty=True),
            StateField("selected_protection_object", non_empty=True),
        ],
    },
    "gate-a.confirmation": {
        "enter": [
            StateField("gate_a.drafting_decisions.status", equals="completed"),
        ],
        "exit": [
            StateField("gate_a.status", equals="passed"),
        ],
    },
    "step-4": {
        "enter": [
            StateField("gate_a.status", equals="passed"),
        ],
        "exit": [
            StateField("current_draft_path", non_empty=True),
            StateField("figure_manifest_path", non_empty=True),
        ],
    },
    "step-5": {
        "enter": [
            StateField("current_draft_path", non_empty=True),
        ],
        "exit": [
            # 字段命名锁定 2026-05-25(spec §3.7 + §5)
            StateField("review_feedback.pre_review_risk_acknowledged", equals=True),
        ],
    },
    "step-6": {
        "enter": [
            StateField("review_feedback.pre_review_risk_acknowledged", equals=True),
            StateField("step_6.review_mode", non_empty=True),  # single/multi
        ],
        "exit": [
            DeliverableExists("reviews/attorney-review.md"),
            StateField("review_feedback.latest_review_notes_path", non_empty=True),
        ],
    },
    "gate-b": {
        "enter": [
            StateField("review_feedback.latest_review_notes_path", non_empty=True),
        ],
        "exit": [
            StateField("gate_b.status", equals="passed"),
        ],
    },
    "step-8": {
        "enter": [
            StateField("gate_b.status", equals="passed"),
            StateField("step_8.revision_subagent_dispatched", equals=True),
        ],
        "exit": [
            DeliverableExists("reviews/user-feedback.md"),
            StateField("review_feedback.latest_revised_draft_path", non_empty=True),
        ],
    },
    "gate-c": {
        "enter": [
            StateField("review_feedback.latest_revised_draft_path", non_empty=True),
        ],
        "exit": [
            StateField("gate_c.status", equals="passed"),
        ],
    },
}


# ---------------------------------------------------------------------------
# 类 B:9 个等待状态(只校验"上一阶段产物 + 用户响应已写 state",无独立 exit 条件)
# ---------------------------------------------------------------------------
STAGE_AWAITING_CHECKS_B = {
    "step-3.awaiting_user_verdict_ack": [
        StateField("step_3.pre_draft_review.verdict", non_empty=True),
        StateField("step_3.pre_draft_review.risk_acknowledged", equals=True),
        StateField("step_3.pre_draft_review.risk_acknowledged_source", equals="user-confirmed"),
    ],
    "step-3.awaiting_gate_a_passed": [
        StateField("step_3.post_disclosure_decision.choice", non_empty=True),
    ],
    "step-6.awaiting_review_mode": [
        StateField("step_6.review_mode", non_empty=True),
    ],
    "step-8.awaiting_revision_subagent": [
        StateField("step_8.revision_subagent_dispatched", equals=True),
    ],
    "ask_patent_dept_pickup": [
        StateField("handoff.status", equals="packaged"),
    ],
    "ask_risk_review": [
        StateField("handoff.status", equals="picked_up"),
        # 改动 9(2026-05-27): S1 风险确认完成时编排器必写 gate_a.risk_review.acknowledged_at
        # (ISO 时间戳;真相源与 lib/handoff.py picked_up_substage 判定字段一致)。
        # 该字段为 picked_up_substage 从 S1 推进到 S2 的硬条件,防止跳过 S1 直接进 Gate A 段决策。
        StateField("gate_a.risk_review.acknowledged_at", non_empty=True),
    ],
    "ask_notes_fill_mode": [
        StateField("handoff.status", equals="picked_up"),
        StateField("gate_a.drafting_decisions.status", equals="completed"),
    ],
    "enter_gate_a_drafting_decisions": [
        StateField("step_3.status", equals="completed"),
    ],
    "enter_gate_a_confirmation": [
        StateField("gate_a.drafting_decisions.status", equals="completed"),
    ],
}


def check_stage(stage: str, mode: str, state: dict, patent_root: Path) -> dict:
    """主入口: result ∈ {ok, blocked, warned},含 passed/missing/blocked/warnings 列表。

    类 A 走 STAGE_PRECONDITIONS_A[stage][mode];类 B 不区分 mode,直接走 STAGE_AWAITING_CHECKS_B。
    未知 stage → result=blocked。
    """
    passed, missing, blocked, warnings = [], [], [], []

    if stage in STAGE_PRECONDITIONS_A:
        checks = STAGE_PRECONDITIONS_A[stage].get(mode, [])
    elif stage in STAGE_AWAITING_CHECKS_B:
        checks = STAGE_AWAITING_CHECKS_B[stage]  # 类 B 不区分 enter/exit
    else:
        return {
            "stage": stage,
            "mode": mode,
            "result": "blocked",
            "passed": [],
            "missing": [{"unknown_stage": stage}],
            "blocked": [],
            "warnings": [],
        }

    for c in checks:
        if isinstance(c, StateField):
            ok, detail = c.check(state)
            target = passed if ok else missing
            target.append({"field": c.field, "detail": detail or "ok"})
        elif isinstance(c, DeliverableExists):
            ok, detail = c.check(patent_root)
            target = passed if ok else missing
            target.append({"deliverable": c.relpath, "detail": detail or "ok"})
        elif isinstance(c, CoversTracks):
            ok, detail = c.check(state)
            target = passed if ok else missing
            target.append({"covers_tracks": c.field, "required_tracks": c.required_tracks, "detail": detail or "ok"})

    if missing or blocked:
        result = "blocked"
    elif warnings:
        result = "warned"
    else:
        result = "ok"

    return {
        "stage": stage,
        "mode": mode,
        "result": result,
        "passed": passed,
        "missing": missing,
        "blocked": blocked,
        "warnings": warnings,
    }
