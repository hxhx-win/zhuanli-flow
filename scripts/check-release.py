import json
import re
import subprocess
import sys
from pathlib import Path

from _release_utils import file_inventory, tree_sha256


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifest.json"
VERSION_PATH = REPO_ROOT / "VERSION"
README_PATH = REPO_ROOT / "README.md"
SKILLS_ROOT = REPO_ROOT / "skills"
PROVENANCE_PATH = REPO_ROOT / "third_party" / "provenance.json"
LICENSE_PATH = REPO_ROOT / "LICENSE"
THIRD_PARTY_NOTICES_PATH = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
SECURITY_PATH = REPO_ROOT / "SECURITY.md"
INSTALLER_PATH = REPO_ROOT / "scripts" / "install-skills.py"
BUILD_SCRIPT_PATH = REPO_ROOT / "scripts" / "build-release.py"
DEV_LINK_PATH = REPO_ROOT / "scripts" / "dev" / "link-live-skills.py"
DEV_CHECK_PATH = REPO_ROOT / "scripts" / "dev" / "check-live-links.py"
EXPECTED_CORE_COUNT = 9
EXPECTED_VENDORED_COUNT = 6
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx", ".pptx", ".xlsx"}
CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SECRET_PATTERN = re.compile(
    r"(bearer\s+[A-Za-z0-9._-]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN .*PRIVATE KEY)",
    re.IGNORECASE,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        REPO_ROOT / raw.decode("utf-8")
        for raw in result.stdout.split(b"\0")
        if raw
    ]


def add_cache_errors(errors: list[str], tracked_files: list[Path]) -> None:
    for path in tracked_files:
        relative = path.relative_to(REPO_ROOT)
        if any(part in CACHE_DIR_NAMES for part in relative.parts):
            errors.append(f"不应提交缓存目录: {path}")
        if path.suffix in {".pyc", ".pyo"}:
            errors.append(f"不应提交生成文件: {path}")


def add_secret_errors(errors: list[str], tracked_files: list[Path]) -> None:
    current_script = Path(__file__).resolve()
    for path in tracked_files:
        if not path.exists():
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


def add_provenance_errors(errors: list[str], manifest: dict) -> None:
    if not PROVENANCE_PATH.exists():
        errors.append("third_party/provenance.json not found.")
        return
    try:
        provenance = json.loads(read_text(PROVENANCE_PATH))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"无法读取 third_party/provenance.json: {exc}")
        return

    vendored_names = {
        str(skill.get("name", ""))
        for skill in manifest.get("skills", [])
        if skill.get("role") == "vendored"
    }
    entries = provenance.get("skills")
    if not isinstance(entries, list):
        errors.append("third_party/provenance.json.skills 必须是数组。")
        return
    entry_names = {str(entry.get("name", "")) for entry in entries if isinstance(entry, dict)}
    if entry_names != vendored_names:
        errors.append(f"vendored 来源记录集合不一致: provenance={sorted(entry_names)}, manifest={sorted(vendored_names)}")

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("vendored 来源记录必须是对象。")
            continue
        name = str(entry.get("name", ""))
        if entry.get("source_revision") is not None:
            errors.append(f"未验证的 vendored source_revision 必须保持 null: {name}")
        if entry.get("revision_status") != "not-recorded-at-import":
            errors.append(f"vendored revision_status 非预期: {name}")
        if not entry.get("source_repository") or not entry.get("declared_license"):
            errors.append(f"vendored 来源或许可证缺失: {name}")
        for relative_license in entry.get("license_files", []):
            license_path = REPO_ROOT / str(relative_license)
            if not license_path.is_file():
                errors.append(f"vendored 许可证文件不存在: {relative_license}")
        skill_root = SKILLS_ROOT / name
        try:
            actual_hash = tree_sha256(file_inventory(skill_root))
        except (OSError, ValueError) as exc:
            errors.append(f"无法计算 vendored 目录摘要 {name}: {exc}")
            continue
        if entry.get("tree_sha256") != actual_hash:
            errors.append(f"vendored 目录摘要不一致: {name}, expected={entry.get('tree_sha256')}, actual={actual_hash}")


def main() -> int:
    errors: list[str] = []

    try:
        tracked_files = get_tracked_files()
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        print(f"无法读取 Git 跟踪文件列表: {exc}", file=sys.stderr)
        return 1

    if not MANIFEST_PATH.exists():
        print(f"manifest.json not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = json.loads(read_text(MANIFEST_PATH))

    roles = [str(skill.get("role", "")) for skill in manifest.get("skills", [])]
    if roles.count("core") != EXPECTED_CORE_COUNT:
        errors.append(f"核心 Skill 数量必须为 {EXPECTED_CORE_COUNT}，实际为 {roles.count('core')}。")
    if roles.count("vendored") != EXPECTED_VENDORED_COUNT:
        errors.append(f"vendored Skill 数量必须为 {EXPECTED_VENDORED_COUNT}，实际为 {roles.count('vendored')}。")
    if len(roles) != EXPECTED_CORE_COUNT + EXPECTED_VENDORED_COUNT:
        errors.append(f"manifest Skill 总数必须为 {EXPECTED_CORE_COUNT + EXPECTED_VENDORED_COUNT}，实际为 {len(roles)}。")

    if VERSION_PATH.exists():
        version = read_text(VERSION_PATH).strip()
    else:
        version = ""
        errors.append("VERSION not found.")

    if manifest.get("version") != version:
        errors.append(f"VERSION ({version}) 与 manifest.json.version ({manifest.get('version')}) 不一致。")

    if README_PATH.exists():
        readme = read_text(README_PATH)
        if version and version not in readme:
            errors.append(f"README.md 未提及当前版本: {version}")
    else:
        readme = ""
        errors.append("README.md not found.")

    if not LICENSE_PATH.exists() or not read_text(LICENSE_PATH).startswith("MIT License\n"):
        errors.append("LICENSE 必须是 MIT License。")
    if not THIRD_PARTY_NOTICES_PATH.is_file():
        errors.append("THIRD_PARTY_NOTICES.md not found.")
    if not SECURITY_PATH.is_file():
        errors.append("SECURITY.md not found.")
    for required_path in (INSTALLER_PATH, BUILD_SCRIPT_PATH, DEV_LINK_PATH, DEV_CHECK_PATH):
        if not required_path.is_file():
            errors.append(f"必要脚本不存在: {required_path.relative_to(REPO_ROOT)}")
    for retired_path in (REPO_ROOT / "scripts" / "link-live-skills.py", REPO_ROOT / "scripts" / "check-live-links.py"):
        if retired_path.exists():
            errors.append(f"live-link 开发脚本仍位于公开脚本目录: {retired_path.relative_to(REPO_ROOT)}")

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

    add_cache_errors(errors, tracked_files)
    add_secret_errors(errors, tracked_files)
    add_provenance_errors(errors, manifest)

    if errors:
        print("Release check failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Release check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
