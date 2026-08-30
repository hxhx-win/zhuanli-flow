"""中文专利 Domain Runtime 的确定性门面。"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from preconditions import check_stage
from stage_executors import STAGE_EXECUTORS, lookup as lookup_executor
from state_io import load_state, patent_root_from_state_path, write_state


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
LOCK_TIMEOUT_SECONDS = 5.0

_ALLOWED_EXACT_FIELDS = {
    "step_3.stage",
    "step_3.status",
    "handoff.status",
    "handoff.drafting_initiator",
    "handoff.packaged_at",
    "handoff.picked_up_at",
    "handoff.notes_decision_at",
    "handoff.notes_fill_mode",
    "handoff.notes_source_document",
    "autonomous_iteration.current_round",
    "step_6.review_mode",
    "step_6.review_mode_decided_at",
    "step_6.review_mode_selected_at",
    "step_6.synthesis_subagent_dispatched_at",
    "step_8.revision_subagent_dispatched",
    "step_8.revision_subagent_dispatched_at",
    "review_feedback.status",
}
_ALLOWED_FIELD_PREFIXES = (
    "step_3.post_disclosure_decision.",
    "gate_a.risk_review.",
    "gate_a.drafting_decisions.",
    "gate_a.gate_a_confirmation.",
    "gate_b.",
    "gate_c.",
    "step_6.multi_agent_dispatch.",
    "review_feedback.pre_review_risk_acknowledged",
)
_ALLOWED_GATE_A_FIELDS = {"gate_a.stage", "gate_a.status"}
_RESERVED_FIELDS = {"current_stage", "updated_at"}


class RuntimeFailure(Exception):
    """可转换为统一 Runtime error envelope 的预期失败。"""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.exit_code = exit_code


def envelope(
    command: str,
    state_path: Path | str,
    *,
    ok: bool,
    current_stage: str | None = None,
    next_action: str | None = None,
    executor_info: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    applied_changes: dict[str, Any] | None = None,
    warnings: list[Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "command": command,
        "state_path": str(Path(state_path).resolve()),
        "current_stage": current_stage,
        "next_action": next_action,
        "executor_info": executor_info,
        "validation": validation,
        "applied_changes": applied_changes or {},
        "warnings": warnings or [],
        "error": error,
    }


def failure_envelope(command: str, state_path: Path | str, failure: RuntimeFailure) -> dict[str, Any]:
    current_stage = None
    try:
        current_stage = load_state(state_path).get("current_stage")
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return envelope(
        command,
        state_path,
        ok=False,
        current_stage=current_stage,
        error={
            "code": failure.code,
            "message": failure.message,
            "details": failure.details,
        },
    )


def _load_router_module():
    module_path = SCRIPTS_ROOT / "get-next-step.py"
    spec = importlib.util.spec_from_file_location("_domain_runtime_router", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载路由模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_next_action(state: dict[str, Any], state_path: Path) -> dict[str, Any]:
    """调用既有路由真相源，不复制路由规则。"""
    return _load_router_module().compute_next_action(state, state_path)


def load_runtime_state(state_path: Path | str) -> tuple[Path, dict[str, Any]]:
    path = Path(state_path).resolve()
    if not path.exists():
        raise RuntimeFailure(
            "state_not_found",
            f"state 文件不存在: {path}",
            details={"state_path": str(path)},
            exit_code=1,
        )
    try:
        state = load_state(path)
    except json.JSONDecodeError as exc:
        raise RuntimeFailure(
            "state_invalid_json",
            f"state JSON 无法解析: {path}",
            details={"line": exc.lineno, "column": exc.colno},
            exit_code=1,
        ) from exc
    except OSError as exc:
        raise RuntimeFailure(
            "state_read_error",
            f"state 文件无法读取: {path}",
            details={"reason": str(exc)},
            exit_code=1,
        ) from exc
    if not isinstance(state, dict):
        raise RuntimeFailure(
            "state_invalid_type",
            "state JSON 顶层必须是对象",
            details={"actual_type": type(state).__name__},
            exit_code=1,
        )
    return path, state


def status(state_path: Path | str) -> dict[str, Any]:
    path, state = load_runtime_state(state_path)
    route = compute_next_action(state, path)
    return envelope(
        "status",
        path,
        ok=True,
        current_stage=state.get("current_stage"),
        next_action=route.get("next_action"),
        executor_info=route.get("executor_info"),
        warnings=route.get("warnings", []),
    )


def validate(state_path: Path | str, stage: str, mode: str) -> tuple[dict[str, Any], int]:
    path, state = load_runtime_state(state_path)
    result = check_stage(stage, mode, state, patent_root_from_state_path(path))
    next_action = None
    if mode == "exit" and result.get("result") != "blocked":
        next_action = compute_next_action(state, path).get("next_action")
    is_ok = result.get("result") != "blocked"
    response = envelope(
        "validate",
        path,
        ok=is_ok,
        current_stage=state.get("current_stage"),
        next_action=next_action,
        executor_info=lookup_executor(stage),
        validation=result,
        warnings=result.get("warnings", []),
        error=None if is_ok else {
            "code": "validation_blocked",
            "message": f"stage {stage} {mode} 校验未通过",
            "details": {"stage": stage, "mode": mode},
        },
    )
    return response, 0 if is_ok else 2


def _flatten_changes(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for raw_key, child in value.items():
        if not isinstance(raw_key, str) or not raw_key or raw_key.startswith(".") or raw_key.endswith("."):
            raise RuntimeFailure(
                "invalid_change_path",
                "changes-json 的字段路径必须是非空字符串且不能以点号开头或结尾",
                details={"field": raw_key},
                exit_code=1,
            )
        key = f"{prefix}.{raw_key}" if prefix else raw_key
        if isinstance(child, dict) and child:
            flattened.update(_flatten_changes(child, key))
        else:
            flattened[key] = child
    return flattened


def normalize_changes(changes: dict[str, Any] | None) -> dict[str, Any]:
    if changes is None:
        return {}
    if not isinstance(changes, dict):
        raise RuntimeFailure(
            "changes_invalid_type",
            "changes-json 顶层必须是 JSON 对象",
            details={"actual_type": type(changes).__name__},
            exit_code=1,
        )
    flattened = _flatten_changes(changes)
    for field in flattened:
        if field in _RESERVED_FIELDS:
            raise RuntimeFailure(
                "forbidden_state_field",
                f"字段只能由 Runtime 自动设置: {field}",
                details={"field": field},
            )
        allowed = (
            field in _ALLOWED_EXACT_FIELDS
            or field in _ALLOWED_GATE_A_FIELDS
            or any(field.startswith(prefix) for prefix in _ALLOWED_FIELD_PREFIXES)
        )
        if not allowed:
            raise RuntimeFailure(
                "forbidden_state_field",
                f"禁止通过 Runtime 修改专业结果字段: {field}",
                details={"field": field},
            )
    return flattened


def _set_dotted(state: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    current = state
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
            current[part] = child
        if not isinstance(child, dict):
            raise RuntimeFailure(
                "invalid_change_path",
                f"无法写入字段，父路径不是对象: {dotted}",
                details={"field": dotted, "parent": part},
            )
        current = child
    current[parts[-1]] = value


@contextmanager
def state_lock(state_path: Path, timeout_seconds: float = LOCK_TIMEOUT_SECONDS) -> Iterator[Path]:
    lock_path = Path(f"{state_path}.lock")
    deadline = time.monotonic() + timeout_seconds
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeFailure(
                    "lock_timeout",
                    f"等待 state 锁超时: {lock_path}",
                    details={"lock_path": str(lock_path), "timeout_seconds": timeout_seconds},
                    exit_code=1,
                )
            time.sleep(0.05)
    try:
        payload = json.dumps(
            {"pid": os.getpid(), "acquired_at": datetime.now(timezone.utc).isoformat()},
            ensure_ascii=False,
        ).encode("utf-8")
        os.write(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        yield lock_path
    finally:
        if descriptor is not None:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def transition(
    state_path: Path | str,
    from_stage: str,
    to_stage: str,
    changes: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    path = Path(state_path).resolve()
    if from_stage not in STAGE_EXECUTORS:
        failure = RuntimeFailure(
            "unknown_source_stage",
            f"未知来源 stage: {from_stage}",
            details={"stage": from_stage},
        )
        return failure_envelope("transition", path, failure), failure.exit_code
    if to_stage != "completed" and to_stage not in STAGE_EXECUTORS:
        failure = RuntimeFailure(
            "illegal_target_stage",
            f"未知目标 stage: {to_stage}",
            details={"stage": to_stage},
        )
        return failure_envelope("transition", path, failure), failure.exit_code

    try:
        normalized_changes = normalize_changes(changes)
        if not path.exists():
            load_runtime_state(path)
        with state_lock(path):
            path, state = load_runtime_state(path)
            current_stage = state.get("current_stage")
            if current_stage != from_stage:
                raise RuntimeFailure(
                    "state_conflict",
                    "state.current_stage 与 --from-stage 不一致",
                    details={"expected": from_stage, "actual": current_stage},
                )

            candidate = copy.deepcopy(state)
            for field, value in normalized_changes.items():
                _set_dotted(candidate, field, value)

            patent_root = patent_root_from_state_path(path)
            source_validation = check_stage(from_stage, "exit", candidate, patent_root)
            if source_validation.get("result") == "blocked":
                raise RuntimeFailure(
                    "validation_blocked",
                    f"来源 stage {from_stage} exit 校验未通过",
                    details={"validation": source_validation},
                )

            routable = copy.deepcopy(candidate)
            routable.pop("current_stage", None)
            route = compute_next_action(routable, path)
            derived_target = route.get("next_action")
            if derived_target != to_stage:
                raise RuntimeFailure(
                    "illegal_transition",
                    "目标 stage 与状态机推导结果不一致",
                    details={
                        "requested": to_stage,
                        "derived": derived_target,
                        "route": route,
                    },
                )

            target_validation = None
            if to_stage != "completed":
                target_validation = check_stage(to_stage, "enter", candidate, patent_root)
                if target_validation.get("result") == "blocked":
                    raise RuntimeFailure(
                        "validation_blocked",
                        f"目标 stage {to_stage} enter 校验未通过",
                        details={"validation": target_validation},
                    )

            candidate["current_stage"] = to_stage
            candidate["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_state(path, candidate)
            applied = dict(normalized_changes)
            applied["current_stage"] = to_stage
            applied["updated_at"] = candidate["updated_at"]
            response = envelope(
                "transition",
                path,
                ok=True,
                current_stage=to_stage,
                next_action=to_stage,
                executor_info=None if to_stage == "completed" else lookup_executor(to_stage),
                validation={"source_exit": source_validation, "target_enter": target_validation},
                applied_changes=applied,
                warnings=(source_validation.get("warnings", []) + (target_validation or {}).get("warnings", [])),
            )
            return response, 0
    except RuntimeFailure as failure:
        return failure_envelope("transition", path, failure), failure.exit_code
    except OSError as exc:
        failure = RuntimeFailure(
            "state_write_error",
            f"state 迁移期间发生文件错误: {path}",
            details={"reason": str(exc)},
            exit_code=1,
        )
        return failure_envelope("transition", path, failure), failure.exit_code
