import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

from _release_utils import is_link_like


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifest.json"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
ROOT_FILES = (
    "README.md",
    "VERSION",
    "manifest.json",
    "CHANGELOG.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
)
SCRIPT_FILES = (
    "scripts/install-skills.py",
    "scripts/_release_utils.py",
)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def add_tree(files: list[Path], root: Path) -> None:
    if is_link_like(root) or not root.is_dir():
        raise RuntimeError(f"发行目录不存在或为链接: {root}")
    for path in root.rglob("*"):
        if is_link_like(path):
            raise RuntimeError(f"发行内容不能包含链接或 reparse point: {path}")
        if path.is_file():
            files.append(path)


def release_files(manifest: dict) -> list[Path]:
    files = [REPO_ROOT / item for item in ROOT_FILES + SCRIPT_FILES]
    add_tree(files, REPO_ROOT / "third_party")
    for skill in manifest.get("skills", []):
        add_tree(files, REPO_ROOT / "skills" / str(skill["name"]))

    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError("发行文件缺失:\n - " + "\n - ".join(missing))
    unique = {path.relative_to(REPO_ROOT).as_posix(): path for path in files}
    return [unique[key] for key in sorted(unique)]


def write_deterministic_zip(zip_path: Path, root_name: str, files: list[Path]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(REPO_ROOT).as_posix()
            info = zipfile.ZipInfo(f"{root_name}/{relative}", FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 ZhuanliFlow 确定性完整发行包。")
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist"), help="输出目录，默认 dist/")
    args = parser.parse_args()
    try:
        manifest = load_manifest()
        version = str(manifest["version"])
        output_dir = Path(args.output_dir).expanduser().absolute()
        output_dir.mkdir(parents=True, exist_ok=True)
        asset_name = f"zhuanli-flow-v{version}-full.zip"
        zip_path = output_dir / asset_name
        checksum_path = output_dir / f"{asset_name}.sha256"
        temporary_path = output_dir / f".{asset_name}.tmp"
        if temporary_path.exists():
            temporary_path.unlink()

        write_deterministic_zip(temporary_path, f"zhuanli-flow-{version}", release_files(manifest))
        os.replace(temporary_path, zip_path)
        digest = sha256_file(zip_path)
        checksum_path.write_text(f"{digest}  {asset_name}\n", encoding="utf-8", newline="\n")
        print(zip_path)
        print(checksum_path)
        print(f"SHA-256: {digest}")
        return 0
    except (OSError, KeyError, ValueError, json.JSONDecodeError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"Release build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
