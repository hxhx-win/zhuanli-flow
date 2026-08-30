import argparse
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "manifest.json"
SKILLS_ROOT = REPO_ROOT / "skills"
DEFAULT_LIVE_ROOTS = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}
RENAMED_SKILLS = {
    "cn-patent-workflow-orchestrator": "cn-patent-domain-runtime",
}


def path_lexists(path: Path) -> bool:
    return os.path.lexists(path)


def is_reparse_point(path: Path) -> bool:
    try:
        attrs = path.stat(follow_symlinks=False).st_file_attributes
    except AttributeError:
        return path.is_symlink()
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def same_target(live_path: Path, repo_path: Path) -> bool:
    if not live_path.exists() or not is_reparse_point(live_path):
        return False
    try:
        return live_path.resolve(strict=True) == repo_path.resolve(strict=True)
    except OSError:
        return False


def remove_live_link(path: Path) -> None:
    """只移除 symlink/junction 本身，绝不递归删除目标。"""
    if path.is_symlink():
        path.unlink()
        return
    if is_reparse_point(path):
        path.rmdir()
        return
    raise RuntimeError(f"拒绝把真实目录当作 live link 删除: {path}")


def choose_backup_root(live_root: Path, agent: str) -> Path:
    base = live_root / f".patents-workflow-backup-{agent}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    candidate = base
    suffix = 2
    while path_lexists(candidate):
        candidate = Path(f"{base}-{suffix}")
        suffix += 1
    return candidate


def create_live_link(link_path: Path, target_path: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"创建 junction 失败: {link_path} -> {target_path}: {message}")
        return

    os.symlink(target_path, link_path, target_is_directory=True)


def load_skill_names() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [str(skill["name"]) for skill in manifest.get("skills", [])]


def main() -> int:
    parser = argparse.ArgumentParser(description="把当前仓库的 skills 链接到本机 agent live skill 目录。")
    parser.add_argument("--agent", choices=sorted(DEFAULT_LIVE_ROOTS), default="codex", help="目标 agent，默认 codex")
    parser.add_argument("--live-root", help="live skill 根目录；不传时按 --agent 使用当前用户默认目录")
    parser.add_argument("--apply", action="store_true", help="实际移动已有目录并创建 junction/symlink；不加时只预览")
    args = parser.parse_args()

    live_root = Path(args.live_root or DEFAULT_LIVE_ROOTS[args.agent]).expanduser().resolve()
    backup_root = choose_backup_root(live_root, args.agent)
    actions: list[str] = []
    errors: list[str] = []

    for old_name, new_name in RENAMED_SKILLS.items():
        old_live_path = live_root / old_name
        if not path_lexists(old_live_path):
            continue
        if is_reparse_point(old_live_path):
            actions.append(f"移除已重命名的旧 live link: {old_live_path} (新名称: {new_name})")
            if args.apply:
                try:
                    remove_live_link(old_live_path)
                except OSError as exc:
                    errors.append(f"无法移除旧 live link: {old_live_path}: {exc}")
        else:
            backup_path = backup_root / old_name
            actions.append(f"备份已重命名的旧真实目录: {old_live_path} -> {backup_path}")
            if args.apply:
                try:
                    backup_root.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_live_path), str(backup_path))
                except OSError as exc:
                    errors.append(f"无法备份旧 live skill: {old_live_path}: {exc}")

    for skill_name in load_skill_names():
        repo_path = SKILLS_ROOT / skill_name
        live_path = live_root / skill_name

        if not (repo_path / "SKILL.md").exists():
            errors.append(f"仓库 skill 缺少 SKILL.md: {repo_path}")
            continue

        if same_target(live_path, repo_path):
            actions.append(f"已链接，跳过: {live_path}")
            continue

        if path_lexists(live_path):
            backup_path = backup_root / skill_name
            actions.append(f"移动已有 live skill 到备份: {live_path} -> {backup_path}")
            if args.apply:
                backup_root.mkdir(parents=True, exist_ok=True)
                shutil.move(str(live_path), str(backup_path))

        actions.append(f"创建 live link: {live_path} -> {repo_path}")
        if args.apply:
            live_root.mkdir(parents=True, exist_ok=True)
            create_live_link(live_path, repo_path)

    if errors:
        print("Link live skills failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    if not args.apply:
        print("Dry run only. Add --apply to make changes.")

    for action in actions:
        print(action)

    if args.apply:
        print("Live skill links updated.")
        if backup_root.exists():
            print(f"Backup root: {backup_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
