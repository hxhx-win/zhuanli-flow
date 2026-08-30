#!/usr/bin/env python3
"""Automated quality check for patent Markdown drafts."""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def parse_markdown_sections(text):
    """Parse markdown into list of {level, title, body} dicts."""
    sections = []
    current_title, current_level = "", 0
    buffer = []
    for line in text.split('\n'):
        m = re.match(r'^(#{1,6})\s*(.+?)\s*$', line)
        if m:
            if current_title:
                sections.append({
                    "level": current_level,
                    "title": current_title,
                    "body": "\n".join(buffer).strip()
                })
            current_level = len(m.group(1))
            current_title = m.group(2).strip()
            buffer = []
        else:
            buffer.append(line)
    if current_title:
        sections.append({
            "level": current_level,
            "title": current_title,
            "body": "\n".join(buffer).strip()
        })
    return sections


def get_section_body(sections, title):
    for s in sections:
        if s["title"] == title:
            return s["body"]
    return ""


def get_markdown_region(text, heading, include_same_level=False):
    """Return text under a markdown heading until next heading of same/higher level."""
    pattern = re.compile(rf'(?m)^(#+)\s*{re.escape(heading)}\s*$')
    m = pattern.search(text)
    if not m:
        return ""
    level = len(m.group(1))
    start = m.end()
    stop_level = level - 1 if include_same_level else level
    next_heading = re.compile(rf'(?m)^#{{1,{stop_level}}}\s+.+$')
    n = next_heading.search(text, start)
    end = n.start() if n else len(text)
    return text[start:end].strip()


def has_section_title(sections, titles):
    """Return True if any of the given titles exists in sections."""
    title_set = set(titles)
    return any(s["title"] in title_set for s in sections)


def get_first_nonempty_line(text):
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def get_anchor_keywords(text):
    if not text:
        return []
    normalized = re.sub(r'[，。；：、（）()\[\]<>《》,.;:/\\-]', '|', text)
    normalized = re.sub(r'一种|基于|用于|面向|的|及|和|与|方法|系统|装置|设备|介质|存储介质', '|', normalized)
    tokens = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]{2,16}', normalized)
    return list(dict.fromkeys(tokens))[:8]


def get_claim_numbers(sections):
    numbers = []
    for s in sections:
        m = re.match(r'^权利要求\s*([0-9]+)$', s["title"])
        if m:
            numbers.append(int(m.group(1)))
    if numbers:
        return numbers
    claim_body = get_section_body(sections, "权利要求书")
    for m in re.finditer(r'(?m)^\s*([0-9]+)[\.、]\s+', claim_body):
        numbers.append(int(m.group(1)))
    return numbers


def is_placeholder(value):
    """Detect placeholder / unfilled values."""
    if not value or not str(value).strip():
        return True
    return bool(re.search(r'填写|待补充|TODO|TBD|\[可替换\]|\[填写', str(value)))


def test_passed(status):
    """Return True if status string represents a passed/approved state."""
    if not status:
        return False
    return status.strip().lower() in (
        "approved", "confirmed", "passed", "complete", "completed",
        "ok", "frozen", "accepted", "authorized"
    )


def get_markdown_table_rows(text):
    """Parse markdown table rows; skip separator rows. Returns list of cell lists."""
    rows = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        if re.match(r'^\|\s*-+', stripped):
            continue
        parts = stripped.split('|')
        # Remove first and last empty elements from leading/trailing |
        parts = parts[1:-1] if len(parts) >= 2 else parts
        cells = [p.strip() for p in parts]
        if cells:
            rows.append(cells)
    return rows


def escape_markdown_table_cell(value):
    """Escape pipe characters and newlines for use in a markdown table cell."""
    if value is None:
        return ""
    return str(value).replace('|', r'\|').replace('\r\n', '<br>').replace('\n', '<br>')


def get_meaningful_item_count(items):
    """Count non-empty, non-placeholder items."""
    count = 0
    for item in (items or []):
        if item is None:
            continue
        text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        if text.strip() and not is_placeholder(text):
            count += 1
    return count


def join_items(items):
    """Join non-empty items into a comma-separated string."""
    vals = [str(v) for v in (items or []) if v is not None and str(v).strip()]
    if not vals:
        return "[not detected]"
    return ", ".join(vals)


def count_abstract_chars(text):
    """Approximate CNIPA abstract length count, excluding whitespace."""
    return len(re.sub(r'\s+', '', text or ""))


def extract_backtick_code_terms(text):
    """Extract likely code identifiers in inline code spans."""
    terms = []
    for value in re.findall(r'`([^`]+)`', text or ""):
        if re.search(r'[A-Za-z_]|::|->|\.', value):
            terms.append(value)
    return terms


def try_resolve_existing_path(path_value):
    """Return resolved path string if file exists, else empty string."""
    if not path_value or not str(path_value).strip():
        return ""
    p = Path(str(path_value))
    if p.exists():
        return str(p.resolve())
    return ""


# ---------------------------------------------------------------------------
# State accessors (safe, mirrors PS1 Get-*Property helpers)
# ---------------------------------------------------------------------------

def sp(obj, name, default=""):
    """Get string property from dict/object safely."""
    if obj is None:
        return default
    val = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    if val is None:
        return default
    return str(val)


def bp(obj, name, default=False):
    """Get bool property from dict/object safely."""
    if obj is None:
        return default
    val = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ('true', 'yes', '1', 'authorized', 'approved')


def ap(obj, name):
    """Get array property from dict/object safely."""
    if obj is None:
        return []
    val = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def op(obj, name, default=None):
    """Get object/any property from dict/object safely."""
    if obj is None:
        return default
    val = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return val if val is not None else default


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Patent draft quality check')
    parser.add_argument('--draft-path', required=True)
    parser.add_argument('--state-path', default='')
    parser.add_argument('--output-path', default='')
    args = parser.parse_args()

    draft_path = Path(args.draft_path).resolve()
    draft_text = draft_path.read_text(encoding='utf-8')
    sections = parse_markdown_sections(draft_text)

    # Load state
    state = None
    resolved_state_path = "[not provided]"
    if args.state_path:
        sp_path = Path(args.state_path)
        if sp_path.exists():
            state = json.loads(sp_path.read_text(encoding='utf-8'))
            resolved_state_path = str(sp_path.resolve())
        else:
            resolved_state_path = f"[not found] {args.state_path}"

    # Evidence notes auto-discovery
    evidence_notes_path = draft_path.parent / (draft_path.stem + "-evidence-notes.md")
    evidence_text = ""
    evidence_sections = []
    if evidence_notes_path.exists():
        evidence_text = evidence_notes_path.read_text(encoding='utf-8')
        evidence_sections = parse_markdown_sections(evidence_text)

    # Output path
    output_path = args.output_path
    if not output_path:
        if args.state_path:
            state_path_for_output = Path(args.state_path)
            if state_path_for_output.parent.name == "state":
                output_path = str(state_path_for_output.parent.parent / "quality" / (draft_path.stem + "-quality-check.md"))
            else:
                output_path = str(state_path_for_output.parent / "quality" / (draft_path.stem + "-quality-check.md"))
        else:
            output_path = str(draft_path.parent.parent / "quality" / (draft_path.stem + "-quality-check.md"))

    findings = []

    def add_finding(severity, category, message, evidence=""):
        findings.append({
            "severity": severity,
            "category": category,
            "message": message,
            "evidence": evidence
        })

    # -----------------------------------------------------------------------
    # Workflow state warning
    # -----------------------------------------------------------------------
    if state is None:
        add_finding("warning", "workflow-state",
                    "未提供可读取的迭代状态文件，Gate A/B/C、代理师审稿和交付就绪度只能做弱校验。")

    # -----------------------------------------------------------------------
    # Title and mainline extraction
    # -----------------------------------------------------------------------
    title_text = sp(state, "selected_title")
    if not title_text:
        title_text = get_first_nonempty_line(get_section_body(sections, "发明名称"))

    mainline_text = sp(state, "selected_mainline")
    if not mainline_text:
        for sec in sections:
            m = re.search(r'(?:推荐进入 Gate A 的保护路径|推荐主线)[:：]\s*(.+)', sec["body"])
            if m:
                mainline_text = m.group(1).strip()
                break

    anchor_keywords = get_anchor_keywords(title_text + " " + mainline_text)
    abstract_text = get_section_body(sections, "摘要")
    claim1_text = get_section_body(sections, "权利要求1")
    tech_text = (get_section_body(sections, "技术方案") + "\n" +
                 get_section_body(sections, "发明内容") + "\n" +
                 get_section_body(sections, "具体实施方式"))

    if not title_text:
        add_finding("warning", "mainline", "未提取到发明名称，主线一致性检查只能做弱校验。")
    if not mainline_text:
        add_finding("warning", "mainline", "未提取到已选主线，建议在状态文件中明确 selected_mainline。")

    if anchor_keywords:
        for name, text in [
            ("摘要", abstract_text),
            ("权利要求1", claim1_text),
            ("技术方案/实施方式", tech_text)
        ]:
            covered = [kw for kw in anchor_keywords if kw in text]
            if len(covered) < max(1, len(anchor_keywords) // 2):
                add_finding("warning", "mainline",
                            f"{name} 对主线关键词覆盖不足。",
                            join_items(anchor_keywords))

    # -----------------------------------------------------------------------
    # Terminology / glossary check
    # -----------------------------------------------------------------------
    glossary = ap(state, "glossary")
    if not glossary:
        glossary = ap(state, "preferred_terms")

    if not glossary:
        add_finding("info", "terminology", "未提供术语表，术语一致性检查仅能依赖弱规则。")
    else:
        for item in glossary:
            preferred = sp(item, "preferred")
            if preferred and preferred not in draft_text:
                add_finding("warning", "terminology",
                            f"首选术语未出现在草稿中：{preferred}")
            for alias in ap(item, "aliases"):
                if alias and alias in draft_text:
                    add_finding("warning", "terminology",
                                f"检测到别名/禁用术语：{alias}",
                                f"建议统一为：{preferred}")

    # -----------------------------------------------------------------------
    # Claim numbering
    # -----------------------------------------------------------------------
    claim_numbers = get_claim_numbers(sections)
    if not claim_numbers:
        add_finding("error", "claims", "未检测到权利要求编号。")
    else:
        for i, num in enumerate(claim_numbers):
            if num != i + 1:
                add_finding("error", "claims", "权利要求编号不连续。",
                            f"检测到序列：{join_items(claim_numbers)}")
                break

    # -----------------------------------------------------------------------
    # Support matrix row-level validation
    # -----------------------------------------------------------------------
    matrix_section = get_section_body(sections, "支撑矩阵")
    if not matrix_section and evidence_sections:
        matrix_section = get_section_body(evidence_sections, "支撑矩阵")

    matrix_rows = get_markdown_table_rows(matrix_section)
    if not matrix_rows:
        add_finding("warning", "support-matrix", "未检测到支撑矩阵或支撑矩阵为空。")
    else:
        for row_index, row in enumerate(matrix_rows, start=1):
            if len(row) < 5:
                add_finding("warning", "support-matrix",
                            f"支撑矩阵第 {row_index} 行列数不足。")
                continue
            if any(is_placeholder(cell) for cell in row):
                add_finding("warning", "support-matrix",
                            f"支撑矩阵第 {row_index} 行仍有占位项。",
                            join_items(row))

    # -----------------------------------------------------------------------
    # Pending items statistics
    # -----------------------------------------------------------------------
    pending_section = get_section_body(sections, "风险点与待确认事项")
    if not pending_section:
        pending_section = get_section_body(sections, "待确认事项")
    pending_source = "draft"
    if not pending_section and evidence_sections:
        pending_section = get_section_body(evidence_sections, "风险点与待确认事项")
        if not pending_section:
            pending_section = get_section_body(evidence_sections, "待确认事项")
        if pending_section:
            pending_source = "evidence-notes"

    pending_bullets = re.findall(r'(?m)^\s*-\s+(.+)$', pending_section)
    pending_bullets = [b.strip() for b in pending_bullets]
    pending_mentions = len(re.findall(r'待用户确认|待确认', draft_text + "\n" + evidence_text))

    if pending_mentions == 0:
        add_finding("info", "pending", "全文未检测到待确认或待用户确认标记。")
    if not pending_section:
        add_finding("warning", "pending", "未单列风险点与待确认事项部分。")
    elif not pending_bullets:
        add_finding("warning", "pending", "已存在风险点与待确认事项标题，但未列出具体事项。")

    # -----------------------------------------------------------------------
    # Conservative content-quality heuristics (warnings only)
    # -----------------------------------------------------------------------
    abstract_char_count = count_abstract_chars(abstract_text)
    if abstract_text and abstract_char_count > 300:
        add_finding("warning", "abstract",
                    "摘要文字疑似超过 300 字，建议压缩至形式审查友好长度。",
                    f"chars_without_spaces={abstract_char_count}")

    claims_text = get_section_body(sections, "权利要求书")
    claim_code_terms = extract_backtick_code_terms(claims_text)
    if len(claim_code_terms) >= 8:
        add_finding("warning", "code-abstraction",
                    "权利要求书中代码标识符较多，建议检查是否已抽象为技术特征。",
                    join_items(claim_code_terms[:12]))

    embodiment_text = get_markdown_region(draft_text, "具体实施方式", include_same_level=True)
    optional_mentions = len(re.findall(r'可选实施方式|替代实施方式|在一种可选实施方式中|在另一种实施方式中', embodiment_text))
    effect_mentions = len(re.findall(r'通过该|如此|由此|从而|能够|有利于|提高|降低|减少|改善|避免|保证', embodiment_text))
    if embodiment_text:
        invention_content_text = get_markdown_region(draft_text, "发明内容")
        if invention_content_text and len(embodiment_text) < len(invention_content_text):
            add_finding("warning", "embodiment-density",
                        "具体实施方式短于发明内容，建议人工检查实施方式有效密度。")
        if optional_mentions == 0:
            add_finding("warning", "embodiment-density",
                        "具体实施方式中未检测到可选/替代实施方式表述。")
        if effect_mentions < 3:
            add_finding("warning", "embodiment-density",
                        "具体实施方式中效果回扣连接词较少，建议检查特征-作用-效果链。")
    else:
        add_finding("warning", "embodiment-density",
                    "未检测到具体实施方式正文，无法进行实施方式密度弱校验。")

    coverage_plan_detected = (
        "实施方式覆盖计划" in evidence_text or
        "实施方式密度自检" in evidence_text
    )

    # -----------------------------------------------------------------------
    # State-dependent checks
    # -----------------------------------------------------------------------
    stage = ""
    gate_a_status = "[missing]"
    gate_b_status = "[missing]"
    gate_c_status = "[missing]"
    attorney_review_status = "not-started"
    deliverable_status = "not-ready"
    docx_export_allowed = False
    gate_c_docx_export_authorized = False
    autonomous_max_rounds = ""
    autonomous_current_round = ""
    open_question_count = 0
    blocking_question_count = 0
    remaining_risk_count = 0
    latex_readiness_status = "not-run"
    latex_readiness_error_count = 0
    latex_readiness_warning_count = 0

    if state is not None:
        stage = sp(state, "current_stage")
        selected_protection_object = sp(state, "selected_protection_object")

        gate_a = op(state, "gate_a")
        gate_b = op(state, "gate_b")
        gate_c = op(state, "gate_c")
        raw_a = sp(gate_a, "status")
        raw_b = sp(gate_b, "status")
        raw_c = sp(gate_c, "status")
        if raw_a:
            gate_a_status = raw_a
        if raw_b:
            gate_b_status = raw_b
        if raw_c:
            gate_c_status = raw_c
        gate_c_docx_export_authorized = bp(gate_c, "docx_export_authorized")

        autonomous_iteration = op(state, "autonomous_iteration")
        autonomous_max_rounds = sp(autonomous_iteration, "max_rounds")
        autonomous_current_round = sp(autonomous_iteration, "current_round")

        open_question_count = get_meaningful_item_count(ap(state, "open_questions"))
        blocking_question_count = get_meaningful_item_count(ap(state, "blocking_questions"))

        deliverable_readiness = op(state, "deliverable_readiness")
        raw_del = sp(deliverable_readiness, "status")
        if raw_del:
            deliverable_status = raw_del
        docx_export_allowed = bp(deliverable_readiness, "docx_export_allowed")
        remaining_risk_count = get_meaningful_item_count(ap(deliverable_readiness, "remaining_risks"))

        draft_evidence_notes_path = try_resolve_existing_path(sp(state, "draft_evidence_notes_path"))
        embodiment_coverage_plan_path = try_resolve_existing_path(sp(state, "embodiment_coverage_plan_path"))
        if evidence_notes_path.exists() and not draft_evidence_notes_path:
            add_finding("warning", "state-consistency",
                        "检测到正式稿配套 evidence notes，但状态文件未记录 draft_evidence_notes_path。",
                        str(evidence_notes_path.resolve()))
        if stage in ("formal-drafting", "pre-review-risk", "attorney-review", "gate-b-pending",
                     "feedback-revision", "feedback-revision-review", "ready-for-gate-c",
                     "gate-c-pending", "export-docx", "completed"):
            if not embodiment_coverage_plan_path and not coverage_plan_detected:
                add_finding("warning", "embodiment-coverage",
                            "未检测到实施方式覆盖计划路径或 evidence notes 中的覆盖计划记录。")
        recorded_quality_path = sp(deliverable_readiness, "quality_check_path")
        if recorded_quality_path:
            recorded_quality_resolved = try_resolve_existing_path(recorded_quality_path)
            if recorded_quality_resolved and Path(recorded_quality_resolved).resolve() != Path(output_path).resolve():
                add_finding("warning", "state-consistency",
                            "状态文件记录的 quality_check_path 与本次输出路径不一致。",
                            f"recorded={recorded_quality_resolved}; current={Path(output_path).resolve()}")

        # Blocking / open questions
        if blocking_question_count > 0:
            add_finding("error", "workflow-gate",
                        "blocking_questions 非空，不能进入最终交付或 DOCX 导出。",
                        f"count={blocking_question_count}")
        if open_question_count > 0:
            add_finding("warning", "workflow-gate",
                        "状态文件仍有 open_questions，交付前应确认或转入风险列表。",
                        f"count={open_question_count}")

        # Gate A
        requires_gate_a = [
            "formal-drafting", "pre-review-risk", "attorney-review", "gate-b-pending",
            "feedback-revision", "feedback-revision-review", "ready-for-gate-c",
            "gate-c-pending", "export-docx", "completed"
        ]
        if stage in requires_gate_a:
            if not test_passed(gate_a_status):
                add_finding("error", "workflow-gate",
                            "当前阶段需要 Gate A 已通过，但状态文件未记录通过状态。",
                            f"gate_a.status={gate_a_status}")
            selected_title = sp(state, "selected_title")
            selected_mainline = sp(state, "selected_mainline")
            if not selected_title or not selected_mainline or not selected_protection_object:
                add_finding("error", "workflow-gate",
                            "Gate A 需要冻结题目、主线和保护客体，但状态文件缺少必要字段。")

        # Gate B
        if stage == "pre-review-risk" and not test_passed(gate_b_status):
            add_finding("warning", "workflow-gate",
                        "正式稿阶段尚未通过 Gate B；只能输出代理师审稿意见和补证方向，不能进入自主修订闭环。")
        if stage in ("feedback-revision", "feedback-revision-review", "ready-for-gate-c", "gate-c-pending", "export-docx", "completed") and not test_passed(gate_b_status):
            add_finding("error", "workflow-gate",
                        "当前阶段需要 Gate B 已通过，但状态文件未记录通过状态。",
                        f"gate_b.status={gate_b_status}")

        # Deliverable readiness full validation
        deliverable_ready = deliverable_status.lower() in (
            "ready", "ready-for-delivery", "passed", "approved", "deliverable"
        )
        if (stage in ("export-docx", "completed") or deliverable_ready or docx_export_allowed) \
                and not test_passed(gate_c_status):
            add_finding("error", "workflow-gate",
                        "最终交付或 DOCX 导出需要 Gate C 已通过，或用户明确授权并记录风险。",
                        f"gate_c.status={gate_c_status}")
        if test_passed(gate_c_status) and not docx_export_allowed and stage in ("export-docx", "completed"):
            add_finding("warning", "state-consistency",
                        "Gate C 已通过且处于导出/完成阶段，但 deliverable_readiness.docx_export_allowed 未标记为 true。")
        if deliverable_ready and remaining_risk_count > 0:
            add_finding("warning", "deliverable-readiness",
                        "deliverable_readiness 已标记就绪，但仍登记 remaining_risks。",
                        f"count={remaining_risk_count}")
        if deliverable_ready and not sp(deliverable_readiness, "quality_check_path"):
            add_finding("warning", "deliverable-readiness",
                        "deliverable_readiness 已标记就绪，但未记录 quality_check_path。")

        # Prior-art check
        needs_prior_art = [
            "gate-a-pending", "formal-drafting", "pre-review-risk", "attorney-review",
            "gate-b-pending", "feedback-revision", "feedback-revision-review",
            "ready-for-gate-c", "gate-c-pending", "export-docx", "completed"
        ]
        if stage in needs_prior_art:
            prior_art_search = op(state, "prior_art_search")
            prior_art_report_path = try_resolve_existing_path(sp(prior_art_search, "report_path"))
            if not sp(state, "closest_prior_art"):
                add_finding("warning", "prior-art",
                            "已进入主线筛选/起草阶段，但状态文件中的 closest_prior_art 仍为空。")
            if not prior_art_report_path:
                add_finding("warning", "prior-art",
                            "未检测到现有技术检索报告，创造性主线筛选仍缺少可追溯依据。")

        # Attorney review status validation
        review_feedback = op(state, "review_feedback")
        attorney_review = op(state, "attorney_review_status")
        raw_ar = sp(attorney_review, "status")
        if not raw_ar:
            raw_ar = sp(review_feedback, "status")
        if raw_ar:
            attorney_review_status = raw_ar

        review_notes_path = try_resolve_existing_path(sp(attorney_review, "latest_review_notes_path"))
        if not review_notes_path:
            review_notes_path = try_resolve_existing_path(sp(review_feedback, "latest_review_notes_path"))
        user_feedback_path = try_resolve_existing_path(sp(attorney_review, "latest_user_feedback_path"))
        if not user_feedback_path:
            user_feedback_path = try_resolve_existing_path(sp(review_feedback, "latest_user_feedback_path"))

        if stage == "pre-review-risk" and not review_notes_path:
            add_finding("warning", "review-feedback",
                        "已进入正式稿阶段，但尚未挂接代理师修改意见；Gate B 前不应进入自主迭代或最终交付。")
        if stage in ("attorney-review", "gate-b-pending", "feedback-revision", "feedback-revision-review", "ready-for-gate-c", "gate-c-pending", "export-docx", "completed"):
            if not review_notes_path:
                add_finding("warning", "review-feedback",
                            "状态文件显示已进入代理师审稿/反馈迭代阶段，但未检测到代理师修改意见文件。")
            if sp(review_feedback, "status") == "user-pending" and not user_feedback_path:
                add_finding("warning", "review-feedback",
                            "状态文件显示等待用户反馈，但未检测到用户反馈记录文件。")

        # Stage consistency checks
        if stage == "formal-drafting":
            if not abstract_text or not claim1_text or not has_section_title(sections, ["说明书"]):
                add_finding("error", "state",
                            "状态文件显示处于正式稿阶段，但摘要/权利要求/说明书结构尚不完整。")

    # -----------------------------------------------------------------------
    # LaTeX strict gate logic
    # -----------------------------------------------------------------------
    latex_gate_strict = (
        stage in ("export-docx", "completed") or
        docx_export_allowed or
        gate_c_docx_export_authorized
    )

    latex_script = Path(__file__).parent / "test-latex-formula-readiness.py"
    if latex_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(latex_script), '--draft-path', str(draft_path), '--as-json'],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
            )
            if result.stdout.strip():
                latex_data = json.loads(result.stdout)
                latex_readiness_error_count = int(latex_data.get("ErrorCount", 0))
                latex_readiness_warning_count = int(latex_data.get("WarningCount", 0))
                if latex_readiness_error_count > 0:
                    latex_readiness_status = "failed"
                elif latex_readiness_warning_count > 0:
                    latex_readiness_status = "warning"
                else:
                    latex_readiness_status = "passed"
                for f in latex_data.get("Findings", []):
                    formula_severity = str(f.get("Severity", "warning"))
                    if formula_severity == "error":
                        quality_severity = "error" if latex_gate_strict else "warning"
                    else:
                        quality_severity = "warning"
                    line_number = str(f.get("LineNumber", ""))
                    evidence_val = str(f.get("Evidence", ""))
                    add_finding(quality_severity, "latex-formula",
                                str(f.get("Message", "")),
                                f"line={line_number}; {evidence_val}")
            else:
                raise ValueError("latex readiness validator returned empty output")
        except Exception as e:
            latex_readiness_status = "validator-error"
            severity = "error" if latex_gate_strict else "warning"
            add_finding(severity, "latex-formula",
                        "LaTeX formula readiness validator failed to run.",
                        str(e))
    else:
        latex_readiness_status = "validator-missing"
        severity = "error" if latex_gate_strict else "warning"
        add_finding(severity, "latex-formula",
                    "LaTeX formula readiness validator is missing.",
                    str(latex_script))

    # -----------------------------------------------------------------------
    # Counts and report
    # -----------------------------------------------------------------------
    error_count = sum(1 for f in findings if f["severity"] == "error")
    warning_count = sum(1 for f in findings if f["severity"] == "warning")
    info_count = sum(1 for f in findings if f["severity"] == "info")

    evidence_notes_display = (
        str(evidence_notes_path.resolve()) if evidence_notes_path.exists()
        else "[not detected]"
    )

    # Build findings table
    if not findings:
        findings_table = "| pass | summary | 未发现问题。 | |\n"
    else:
        rows = []
        for f in findings:
            rows.append(
                f"| {escape_markdown_table_cell(f['severity'])} "
                f"| {escape_markdown_table_cell(f['category'])} "
                f"| {escape_markdown_table_cell(f['message'])} "
                f"| {escape_markdown_table_cell(f['evidence'])} |"
            )
        findings_table = "\n".join(rows) + "\n"

    report = f"""# 自动质量检查报告

- Draft path: `{draft_path}`
- State path: `{resolved_state_path}`
- Evidence notes path: `{evidence_notes_display}`
- Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Error count: {error_count}
- Warning count: {warning_count}
- Info count: {info_count}
- Current stage: {stage}
- Gate A status: {gate_a_status}
- Gate B status: {gate_b_status}
- Gate C status: {gate_c_status}
- Attorney review status: {attorney_review_status}
- Deliverable readiness: {deliverable_status}
- DOCX export allowed: {docx_export_allowed}
- LaTeX formula readiness: {latex_readiness_status} (strict={latex_gate_strict} errors={latex_readiness_error_count} warnings={latex_readiness_warning_count})
- Autonomous iteration: current={autonomous_current_round} max={autonomous_max_rounds}

## Findings

| Severity | Category | Message | Evidence |
|---|---|---|---|
{findings_table}
## Pending Summary

- Pending mentions in full draft: {pending_mentions}
- Pending section source: {pending_source}
- Pending bullets in dedicated section: {len(pending_bullets)}
- Open questions in state: {open_question_count}
- Blocking questions in state: {blocking_question_count}
- Remaining risks in deliverable_readiness: {remaining_risk_count}
- Claim numbers: {join_items(claim_numbers) if claim_numbers else '[not detected]'}
- Anchor keywords: {join_items(anchor_keywords) if anchor_keywords else '[not detected]'}
- LaTeX formula readiness findings: errors={latex_readiness_error_count} warnings={latex_readiness_warning_count} strict={latex_gate_strict}
"""

    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding='utf-8')

    if state is not None and args.state_path and Path(args.state_path).exists():
        deliverable_readiness = state.setdefault("deliverable_readiness", {})
        deliverable_readiness["quality_check_path"] = str(report_path)
        state["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        Path(args.state_path).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"[automated-quality-check] Report written to: {report_path}")
    print(f"[automated-quality-check] Errors={error_count} Warnings={warning_count} Info={info_count}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
