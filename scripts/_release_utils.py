import hashlib
import os
import stat
from pathlib import Path


def path_lexists(path: Path) -> bool:
    return os.path.lexists(path)


def is_link_like(path: Path) -> bool:
    if not path_lexists(path):
        return False
    info = path.stat(follow_symlinks=False)
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_inventory(root: Path) -> dict[str, str]:
    if is_link_like(root):
        raise ValueError(f"拒绝读取链接或 reparse point: {root}")
    if not root.is_dir():
        raise ValueError(f"目录不存在: {root}")

    inventory: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if is_link_like(path):
            raise ValueError(f"目录树中包含链接或 reparse point: {path}")
        if path.is_file():
            inventory[path.relative_to(root).as_posix()] = sha256_file(path)
    return inventory


def tree_sha256(inventory: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative_path, file_digest in sorted(inventory.items()):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_digest))
    return digest.hexdigest()
