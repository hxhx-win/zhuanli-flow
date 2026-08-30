#!/usr/bin/env python3
"""extract-drafting-context.py — step 4 正式稿起草派单前调用,
从 patent-iteration-state.json 提取起草所需子树写入 drafting-context.json。

调用位置:cn-patent-domain-runtime 编排器在 step 4 派 formal-drafting subagent 前。
schema 与字段口径见 docs/superpowers/specs/2026-05-26-formal-drafting-skill-refactor-design.md 附录 C。

输入:
  --state-path <path>    state 绝对路径(必填)
  --patent-slug <slug>   方向标识(必填,写入产物字段)
  --output-path <path>   drafting-context.json 输出绝对路径(可选;默认与 state 同目录)

输出:
  drafting-context.json (~3 KB,UTF-8)

依赖:cn-patent-domain-runtime/scripts/lib/state_io.load_state。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"


def extract_drafting_decisions(state: dict) -> dict:
    """从 state.gate_a.drafting_decisions.categories 提取每个类目的 answer/answers 子字段。

    state 中 categories 形如 {C1_title: {label, hit_rule, answer, ...}, ...}。
    drafting-context 只保留 {C1_title: {answer: <value>}}(单选) 或
    {C5_*: {answers: [...]}}(多答),丢弃 label / hit_rule / candidate 等 metadata。
    """
    cats = state.get("gate_a", {}).get("drafting_decisions", {}).get("categories", {}) or {}
    out = {}
    for key, val in cats.items():
        if not isinstance(val, dict):
            continue
        if "answers" in val:
            out[key] = {"answers": val["answers"]}
        elif "answer" in val:
            out[key] = {"answer": val["answer"]}
        else:
            out[key] = {"answer": None}
    return out


def resolve_against_project_root(state_path: Path, rel: str):
    """state 文件位于 <project_root>/patent/<slug>/state/<file>.json;
    handoff 中相对路径形如 patent/<slug>/reviews/patent-dept-notes.md,基址是 project_root。
    None / 空串 → 返回 None;绝对路径 → 原样返回字符串。
    """
    if not rel:
        return None
    p = Path(rel)
    if p.is_absolute():
        return str(p)
    project_root = state_path.parent.parent.parent.parent
    return str((project_root / p).resolve())


def build_context(state: dict, slug: str, state_path: Path) -> dict:
    patent_root = state_path.parent.parent  # patent/<slug>

    gate_a_state = state.get("gate_a", {}) or {}
    handoff_state = state.get("handoff", {}) or {}
    pre_draft = state.get("step_3", {}).get("pre_draft_review", {}) or {}

    risk_inputs_path = str((patent_root / "reviews" / "pre-draft-review.md").resolve())
    notes_path_abs = resolve_against_project_root(state_path, handoff_state.get("patent_dept_notes_path"))

    return {
        "schema_version": SCHEMA_VERSION,
        "patent_slug": slug,
        "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate_a": {
            "status": gate_a_state.get("status"),
            "selected_title": state.get("selected_title"),
            "selected_mainline": state.get("selected_mainline"),
            "selected_protection_object": state.get("selected_protection_object"),
            "claimable_invention_points": state.get("claimable_invention_points", []),
            "distinguishing_features": state.get("distinguishing_features", []),
            "drafting_decisions": extract_drafting_decisions(state),
        },
        "handoff": {
            "drafting_initiator": handoff_state.get("drafting_initiator"),
            "notes_fill_mode": handoff_state.get("notes_fill_mode"),
            "patent_dept_notes_path": notes_path_abs,
        },
        "pre_review": {
            "risk_inputs_path": risk_inputs_path,
            "oneliner": pre_draft.get("proposal_summary_oneliner"),
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--state-path", required=True, help="state JSON 绝对路径")
    p.add_argument("--patent-slug", required=True, help="方向标识")
    p.add_argument("--output-path", default=None, help="可选;默认与 state 同目录 drafting-context.json")
    args = p.parse_args()

    state_path = Path(args.state_path)
    if not state_path.exists():
        print(f"ERROR: state file not found: {state_path}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(Path(__file__).parent / "lib"))
    from state_io import load_state  # noqa: E402

    try:
        state = load_state(state_path)
    except OSError as e:
        print(f"ERROR: cannot read state file {state_path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: state file unparseable {state_path}: {e}", file=sys.stderr)
        return 1

    gate_status = (state.get("gate_a") or {}).get("status")
    if gate_status not in ("passed", "confirmed", "approved"):
        print(
            f"WARN: gate_a.status = {gate_status!r} 未到通过态;仍生成 drafting-context.json,"
            "但起草 subagent 应检查此字段并停下来。",
            file=sys.stderr,
        )

    ctx = build_context(state, args.patent_slug, state_path)

    out_path = Path(args.output_path) if args.output_path else state_path.parent / "drafting-context.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(ctx, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    size = out_path.stat().st_size
    print(f"OK: wrote {out_path} ({size} bytes)")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
