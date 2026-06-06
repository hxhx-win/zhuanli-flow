"""state_io.py — state 文件读写与 patent_root 推算。无副作用。"""
import json
from pathlib import Path


def load_state(state_path) -> dict:
    """读 state JSON。文件不存在 raise FileNotFoundError,JSON 错 raise json.JSONDecodeError。"""
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def patent_root_from_state_path(state_path) -> Path:
    """state 路径推算 patent_root。约定: patent/<slug>/state/<file>.json → patent/<slug>/"""
    return Path(state_path).parent.parent


def write_state(state_path, state: dict) -> None:
    """写 state JSON,保留缩进与中文。"""
    Path(state_path).write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
