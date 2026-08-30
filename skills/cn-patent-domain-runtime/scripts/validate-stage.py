#!/usr/bin/env python3
"""validate-stage.py — 宿主 Agent调,显式断言 stage 前置/出口条件。

契约见 spec §3.5。

CLI:
  --state-path <path>   必填
  --stage <stage-id>    必填(共 23 项,见 spec §3.5)
  --mode <enter|exit>   默认 enter;类 B awaiting stage 不区分 mode

输出 JSON:
  {
    "stage", "mode",
    "result": "ok" | "blocked" | "warned",
    "passed":   [{"field"/"deliverable": ..., "detail": ...}],
    "missing":  [{...}],
    "blocked":  [{...}],
    "warnings": [{...}],
    "next_suggested_action": "..."
  }

退出码: 0 = 校验完成(任何 result);非零 = 工具错误(如 state 文件缺失)。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from state_io import load_state, patent_root_from_state_path  # noqa: E402
from preconditions import check_stage  # noqa: E402
from stage_executors import lookup as lookup_executor  # noqa: E402


def _suggest(r: dict) -> str:
    if r["result"] == "ok":
        return f"stage {r['stage']} {r['mode']} 通过,可继续推进"
    if r["missing"]:
        items = ", ".join(
            m.get("field") or m.get("deliverable") or m.get("unknown_stage") or "?"
            for m in r["missing"][:3]
        )
        return f"缺失: {items} — 宿主 Agent须 AskUserQuestion 或派 subagent 补"
    if r["blocked"]:
        return "存在硬阻断规则,见 blocked 详情"
    if r["warnings"]:
        return "存在 warned 信号,可推进但应告知用户,见 warnings 详情"
    return "见 result 详情"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--state-path", required=True, help="state JSON 绝对路径")
    p.add_argument("--stage", required=True, help="stage id,见 spec §3.5 枚举")
    p.add_argument("--mode", choices=["enter", "exit"], default="enter",
                   help="enter=前置校验,exit=出口校验(类 B 不区分)")
    args = p.parse_args()

    state_path = Path(args.state_path)
    if not state_path.exists():
        print(f"ERROR: state file not found: {state_path}", file=sys.stderr)
        return 1
    try:
        state = load_state(state_path)
    except Exception as e:
        print(f"ERROR: failed to load state: {e}", file=sys.stderr)
        return 1

    patent_root = patent_root_from_state_path(state_path)
    result = check_stage(args.stage, args.mode, state, patent_root)
    result["next_suggested_action"] = _suggest(result)

    # 注入当前 stage 的 executor 元数据(从 stage_executors.py 真相源读)。
    # 主 agent 看到 executor=main_run_skill / must_load 非空时,必须先 Read 相关文件再操作。
    result["executor_info"] = lookup_executor(args.stage)

    # 主跑型 skill 的 must_write_state_on_load 字段缺失时特化文案,防止 agent 误以为可直接 Edit 补值绕过加载闸门
    _mw = result["executor_info"].get("must_write_state_on_load")
    if _mw and any(m.get("field") == _mw for m in result.get("missing", [])):
        _exe = result["executor_info"].get("executor", "")
        _ml = result["executor_info"].get("must_load", [])
        result["next_suggested_action"] = (
            f"缺失: {_mw} — 该字段必须由 {_exe} skill 加载时写入;请先 Read {' + '.join(_ml)} 并加载该 skill,禁止直接 Edit 补值"
        )

    # exit ok 时自动 chain get-next-step,把下一步的 executor / 必读文件一并暴露。
    # 防止编排器跑完 exit 就以为流程结束,漏掉非直觉衔接 stage(如 post-disclosure-decision)。
    # 文件名带 dash 不能直接 import,用 importlib 加载。
    if args.mode == "exit" and result["result"] == "ok":
        try:
            import importlib.util as _ilu
            _gns_path = Path(__file__).parent / "get-next-step.py"
            _spec = _ilu.spec_from_file_location("_gns", _gns_path)
            _gns = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_gns)
            result["next_step"] = _gns.compute_next_action(state, state_path)
        except Exception as e:  # noqa: BLE001
            result["next_step_error"] = f"failed to chain get-next-step: {e}"

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
