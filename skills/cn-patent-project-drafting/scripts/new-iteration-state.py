#!/usr/bin/env python3
"""Initialize patent iteration state JSON from template."""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def get_material_use_policy(role: str) -> dict:
    role_lower = role.lower()
    if re.search(r'参考样稿|格式样稿|样稿|reference sample|template|style', role_lower):
        return {"use_as": "format_style_only", "invention_evidence": False, "prior_art_source": False, "requires_confirmation": False}
    if re.search(r'原创|核心|论文|代码|技术交底|原始|核心算法|核心算法实现|original|core|paper|code|technical disclosure|disclosure|core_algorithm|core_data|benchmark|experiment', role_lower):
        return {"use_as": "invention_evidence", "invention_evidence": True, "prior_art_source": False, "requires_confirmation": False}
    if re.search(r'现有技术|参考文献|prior art|literature|citation', role_lower):
        return {"use_as": "prior_art_reference", "invention_evidence": False, "prior_art_source": True, "requires_confirmation": False}
    return {"use_as": "unclassified_requires_confirmation", "invention_evidence": False, "prior_art_source": False, "requires_confirmation": True}


def normalize_material_roles(raw) -> list:
    if raw is None:
        return []
    items = raw
    default_declared_by = "user"
    if isinstance(raw, dict):
        direction = raw.get("selected_direction") if isinstance(raw.get("selected_direction"), dict) else {}
        if direction.get("source") == "repo-scout-confirmed":
            default_declared_by = "cn-patent-repo-scout/user-confirmed"
        elif raw.get("direction_slug") and raw.get("status") in ("confirmed", "user_selected"):
            default_declared_by = "cn-patent-repo-scout/user-confirmed"
        source_roles = raw.get("source_material_roles")
        if isinstance(source_roles, dict):
            source_roles = source_roles.get("items")
        items = (
            raw.get("items")
            or raw.get("material_roles")
            or raw.get("materials")  # legacy repo-scout schema (pre-2026-05)
            or source_roles
            or [raw]
        )
    if not isinstance(items, list):
        items = [items]

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or item.get("file") or item.get("source") or item.get("name") or ""
        role = item.get("role") or item.get("declared_role") or item.get("material_role") or item.get("type") or ""
        declared_by = item.get("declaredBy") or item.get("declared_by") or item.get("source_user") or default_declared_by
        notes = item.get("notes") or item.get("note") or item.get("description") or ""
        if not path and not role:
            continue
        policy = get_material_use_policy(role)
        requires_confirmation = item.get("requires_confirmation", policy["requires_confirmation"])
        if not isinstance(requires_confirmation, bool):
            requires_confirmation = policy["requires_confirmation"]
        normalized.append({
            "path": path, "declared_role": role, "declared_by": declared_by,
            "use_as": policy["use_as"], "invention_evidence": policy["invention_evidence"],
            "prior_art_source": policy["prior_art_source"], "requires_confirmation": requires_confirmation,
            "notes": notes,
        })
    return normalized


def normalize_selected_direction(raw, material_roles_path: str = "") -> dict:
    direction = {}
    if isinstance(raw, dict):
        if isinstance(raw.get("selected_direction"), dict):
            direction = raw["selected_direction"]
        elif raw.get("direction_slug"):
            # legacy repo-scout schema (pre-2026-05): 平铺 direction_slug/title/summary/status
            legacy_status = raw.get("status", "")
            direction = {
                "source": (
                    "repo-scout-confirmed"
                    if legacy_status in ("confirmed", "user_selected")
                    else ""  # 未确认方向不伪造 source
                ),
                "slug": raw.get("direction_slug", ""),
                "title": raw.get("title", ""),
                "summary": raw.get("summary", ""),
                "source_material_roles_path": material_roles_path,
            }
    return {
        "source": direction.get("source", ""),
        "slug": direction.get("slug", ""),
        "title": direction.get("title", ""),
        "summary": direction.get("summary", ""),
        "source_material_roles_path": direction.get("source_material_roles_path") or material_roles_path,
    }


def escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")


def write_evidence_file(path: str, items: list):
    lines = [
        "# Source Material Roles", "",
        "Records user-declared source-material roles at project start. Original, core, paper, code, and technical-disclosure materials are invention evidence only; reference samples are format/style sources only and are not automatic invention, prior-art, or reference-literature sources.", "",
        "| Path | Declared role | Use as | Invention evidence | Prior-art/reference source | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        cols = [
            escape_pipe(item["path"]),
            escape_pipe(item["declared_role"]),
            item["use_as"],
            str(item["invention_evidence"]),
            str(item["prior_art_source"]),
            escape_pipe(item["notes"]),
        ]
        lines.append("| " + " | ".join(cols) + " |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    print("[new-iteration-state] Material roles written to: " + path)


def default_execution_checklist_path(output_path: Path, project_root: Path) -> str:
    """Deprecated. Kept only for backward compatibility with older state files;
    no longer written by main(). The execution-checklist artifact has been
    replaced by env-check.json + this state file."""
    return ""


def main():
    parser = argparse.ArgumentParser(description="Initialize patent iteration state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-path", default="patent/<patent-slug>/state/patent-iteration-state.json")
    parser.add_argument("--project-name", default="")
    parser.add_argument("--material-roles-path", default="")
    parser.add_argument("--material-roles-json", default="")
    parser.add_argument("--material-roles-evidence-path", default="")
    parser.add_argument("--skip-material-roles-evidence", action="store_true")
    parser.add_argument(
        "--migrate-from",
        default="",
        help="旧 state JSON 路径。提供时:读旧 state,补缺新字段(spec §5 历史兼容映射),透传旧字段,写入 --output-path。",
    )
    parser.add_argument("--env-check-path", default="",
                        help="Path to env-check.json produced by patent-env-check.py "
                             "(written into state.env_check_path so step-1 can verify "
                             "step-0 was completed).")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    template_path = script_dir / ".." / "assets" / "patent-iteration-state.template.json"
    if not template_path.exists():
        print("ERROR: Template not found: " + str(template_path.resolve()), file=sys.stderr)
        sys.exit(1)

    state = json.loads(template_path.read_text(encoding="utf-8"))

    # --migrate-from: 用旧 state 作为基底,template 作为新字段补全(spec §5 历史兼容)
    migrate_report = []  # 收集 null 字段供报告
    if args.migrate_from:
        old_state_path = Path(args.migrate_from)
        if not old_state_path.exists():
            print(f"ERROR: --migrate-from file not found: {old_state_path}", file=sys.stderr)
            sys.exit(1)
        old_state = json.loads(old_state_path.read_text(encoding="utf-8"))
        # template 字段作为默认值;旧字段透传保留
        merged = dict(state)  # template 副本
        merged.update(old_state)  # 旧字段覆盖
        # review_feedback 子树深合并:template 默认 + 旧字段透传 + 锁定新字段推断
        old_rf = old_state.get("review_feedback", {}) or {}
        new_rf = dict(state.get("review_feedback", {}) or {})  # template 默认(含新字段)
        new_rf.update(old_rf)  # 旧字段透传(含 legacy path 兼容)
        # 旧 pre_review_risk_package_path 非空 → 旧已确认 → acknowledged=True
        old_risk_path = old_rf.get("pre_review_risk_package_path") or ""
        if old_risk_path and not new_rf.get("pre_review_risk_acknowledged"):
            new_rf["pre_review_risk_acknowledged"] = True
            migrate_report.append(
                f"review_feedback.pre_review_risk_acknowledged = True "
                f"(由旧 pre_review_risk_package_path = {old_risk_path!r} 推断)"
            )
        if new_rf.get("pre_review_risk_acknowledged_at") is None:
            migrate_report.append("review_feedback.pre_review_risk_acknowledged_at = null (旧 state 无该字段,migrate 透传 null)")
        if not new_rf.get("pre_review_risk_acknowledged_items"):
            migrate_report.append("review_feedback.pre_review_risk_acknowledged_items = [] (旧 state 无该字段,下一次审稿可补)")
        merged["review_feedback"] = new_rf

        # step_6 补 review_mode 字段(若旧无)
        old_s6 = old_state.get("step_6") or {}
        if "review_mode" not in old_s6:
            merged.setdefault("step_6", {})
            merged["step_6"]["review_mode"] = None
            merged["step_6"]["review_mode_selected_at"] = None
            migrate_report.append("step_6.review_mode = null (旧 state 无,migrate 透传 null)")

        # prior_art_search 子树补新字段（IPC / target_assignees / paths_attempted）
        old_pas = old_state.get("prior_art_search") or {}
        new_pas = dict(state.get("prior_art_search", {}))  # template 默认
        new_pas.update(old_pas)  # 旧字段透传
        merged["prior_art_search"] = new_pas
        if "ipc_classifications" not in old_pas:
            migrate_report.append("prior_art_search.ipc_classifications = {primary:[],secondary:[]} (旧 state 无,迁移后留空待检索阶段填写)")
        if "target_assignees" not in old_pas:
            migrate_report.append("prior_art_search.target_assignees = [] (旧 state 无,迁移后留空待检索阶段填写)")
        if "paths_attempted" not in old_pas:
            migrate_report.append("prior_art_search.paths_attempted = [] (旧 state 无,迁移后留空待检索阶段填写)")

        # step_3.inventor_review 子树补全(旧 state 无此字段时透传默认值)
        old_s3 = old_state.get("step_3") or {}
        if "inventor_review" not in old_s3:
            merged.setdefault("step_3", {})
            merged["step_3"]["inventor_review"] = {
                "round_count": 0,
                "stage_1_status": None,
                "stage_1_feedback": None,
                "stage_2_status": None,
                "stage_2_feedback": None,
                "stage_3_status": None,
                "stage_3_feedback": None,
                "exit_status": None,
                "gate_passed": False,
            }
            migrate_report.append(
                "step_3.inventor_review = <默认空子树> "
                "(旧 state 无该字段,migrate 透传默认值)"
            )

        # 兼容 cleanup(2026-05-26):删除已废字段
        obsolete_inv_fields = ["stage_0_status", "stage_0_feedback",
                                "disclosure_review_passed",
                                "escalation_choice", "escalation_record_path"]
        existing_inv = old_s3.get("inventor_review") or {}
        removed = [k for k in obsolete_inv_fields if k in existing_inv]
        if removed:
            merged_inv = merged["step_3"].get("inventor_review") or {}
            for k in obsolete_inv_fields:
                merged_inv.pop(k, None)
            merged["step_3"]["inventor_review"] = merged_inv
            migrate_report.append(
                f"step_3.inventor_review: 已废字段 {removed} 删除 "
                "(2026-05-26 cleanup,信息归入 exit_status / stage_X_feedback)"
            )

        # 兼容(2026-05-27):旧 state 已通过 inventor-review 但 stage_X_status 为空时补 approved,
        # 避免新增的 stage_X_status non_empty 断言误拦既往项目。
        merged_inv2 = merged.get("step_3", {}).get("inventor_review") or {}
        if merged_inv2.get("exit_status") in ("approved", "accepted_with_dissent") and merged_inv2.get("gate_passed"):
            for k in ("stage_1_status", "stage_2_status", "stage_3_status"):
                if not merged_inv2.get(k):
                    merged_inv2[k] = "approved"
            merged["step_3"]["inventor_review"] = merged_inv2

        state = merged
        # 显式报告 stderr,不静默
        if migrate_report:
            print("--- migrate-from 字段补全报告 ---", file=sys.stderr)
            for line in migrate_report:
                print(f"  • {line}", file=sys.stderr)
            print("--------------------------------", file=sys.stderr)

    output = Path(args.output_path)
    resolved_root = Path(args.project_root).resolve()
    state["project_root"] = "."
    state["project_name"] = args.project_name if args.project_name else resolved_root.name
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if args.env_check_path:
        env_check_resolved = Path(args.env_check_path)
        try:
            env_check_str = str(env_check_resolved.resolve().relative_to(resolved_root.resolve()))
        except ValueError:
            env_check_str = str(env_check_resolved)
        state["env_check_path"] = env_check_str
    else:
        state.setdefault("env_check_path", "patent/<patent-slug>/state/env-check.json")

    state.setdefault("evidence_matrix_path", "patent/<patent-slug>/evidence/evidence-matrix.md")
    state.setdefault("mainline_analysis_path", "patent/<patent-slug>/analysis/mainline-analysis.md")
    state.setdefault("protection_path_candidates", [])
    state.setdefault("feature_layers", [])
    state.setdefault("invention_points", [])
    state.setdefault("claimable_invention_points", [])
    state.setdefault("current_draft_path", "")
    state.setdefault("figure_generation_plan_path", "")
    state.setdefault("figure_manifest_path", "")

    # step_3 子树(由 template 提供;此处兜底以兼容旧 template)
    step_3 = state.setdefault("step_3", {})
    step_3.setdefault("stage", "pending")
    step_3.setdefault("status", "pending")
    step_3.setdefault("pre_draft_review", {
        "verdict": None,
        "decision_readiness": None,
        "risk_acknowledged": False,
        "report_path": None,
        "risk_inputs": [],
        "chain_check": {"status": "pending", "broken_items": []},
        "proposal_summary_oneliner": None,
    })
    step_3.setdefault("disclosure_draft", {
        "status": "pending",
        "draft_path": None,
    })
    step_3.setdefault("post_disclosure_decision", {
        "choice": None,
        "revise_count": 0,
    })
    step_3.setdefault("inventor_review", {
        "round_count": 0,
        "stage_1_status": None,
        "stage_1_feedback": None,
        "stage_2_status": None,
        "stage_2_feedback": None,
        "stage_3_status": None,
        "stage_3_feedback": None,
        "exit_status": None,
        "gate_passed": False,
    })

    gate_a = state.setdefault("gate_a", {})
    gate_a.setdefault("stage", "pending")
    gate_a.setdefault("status", "pending")
    gate_a.setdefault("drafting_decisions", {"status": "pending", "categories": {}})
    gate_a.setdefault("gate_a_confirmation", {"user_confirmation": None, "passed_at": None})
    # gate_a.confirmation_package_path 字段已废(伪产物 gate-a-confirmation-package.md
    # 已删除,spec §3.7);新建 state 不再种该字段。--migrate-from 不破坏旧 state 字段。

    # handoff 段(由 template 提供;此处兜底)
    handoff = state.setdefault("handoff", {})
    handoff.setdefault("status", "not_initiated")
    handoff.setdefault("package_path", None)
    handoff.setdefault("patent_dept_notes_path", None)
    handoff.setdefault("drafting_initiator", None)
    handoff.setdefault("packaged_at", None)
    handoff.setdefault("picked_up_at", None)
    handoff.setdefault("notes_decision_at", None)

    # gate_b.confirmation_package_path / gate_c.confirmation_package_path 字段已废
    state.setdefault("gate_b", {})
    state.setdefault("gate_c", {})

    # review_feedback 子树:审稿前风险确认字段(锁定 2026-05-25 命名)
    review_feedback = state.setdefault("review_feedback", {})
    # 旧 pre_review_risk_package_path / pre_review_confirmation_path 字段已废
    review_feedback.setdefault("pre_review_risk_acknowledged", False)
    review_feedback.setdefault("pre_review_risk_acknowledged_at", None)
    review_feedback.setdefault("pre_review_risk_acknowledged_items", [])

    if args.material_roles_path and args.material_roles_json:
        print("ERROR: Use either --material-roles-path or --material-roles-json, not both.", file=sys.stderr)
        sys.exit(1)

    raw_roles = None
    if args.material_roles_path:
        raw_roles = json.loads(Path(args.material_roles_path).read_text(encoding="utf-8"))
    elif args.material_roles_json:
        raw_roles = json.loads(args.material_roles_json)

    role_items = normalize_material_roles(raw_roles)
    state["selected_direction"] = normalize_selected_direction(raw_roles, args.material_roles_path)
    if "source_material_roles" not in state:
        state["source_material_roles"] = {"declared_at": "", "role_policy": "User-declared original/core/paper/code/technical-disclosure materials are invention evidence only; reference samples are format/style sources only and are not automatic invention, prior-art, or reference-literature sources.", "items": []}
    state["source_material_roles"]["declared_at"] = state["updated_at"] if role_items else ""
    state["source_material_roles"]["items"] = role_items

    if role_items and args.material_roles_evidence_path and not args.skip_material_roles_evidence:
        write_evidence_file(args.material_roles_evidence_path, role_items)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[new-iteration-state] Output written to: " + str(output))


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
