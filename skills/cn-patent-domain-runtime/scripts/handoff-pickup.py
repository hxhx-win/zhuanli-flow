#!/usr/bin/env python3
"""handoff-pickup.py — 专利部门启动编排器后用户确认接手时调用,切 state.handoff.status = picked_up,
并自动从模板创建 patent/<slug>/reviews/patent-dept-notes.md(若不存在)。

调用位置:cn-patent-workflow-orchestrator 编排器在启动后检测到 handoff.status == packaged,
        AskUserQuestion 三选用户回答"我是专利部门,接手起草"时。

输入:
  --slug <slug>             方向标识(必填)
  --state-path <path>       state 文件路径(必填,绝对路径)

输出:
  patent/<slug>/reviews/patent-dept-notes.md  (若不存在则从模板创建空白注释文件)
  stdout 打印接续提示

state 变更:
  handoff.status = "picked_up"
  handoff.drafting_initiator = "patent_dept"
  handoff.picked_up_at = "<ISO8601 UTC>"
  handoff.patent_dept_notes_path = "patent/<slug>/reviews/patent-dept-notes.md"

接续:
  脚本不直接弹 notes 准备状态问题;编排器在调脚本后立即进入第二次 AskUserQuestion(notes 四选填写方式),
  完成后必须同时写两个字段:handoff.notes_fill_mode(prompt|document|manual|none,供 extract-drafting-context
  决定是否把 patent-dept-notes 传给起草 subagent)+ handoff.notes_decision_at(ISO 时间,供 picked_up_substage 推进 S4)。
  只写 notes_decision_at 会让专利部强制意见漏传起草侧。
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


NEXT_PROMPT = """\
✓ 已切换为专利部门接手模式(handoff.status = picked_up)。

✓ 已创建专利部门修改意见文件(若不存在):
  patent/{slug}/reviews/patent-dept-notes.md

下一步编排器将询问填写方式(四选):

  1. 输入提示词                → AI 据提示词转写为 patent-dept-notes.md(强制意见)
  2. 提供已写好的修改意见文档  → AI 读取专利部门的意见文档(任意格式:Word/Markdown/
                                  txt/PDF 等),提炼后转写为 patent-dept-notes.md
  3. 手动编辑                  → 用户自行编辑 patent-dept-notes.md 后告知"已填好"
  4. 暂无修改意见              → 跳过 notes(patent_dept_notes_path 置空)直接进 Gate A 段

提示:patent-dept-notes.md 是专利部门强制意见,优先级最高,下游起草必须落地。
"""


def resolve_template_path() -> Path:
    """assets/patent-dept-notes.template.md 与本脚本相对位置固定。"""
    return Path(__file__).resolve().parent.parent / "assets" / "patent-dept-notes.template.md"


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

    # 转换合法性校验:当前分支需允许切 picked_up
    current = current_branch(state)
    if "picked_up" not in legal_transitions(current):
        print(
            f"ERROR: handoff.status = {current!r} 不允许切 picked_up; "
            f"合法转换: {legal_transitions(current)}",
            file=sys.stderr,
        )
        return 2

    # state 文件位于 patent/<slug>/state/...,reviews 目录与 state 同级
    patent_root = state_path.parent.parent
    reviews_dir = patent_root / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    notes_path = reviews_dir / "patent-dept-notes.md"
    notes_rel_path = f"patent/{args.slug}/reviews/patent-dept-notes.md"

    if not notes_path.exists():
        template_path = resolve_template_path()
        if not template_path.exists():
            print(
                f"ERROR: template not found: {template_path}",
                file=sys.stderr,
            )
            return 3
        notes_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["handoff"]["status"] = "picked_up"
    state["handoff"]["drafting_initiator"] = "patent_dept"
    state["handoff"]["picked_up_at"] = now
    state["handoff"]["patent_dept_notes_path"] = notes_rel_path
    write_state(state_path, state)

    print(NEXT_PROMPT.format(slug=args.slug))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
