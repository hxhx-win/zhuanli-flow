#!/usr/bin/env python3
"""handoff-package.py — 研发交付专利部门时调用,生成 handoff-package.md + 切 state.handoff.status = packaged。

调用位置:cn-patent-workflow-orchestrator 编排器在 step 3 用户分流决策选"交付专利部"时。

输入:
  --slug <slug>             方向标识(必填)
  --state-path <path>       state 文件路径(必填,绝对路径)

输出:
  patent/<patent-slug>/handoff/handoff-package.md  (整目录交接包)

state 变更:
  handoff.status = "packaged"
  handoff.package_path = "patent/<patent-slug>/handoff/handoff-package.md"
  handoff.packaged_at = "<ISO8601 UTC>"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


VERDICT_CN = {
    "go": "评审通过",
    "revise-recommended": "建议修订（非阻断）",
    "revise-required": "需要修订后再起草",
    "stop-recommended": "建议中止该方向",
}

READINESS_CN = {
    "ready": "已就绪",
    "needs_supplement": "需补充材料",
}


TEMPLATE = """# 研发→专利部门交接包

- 项目 slug:{slug}
- 交付时间:{ts}
- 研发提交人:{submitter}

## 发明点一句话概括

{oneliner}

## 上游产物路径

- 主线分析:patent/{slug}/analysis/mainline-analysis.md
- 证据矩阵:patent/{slug}/evidence/evidence-matrix.md
- 检索报告:patent/{slug}/evidence/prior-art-search-report.md
- 评审报告:patent/{slug}/reviews/pre-draft-review.md
- 技术交底书:patent/{slug}/disclosure/disclosure-draft.md
- DF 反例自检信号:patent/{slug}/evidence/df-rationale-signals.yml

## 评审结论

- 评审结论:{verdict}
- 起草前决策准备度:{decision_readiness}
- 补证清单:见 pre-draft-review.md
- 待澄清问题:见 pre-draft-review.md

## 待 Gate A 段决策类目

由编排器在专利部接手后通过 AskUserQuestion 逐题问。候选项动态从上游产物抽取(见 cn-patent-workflow-orchestrator/assets/decision-categories.json)。

## 沟通模板(专利部门可填写)

请在 `patent/{slug}/reviews/patent-dept-notes.md` 中按以下结构填写修改意见;若无意见可不填,编排器在专利部接手时会问"已准备好"/"暂无意见"/"暂停"三选。

```
- 题目偏好:
- 保护客体偏好:
- 写入范围偏好(独权/从权/实施例取舍):
- 附图策略偏好:
- 其他备注:
```
"""


def get_submitter() -> str:
    """优先 git config user.name,退化为 $USER。"""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2,
        )
        name = r.stdout.strip()
        if name:
            return name
    except Exception:
        pass
    return os.environ.get("USER", "unknown")


def render_package(slug: str, state: dict) -> str:
    pre_draft = state.get("step_3", {}).get("pre_draft_review", {})
    return TEMPLATE.format(
        slug=slug,
        ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        submitter=get_submitter(),
        oneliner=pre_draft.get("proposal_summary_oneliner") or "(未生成;详见 pre-draft-review.md)",
        verdict=VERDICT_CN.get(pre_draft.get("verdict"), "未知"),
        decision_readiness=READINESS_CN.get(pre_draft.get("decision_readiness"), "未知"),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--slug", required=True)
    p.add_argument("--state-path", required=True)
    args = p.parse_args()

    state_path = Path(args.state_path)
    if not state_path.exists():
        print(f"ERROR: state file not found: {state_path}", file=sys.stderr)
        return 1
    # 用 lib.state_io / lib.handoff 统一 state 读写 + transition 合法性校验
    sys.path.insert(0, str(Path(__file__).parent / "lib"))
    from state_io import load_state, write_state  # noqa: E402
    from handoff import current_branch, legal_transitions  # noqa: E402

    try:
        state = load_state(state_path)
    except OSError as e:
        print(f"ERROR: cannot read state file {state_path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: state file unparseable {state_path}: {e}", file=sys.stderr)
        return 1

    # state 必须已含 step_3.disclosure_draft.status == completed
    s3 = state.get("step_3", {})
    if s3.get("disclosure_draft", {}).get("status") != "completed":
        print("ERROR: step_3.disclosure_draft.status != completed; 不能交付", file=sys.stderr)
        return 2

    # 转换合法性校验:当前分支需允许切 packaged
    current = current_branch(state)
    if "packaged" not in legal_transitions(current):
        print(
            f"ERROR: handoff.status = {current!r} 不允许切 packaged; "
            f"合法转换: {legal_transitions(current)}",
            file=sys.stderr,
        )
        return 2

    # 渲染并写入 handoff-package.md
    # state 文件位于 patent/<patent-slug>/state/...,handoff 目录与 state 同级
    patent_root = state_path.parent.parent
    handoff_dir = patent_root / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    pkg_path = handoff_dir / "handoff-package.md"
    pkg_path.write_text(render_package(args.slug, state), encoding="utf-8")

    # 更新 state
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.setdefault("handoff", {})
    state["handoff"]["status"] = "packaged"
    state["handoff"]["package_path"] = f"patent/{args.slug}/handoff/handoff-package.md"
    state["handoff"]["packaged_at"] = now
    write_state(state_path, state)

    print(f"OK: packaged. wrote {pkg_path}; state.handoff.status = packaged")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
