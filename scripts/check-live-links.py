import argparse
import json
import stat
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifest.json"
SKILLS_ROOT = REPO_ROOT / "skills"
DEFAULT_LIVE_ROOTS = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}


def is_reparse_point(path: Path) -> bool:
    try:
        attrs = path.stat(follow_symlinks=False).st_file_attributes
    except AttributeError:
        return path.is_symlink()
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def normalize(path: Path) -> str:
    return str(path.resolve(strict=True)).rstrip("\\/").casefold()


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 agent live skill 是否指向仓库内 skills 目录。")
    parser.add_argument("--agent", choices=sorted(DEFAULT_LIVE_ROOTS), default="codex", help="目标 agent，默认 codex")
    parser.add_argument("--live-root", help="live skill 根目录；不传时按 --agent 使用当前用户默认目录")
    args = parser.parse_args()

    live_root = Path(args.live_root or DEFAULT_LIVE_ROOTS[args.agent]).expanduser()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    for skill in manifest.get("skills", []):
        skill_name = str(skill.get("name", ""))
        live_path = live_root / skill_name
        repo_path = SKILLS_ROOT / skill_name

        if not live_path.exists():
            errors.append(f"Live skill 路径不存在: {live_path}")
            continue

        if not is_reparse_point(live_path):
            errors.append(f"Live skill 不是 live link/reparse point: {live_path}")
            continue

        try:
            resolved_target = normalize(live_path)
            expected_target = normalize(repo_path)
        except OSError as exc:
            errors.append(f"无法解析 live skill 目标: {live_path}: {exc}")
            continue

        if resolved_target != expected_target:
            errors.append(f"Live skill 目标不一致: {live_path} -> {resolved_target}, expected {expected_target}")

    if errors:
        print("Live link check failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Live link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
