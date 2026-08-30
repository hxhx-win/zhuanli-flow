#!/usr/bin/env python3
"""Domain Runtime 的最小标准库回归测试。"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_ROOT / "lib"))

from domain_runtime import (  # noqa: E402
    RuntimeFailure,
    normalize_changes,
    state_lock,
    status,
    transition,
    validate,
)
from preconditions import check_stage  # noqa: E402
from stage_executors import STAGE_EXECUTORS, lookup  # noqa: E402
from state_io import patent_root_from_state_path  # noqa: E402


ENVELOPE_KEYS = {
    "ok",
    "command",
    "state_path",
    "current_stage",
    "next_action",
    "executor_info",
    "validation",
    "applied_changes",
    "warnings",
    "error",
}


def base_state() -> dict:
    return {
        "state_version": "v0.1",
        "current_stage": "step-0",
        "updated_at": "",
        "env_check_path": "patent/demo/state/env-check.json",
        "source_material_roles": {"items": [{"path": "materials/example.md"}]},
        "selected_direction": {"title": ""},
        "mainline_analysis_path": "",
        "feature_layers": [],
        "invention_points": [],
        "handoff": {"status": "not_initiated"},
        "step_3": {"post_disclosure_decision": {}},
        "gate_a": {"status": "pending"},
        "gate_b": {"status": "pending"},
        "gate_c": {"status": "pending"},
        "step_6": {"review_mode": None},
        "step_8": {"revision_subagent_dispatched": False},
        "review_feedback": {},
        "unknown_business_field": {"preserved": True},
    }


class DomainRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "patent" / "demo"
        self.state_path = self.root / "state" / "patent-iteration-state.json"
        self.state_path.parent.mkdir(parents=True)
        self.state = base_state()
        self._write(self.state)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_status_uses_fixed_envelope_and_existing_router(self) -> None:
        result = status(self.state_path)
        self.assertEqual(set(result), ENVELOPE_KEYS)
        self.assertTrue(result["ok"])
        self.assertEqual(result["next_action"], "step-0")
        self.assertEqual(result["executor_info"]["executor"], "orchestrator")

    def test_validate_matches_precondition_truth_source(self) -> None:
        result, exit_code = validate(self.state_path, "step-0", "exit")
        expected = check_stage("step-0", "exit", self.state, patent_root_from_state_path(self.state_path))
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["validation"], expected)

    def test_transition_updates_only_control_fields_and_preserves_unknown_data(self) -> None:
        result, exit_code = transition(self.state_path, "step-0", "step-1")
        saved = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(saved["current_stage"], "step-1")
        self.assertTrue(saved["updated_at"])
        self.assertEqual(saved["unknown_business_field"], {"preserved": True})
        self.assertFalse(list(self.state_path.parent.glob(f".{self.state_path.name}.*.tmp")))

    def test_stale_from_stage_does_not_modify_state(self) -> None:
        before = self.state_path.read_bytes()
        result, exit_code = transition(self.state_path, "step-1", "step-2")
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["error"]["code"], "state_conflict")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_forbidden_business_field_does_not_modify_state(self) -> None:
        before = self.state_path.read_bytes()
        result, exit_code = transition(
            self.state_path,
            "step-0",
            "step-1",
            {"selected_mainline": "不得由 Runtime 写"},
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["error"]["code"], "forbidden_state_field")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_reserved_field_is_rejected(self) -> None:
        with self.assertRaises(RuntimeFailure) as caught:
            normalize_changes({"current_stage": "step-9"})
        self.assertEqual(caught.exception.code, "forbidden_state_field")

    def test_illegal_target_does_not_modify_state(self) -> None:
        before = self.state_path.read_bytes()
        result, exit_code = transition(self.state_path, "step-0", "missing_prior_deliverables")
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["error"]["code"], "illegal_target_stage")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_missing_state_has_stable_tool_error(self) -> None:
        self.state_path.unlink()
        result, exit_code = transition(self.state_path, "step-0", "step-1")
        self.assertEqual(exit_code, 1)
        self.assertEqual(result["error"]["code"], "state_not_found")
        self.assertFalse(Path(f"{self.state_path}.lock").exists())

    def test_target_must_match_derived_route(self) -> None:
        before = self.state_path.read_bytes()
        result, exit_code = transition(self.state_path, "step-0", "step-2")
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["error"]["code"], "illegal_transition")
        self.assertEqual(result["error"]["details"]["derived"], "step-1")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_blocked_source_exit_does_not_modify_state(self) -> None:
        blocked = copy.deepcopy(self.state)
        blocked["env_check_path"] = ""
        self._write(blocked)
        before = self.state_path.read_bytes()
        result, exit_code = transition(self.state_path, "step-0", "step-1")
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["error"]["code"], "validation_blocked")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_lock_timeout_does_not_remove_foreign_lock(self) -> None:
        lock_path = Path(f"{self.state_path}.lock")
        lock_path.write_text("foreign", encoding="utf-8")
        with self.assertRaises(RuntimeFailure) as caught:
            with state_lock(self.state_path, timeout_seconds=0.01):
                self.fail("不应获得已存在的锁")
        self.assertEqual(caught.exception.code, "lock_timeout")
        self.assertEqual(lock_path.read_text(encoding="utf-8"), "foreign")
        lock_path.unlink()

    def test_all_must_load_paths_exist_after_hard_rename(self) -> None:
        for stage in STAGE_EXECUTORS:
            for path in lookup(stage).get("must_load", []):
                self.assertTrue(Path(path).exists(), f"{stage}: {path}")

    def test_cli_accepts_changes_from_stdin(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPTS_ROOT / "domain-runtime.py"),
                "transition",
                "--state-path",
                str(self.state_path),
                "--from-stage",
                "step-0",
                "--to-stage",
                "step-1",
                "--changes-json",
                "-",
            ],
            input='{"gate_b":{"status":"pending"}}',
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(set(payload), ENVELOPE_KEYS)
        self.assertEqual(payload["applied_changes"]["gate_b.status"], "pending")

    def test_cli_reports_malformed_changes_as_tool_error(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPTS_ROOT / "domain-runtime.py"),
                "transition",
                "--state-path",
                str(self.state_path),
                "--from-stage",
                "step-0",
                "--to-stage",
                "step-1",
                "--changes-json",
                "{bad",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(payload["error"]["code"], "changes_invalid_json")


if __name__ == "__main__":
    unittest.main()
