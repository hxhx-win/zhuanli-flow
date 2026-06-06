import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifest.json"
VERSION_PATH = REPO_ROOT / "VERSION"
README_PATH = REPO_ROOT / "README.md"
SKILLS_ROOT = REPO_ROOT / "skills"
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx", ".pptx", ".xlsx"}
CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SECRET_PATTERN = re.compile(
    r"(bearer\s+[A-Za-z0-9._-]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN .*PRIVATE KEY)",
    re.IGNORECASE,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add_cache_errors(errors: list[str]) -> None:
    for root, dirs, files in os.walk(REPO_ROOT):
        root_path = Path(root)
        if ".git" in root_path.parts:
            dirs[:] = []
            continue

        for dirname in dirs:
            if dirname in CACHE_DIR_NAMES:
                errors.append(f"不应提交缓存目录: {root_path / dirname}")

        for filename in files:
            if Path(filename).suffix in {".pyc", ".pyo"}:
                errors.append(f"不应提交生成文件: {root_path / filename}")


def add_secret_errors(errors: list[str]) -> None:
    current_script = Path(__file__).resolve()
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if path.resolve() == current_script:
            continue
        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue

        try:
            content = read_text(path)
        except UnicodeDecodeError:
            continue

        if SECRET_PATTERN.search(content):
            errors.append(f"疑似 secret pattern: {path}")


def main() -> int:
    errors: list[str] = []

    if not MANIFEST_PATH.exists():
        print(f"manifest.json not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = json.loads(read_text(MANIFEST_PATH))

    if VERSION_PATH.exists():
        version = read_text(VERSION_PATH).strip()
    else:
        version = ""
        errors.append("VERSION not found.")

    if manifest.get("version") != version:
        errors.append(f"VERSION ({version}) 与 manifest.json.version ({manifest.get('version')}) 不一致。")

    if README_PATH.exists():
        readme = read_text(README_PATH)
    else:
        readme = ""
        errors.append("README.md not found.")

    for skill in manifest.get("skills", []):
        skill_name = str(skill.get("name", ""))
        skill_path = SKILLS_ROOT / skill_name
        skill_md = skill_path / "SKILL.md"

        if not skill_path.exists():
            errors.append(f"Skill 目录不存在: skills/{skill_name}")
            continue

        if not skill_md.exists():
            errors.append(f"SKILL.md 不存在: skills/{skill_name}/SKILL.md")
            continue

        text = read_text(skill_md)
        frontmatter_match = re.match(r"(?s)^---\s*(.*?)\s*---", text)
        if not frontmatter_match:
            errors.append(f"SKILL.md frontmatter 不存在: skills/{skill_name}/SKILL.md")
        else:
            frontmatter = frontmatter_match.group(1)
            if not re.search(r"(?m)^name\s*:", frontmatter):
                errors.append(f"SKILL.md frontmatter 缺少 name: skills/{skill_name}/SKILL.md")
            if not re.search(r"(?m)^description\s*:", frontmatter):
                errors.append(f"SKILL.md frontmatter 缺少 description: skills/{skill_name}/SKILL.md")

        if readme and skill_name not in readme:
            errors.append(f"README.md 未提及 manifest skill: {skill_name}")

    add_cache_errors(errors)
    add_secret_errors(errors)

    if errors:
        print("Release check failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Release check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
