"""handoff.py — handoff 状态机封装。

状态: not_initiated → {packaged, local} → packaged → picked_up(终态)
picked_up 段子阶段: S1 风险确认 → S2 C1-C7 决策 → S3 notes 填写 → S4 Gate A 拍板
"""
from __future__ import annotations

from typing import List


def current_branch(state: dict) -> str:
    """读 state.handoff.status,缺省返回 not_initiated。"""
    return (state.get("handoff") or {}).get("status", "not_initiated")


_LEGAL = {
    "not_initiated": ["packaged", "local"],
    "packaged": ["picked_up"],
    "local": [],  # local 起草分支,不进 handoff 状态机
    "picked_up": [],  # 终态;picked_up 后子阶段进展由 picked_up_substage 反映
}


def legal_transitions(current: str) -> List[str]:
    """返回 current 状态下合法的下一状态列表。未知状态返回 []。"""
    return _LEGAL.get(current, [])


def picked_up_substage(state: dict) -> str:
    """按字段顺序判定 picked_up 段子阶段: S1 → S2 → S3 → S4 → completed。

    判定顺序(必须自上而下,跳序异常应在外层 validate-stage 报告):
    - S1: gate_a.risk_review.acknowledged_at 未填
    - S2: gate_a.drafting_decisions.status != completed
    - S3: handoff.notes_decision_at 未填
    - S4: gate_a.status != passed
    - completed: 全部已完成
    """
    gate_a = state.get("gate_a") or {}
    handoff = state.get("handoff") or {}

    risk = gate_a.get("risk_review") or {}
    if not risk.get("acknowledged_at"):
        return "S1_risk"
    if (gate_a.get("drafting_decisions") or {}).get("status") != "completed":
        return "S2_decisions"
    if not handoff.get("notes_decision_at"):
        return "S3_notes"
    if gate_a.get("status") != "passed":
        return "S4_gate_a"
    return "completed"
