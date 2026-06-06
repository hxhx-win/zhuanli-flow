#!/usr/bin/env python3
"""Validate LaTeX formulas in patent Markdown draft for DOCX-readiness."""
import argparse
import json
import re
import sys
from pathlib import Path


def has_cjk(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def remove_inline_math(text):
    clean = re.sub(r'\\\([\s\S]*?\\\)', ' ', text)
    clean = re.sub(r'(?<!\\)\$[^$]+(?<!\\)\$', ' ', clean)
    return clean


def looks_formula_only(text):
    trimmed = text.strip()
    if not trimmed or has_cjk(trimmed):
        return False
    if re.match(r'^[A-Za-z]+\d*$', trimmed):
        return False
    return bool(
        re.search(r'[=\u2208\u2264\u2265<>]', trimmed) or
        re.search(r'\|\|', trimmed) or
        re.search(r'[{}_\^]', trimmed) or
        re.search(r'[\u0370-\u03FF]', trimmed) or
        re.search(r'(?<!\\)\b(sum|sqrt|mu|theta|lambda\d*|Phi|dist|angle|max|min)\s*\(', trimmed)
    )


def is_warning_only_formula(text):
    trimmed = text.strip()
    if re.match(r'^[A-Za-z][A-Za-z0-9_]*\s*=\s*[\{\[]', trimmed):
        return True
    if re.match(r'^[A-Za-z][A-Za-z0-9_]*\s*=\s*[01]\s*$', trimmed):
        return True
    if re.match(r'^[\u0370-\u03FFA-Za-z0-9_,\s\(\)]+(<=|>=|\u2264|\u2265)[\u0370-\u03FFA-Za-z0-9_,\s\(\)]+$', trimmed):
        return True
    return False


def skip_whitespace(text, index):
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def find_matching_brace(text, open_index):
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def read_latex_argument_end(text, index):
    index = skip_whitespace(text, index)
    if index >= len(text):
        return -1
    if text[index] == '{':
        close = find_matching_brace(text, index)
        return (close + 1) if close >= 0 else -1
    if text[index] == '\\':
        cursor = index + 1
        while cursor < len(text) and text[cursor].isalpha():
            cursor += 1
        return max(cursor, index + 2) if cursor == index + 1 else cursor
    return index + 1


def get_unbraced_sum_findings(latex_text):
    issues = []
    for match in re.finditer(r'\\sum(?![A-Za-z])', latex_text):
        cursor = match.end()
        cursor = skip_whitespace(latex_text, cursor)
        if cursor <= len(latex_text) - 7 and latex_text[cursor:cursor+7] == '\\limits':
            cursor += 7
            cursor = skip_whitespace(latex_text, cursor)
        for _ in range(2):
            if cursor >= len(latex_text) or latex_text[cursor] not in '_^':
                break
            arg_end = read_latex_argument_end(latex_text, cursor + 1)
            if arg_end < 0:
                issues.append(match.group())
                break
            cursor = skip_whitespace(latex_text, arg_end)
        else:
            pass
        if cursor >= len(latex_text) or latex_text[cursor] != '{':
            snippet = latex_text[match.start():match.start()+80].strip()
            issues.append(snippet)
            continue
        body_close = find_matching_brace(latex_text, cursor)
        if body_close < 0 or not latex_text[cursor+1:body_close].strip():
            snippet = latex_text[match.start():match.start()+80].strip()
            issues.append(snippet)
    return issues


def get_disallowed_limit_operator_findings(latex_text):
    issues = []
    for match in re.finditer(r'\\(?:max|min)(?![A-Za-z])\s*(?:\\limits\s*)?[_^]', latex_text):
        snippet = latex_text[match.start():match.start()+80].strip()
        issues.append(snippet)
    return issues


def get_operator_text_subscript_findings(latex_text):
    issues = set()
    for pattern in [r'_\{[^{}]*\\(?:max|min|avg|ref|safe)(?![A-Za-z])[^{}]*\}',
                    r'_(?:\\(?:max|min|avg|ref|safe)(?![A-Za-z]))']:
        for match in re.finditer(pattern, latex_text):
            issues.add(match.group().strip())
    return list(issues)


PSEUDO_FUNC = re.compile(r'(?<!\\)\b(sum|sqrt|mu|theta|lambda\d*|Phi|dist|angle|max|min)\s*\(')
RAW_OPERATOR = re.compile(r'\|\||\^T')
BARE_OBJECTIVE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*(?:\([^\)]*\))?\s*=')


def main():
    parser = argparse.ArgumentParser(description='LaTeX formula readiness check')
    parser.add_argument('--draft-path', required=True)
    parser.add_argument('--output-path', default='')
    parser.add_argument('--as-json', action='store_true')
    parser.add_argument('--fail-on-error', action='store_true')
    args = parser.parse_args()

    draft_path = Path(args.draft_path).resolve()
    text = draft_path.read_text(encoding='utf-8')
    lines = text.split('\n')
    findings = []

    in_fence = False
    fence_lang = ""
    fence_start = 0
    latex_fence_has_content = False

    for i, line in enumerate(lines):
        line_number = i + 1
        trimmed = line.strip()

        if in_fence:
            if re.match(r'^```\s*$', trimmed):
                if fence_lang == "latex" and not latex_fence_has_content:
                    findings.append({"Severity": "error", "Category": "latex-fence", "LineNumber": fence_start, "Message": "Empty latex code fence.", "Evidence": f"line {fence_start}"})
                in_fence = False
                fence_lang = ""
                continue
            if fence_lang == "latex":
                if trimmed:
                    latex_fence_has_content = True
                if PSEUDO_FUNC.search(trimmed) or RAW_OPERATOR.search(trimmed) or re.search(r'(?<!\\)(<=|>=)', trimmed):
                    findings.append({"Severity": "error", "Category": "latex-fence", "LineNumber": line_number, "Message": "Latex code fence still contains pseudo-formula syntax.", "Evidence": trimmed})
                for issue in get_unbraced_sum_findings(trimmed):
                    findings.append({"Severity": "error", "Category": "latex-sum-body", "LineNumber": line_number, "Message": "LaTeX \\sum must wrap the summand in an explicit brace group.", "Evidence": issue})
                for issue in get_disallowed_limit_operator_findings(trimmed):
                    findings.append({"Severity": "error", "Category": "latex-limit-operator", "LineNumber": line_number, "Message": "Use function or set form for max/min instead of limit syntax.", "Evidence": issue})
                for issue in get_operator_text_subscript_findings(trimmed):
                    findings.append({"Severity": "error", "Category": "latex-text-subscript", "LineNumber": line_number, "Message": "Textual subscripts must use \\mathrm{...}.", "Evidence": issue})
            continue

        fence_match = re.match(r'^```([A-Za-z0-9_-]+)?\s*$', trimmed)
        if fence_match:
            in_fence = True
            fence_lang = (fence_match.group(1) or "").lower()
            fence_start = line_number
            latex_fence_has_content = False
            continue

        if not trimmed:
            continue

        # Check inline math
        for inline in re.finditer(r'\\\(([\s\S]*?)\\\)', trimmed):
            inner = inline.group(1)
            for issue in get_unbraced_sum_findings(inner):
                findings.append({"Severity": "error", "Category": "latex-sum-body", "LineNumber": line_number, "Message": "Inline \\sum must wrap summand in brace group.", "Evidence": issue})
            for issue in get_disallowed_limit_operator_findings(inner):
                findings.append({"Severity": "error", "Category": "latex-limit-operator", "LineNumber": line_number, "Message": "Inline max/min must use function form.", "Evidence": issue})
            for issue in get_operator_text_subscript_findings(inner):
                findings.append({"Severity": "error", "Category": "latex-text-subscript", "LineNumber": line_number, "Message": "Inline textual subscripts must use \\mathrm{...}.", "Evidence": issue})

        without_math = remove_inline_math(trimmed)
        if not without_math.strip():
            continue

        formula_only = looks_formula_only(without_math)
        has_pseudo = bool(PSEUDO_FUNC.search(without_math))
        has_raw_op = bool(RAW_OPERATOR.search(without_math))
        has_bare_obj = bool(BARE_OBJECTIVE.search(without_math)) and not has_cjk(without_math)

        if formula_only and (has_pseudo or has_raw_op or has_bare_obj) and not is_warning_only_formula(without_math):
            findings.append({"Severity": "error", "Category": "unmarked-display-formula", "LineNumber": line_number, "Message": "Likely display formula not in latex code fence.", "Evidence": trimmed})
            continue

        if has_pseudo or has_raw_op:
            findings.append({"Severity": "error", "Category": "unmarked-inline-formula", "LineNumber": line_number, "Message": "Paragraph contains formula fragment not marked with \\(...\\).", "Evidence": trimmed})
            continue

        if formula_only or re.search(r'\b[A-Za-z][A-Za-z0-9_]*\s*[=\u2208]\s*[\{\[A-Za-z0-9\u0370-\u03FF]', without_math):
            findings.append({"Severity": "warning", "Category": "possible-unmarked-symbol", "LineNumber": line_number, "Message": "Possible symbol not explicitly marked as LaTeX.", "Evidence": trimmed})

    if in_fence:
        if fence_lang == "latex":
            findings.append({"Severity": "error", "Category": "latex-fence", "LineNumber": fence_start, "Message": "Latex code fence is not closed.", "Evidence": f"line {fence_start}"})
        else:
            findings.append({"Severity": "warning", "Category": "code-fence", "LineNumber": fence_start, "Message": "Code fence is not closed and may affect formula recognition.", "Evidence": f"line {fence_start}"})

    errors = [f for f in findings if f["Severity"] == "error"]
    warnings = [f for f in findings if f["Severity"] == "warning"]

    result = {
        "DraftPath": str(draft_path),
        "CheckName": "latex-formula-readiness",
        "ErrorCount": len(errors),
        "WarningCount": len(warnings),
        "FindingCount": len(findings),
        "Findings": findings,
    }

    if args.as_json:
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output_path:
            Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output_path).write_text(output, encoding='utf-8')
        print(output)
    else:
        print("# LaTeX Formula Readiness Report")
        print(f"\n- Draft path: `{draft_path}`")
        print(f"- Error count: {len(errors)}")
        print(f"- Warning count: {len(warnings)}")
        print("\n| Severity | Line | Category | Message | Evidence |")
        print("|---|---:|---|---|---|")
        if not findings:
            print("| pass |  | summary | No formula source issues detected. | |")
        else:
            for f in findings:
                print(f"| {f['Severity']} | {f['LineNumber']} | {f['Category']} | {f['Message']} | {f['Evidence'][:60]} |")

    if args.fail_on_error and len(errors) > 0:
        sys.exit(1)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
