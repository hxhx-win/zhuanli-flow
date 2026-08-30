#!/usr/bin/env python3
"""中文专利 Domain Runtime：状态查询、阶段校验和受控迁移。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from domain_runtime import (  # noqa: E402
    RuntimeFailure,
    failure_envelope,
    status,
    transition,
    validate,
)


class RuntimeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RuntimeFailure("invalid_arguments", message, exit_code=1)


def build_parser() -> argparse.ArgumentParser:
    parser = RuntimeArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="查询当前状态和下一动作")
    status_parser.add_argument("--state-path", required=True)
    status_parser.add_argument("--format", choices=["json", "pretty"], default="json")

    validate_parser = subparsers.add_parser("validate", help="校验阶段入口或出口")
    validate_parser.add_argument("--state-path", required=True)
    validate_parser.add_argument("--stage", required=True)
    validate_parser.add_argument("--mode", choices=["enter", "exit"], required=True)
    validate_parser.add_argument("--format", choices=["json", "pretty"], default="json")

    transition_parser = subparsers.add_parser("transition", help="执行受控状态迁移")
    transition_parser.add_argument("--state-path", required=True)
    transition_parser.add_argument("--from-stage", required=True)
    transition_parser.add_argument("--to-stage", required=True)
    transition_parser.add_argument("--changes-json")
    transition_parser.add_argument("--format", choices=["json", "pretty"], default="json")
    return parser


def parse_changes(raw: str | None):
    if raw is None:
        return None
    source = sys.stdin.read() if raw == "-" else raw
    try:
        return json.loads(source)
    except json.JSONDecodeError as exc:
        raise RuntimeFailure(
            "changes_invalid_json",
            "changes-json 无法解析",
            details={"line": exc.lineno, "column": exc.colno},
            exit_code=1,
        ) from exc


def render(payload: dict, output_format: str) -> None:
    if output_format == "pretty":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    command = "unknown"
    state_path = "."
    output_format = "json"
    try:
        args = parser.parse_args(argv)
        command = args.command
        state_path = args.state_path
        output_format = args.format
        if command == "status":
            payload = status(state_path)
            exit_code = 0
        elif command == "validate":
            payload, exit_code = validate(state_path, args.stage, args.mode)
        else:
            payload, exit_code = transition(
                state_path,
                args.from_stage,
                args.to_stage,
                parse_changes(args.changes_json),
            )
    except RuntimeFailure as failure:
        payload = failure_envelope(command, state_path, failure)
        exit_code = failure.exit_code
    except Exception as exc:  # noqa: BLE001
        failure = RuntimeFailure(
            "runtime_error",
            "Domain Runtime 执行失败",
            details={"reason": str(exc)},
            exit_code=1,
        )
        payload = failure_envelope(command, state_path, failure)
        exit_code = 1
    render(payload, output_format)
    return exit_code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
