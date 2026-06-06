"""paths.py — patent_root 下各 step 产物相对路径表。

唯一真相源,prose 中不再维护。5 个伪产物已废除:
- gates/gate-a-confirmation-package.md
- gates/gate-b-confirmation-package.md
- gates/gate-c-confirmation-package.md
- gates/step-5-pre-review-risk-package.md
- reviews/review-mode-selection.md
"""
from pathlib import Path


# step-3 子阶段 inventor-review 的未解决项不再单独生成 .md 文件;
# accept_with_dissent 时未解决项保留在 state.step_3.inventor_review.stage_X_feedback,
# 由 handoff S1 风险确认环节读取并入风险清单(见 references/state-machine-reference.md)。

DELIVERABLES_BY_STEP = {
    1: ["analysis/mainline-analysis.md", "evidence/evidence-matrix.md"],
    2: ["evidence/prior-art-search-report.md"],
    3: ["reviews/pre-draft-review.md", "disclosure/disclosure-draft.md"],
    4: [],  # step 4 的产物路径在 state.current_draft_path,通过 state 字段维护
    5: [],  # 伪产物 step-5-pre-review-risk-package.md 已废,改 state 字段
    6: ["reviews/attorney-review.md"],
    8: ["reviews/user-feedback.md"],
    9: ["quality/"],
}

# multi 模式 step 6 产物(6 个方向子审稿,真产物)。
# 与 DELIVERABLES_BY_STEP[6] 区分:single 模式只产 attorney-review.md,
# multi 模式额外产 6 份子审稿,二者由 state.step_6.review_mode 决定。
# 方向命名与数量以 cn-patent-attorney-review/references/multi-agent-dispatch.md 为权威。
STEP_6_MULTI_DELIVERABLES = [
    "reviews/attorney-review/01-quality-aura.md",
    "reviews/attorney-review/02-claims.md",
    "reviews/attorney-review/03-spec-support.md",
    "reviews/attorney-review/04-form-evidence.md",
    "reviews/attorney-review/05-language-style.md",
    "reviews/attorney-review/06-legal-compliance.md",
]

# Gate 产物全部废除(5 个伪产物)。Gate A/B/C 拍板状态改由 state 字段记录:
# - state.gate_a.* / state.gate_b.* / state.gate_c.*
# - state.review_feedback.pre_review_risk_acknowledged_*
# - state.step_6.review_mode
GATE_DELIVERABLES: dict = {}


def deliverable_path(patent_root, step, idx: int = 0) -> Path:
    """返回 patent_root + DELIVERABLES_BY_STEP[step][idx] 的绝对路径。"""
    return Path(patent_root) / DELIVERABLES_BY_STEP[step][idx]
