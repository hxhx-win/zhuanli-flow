"""state_io.py — state 文件读写与 patent_root 推算。"""
import json
import os
import tempfile
from pathlib import Path


def load_state(state_path) -> dict:
    """读 state JSON。文件不存在 raise FileNotFoundError,JSON 错 raise json.JSONDecodeError。"""
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def patent_root_from_state_path(state_path) -> Path:
    """state 路径推算 patent_root。约定: patent/<slug>/state/<file>.json → patent/<slug>/"""
    return Path(state_path).parent.parent


def write_state(state_path, state: dict) -> None:
    """原子写入 state JSON，保留缩进与中文。"""
    destination = Path(state_path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(state, temporary, ensure_ascii=False, indent=2)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
