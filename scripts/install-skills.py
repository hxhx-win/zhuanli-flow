import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from _release_utils import file_inventory, is_link_like, path_lexists, sha256_file, tree_sha256


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifest.json"
SKILLS_ROOT = REPO_ROOT / "skills"
RECEIPT_NAME = ".zhuanli-flow-install.json"
DEFAULT_TARGET_ROOTS = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


class ConflictError(Exception):
    pass


def load_manifest() -> dict:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 manifest.json: {exc}") from exc
    skills = manifest.get("skills")
    if not isinstance(skills, list) or not skills:
        raise RuntimeError("manifest.json.skills 必须是非空数组")
    names = [str(item.get("name", "")) for item in skills if isinstance(item, dict)]
    if len(names) != len(skills) or any(not name for name in names) or len(set(names)) != len(names):
        raise RuntimeError("manifest.json 中存在空白、重复或非法 Skill 名称")
    return manifest


def skill_names(manifest: dict) -> list[str]:
    return [str(item["name"]) for item in manifest["skills"]]


def target_root_from_args(args: argparse.Namespace) -> Path:
    selected = Path(args.target_root) if args.target_root else DEFAULT_TARGET_ROOTS[args.agent]
    return selected.expanduser().absolute()


def source_inventories(manifest: dict) -> dict[str, dict[str, str]]:
    inventories: dict[str, dict[str, str]] = {}
    for name in skill_names(manifest):
        source = SKILLS_ROOT / name
        if not (source / "SKILL.md").is_file():
            raise RuntimeError(f"发行包中的 Skill 缺少 SKILL.md: {source}")
        try:
            inventories[name] = file_inventory(source)
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"无法读取发行 Skill {name}: {exc}") from exc
    return inventories


def preflight_install(target_root: Path, names: list[str], overwrite: bool) -> None:
    receipt_path = target_root / RECEIPT_NAME
    if path_lexists(receipt_path) and is_link_like(receipt_path):
        raise ConflictError(f"安装收据不能是链接或 reparse point: {receipt_path}")

    conflicts: list[str] = []
    links: list[str] = []
    for name in names:
        target = target_root / name
        if not path_lexists(target):
            continue
        if is_link_like(target):
            links.append(str(target))
        elif not target.is_dir():
            conflicts.append(f"目标不是目录: {target}")
        elif not overwrite:
            conflicts.append(f"目标目录已存在: {target}")

    if links:
        details = "\n - ".join(links)
        raise ConflictError(
            "安装器拒绝覆盖 live link、symlink、junction 或 reparse point；"
            f"请使用 scripts/dev/ 下的开发者工具处理:\n - {details}"
        )
    if conflicts:
        suffix = "；如确认覆盖，请重新运行并添加 --overwrite" if not overwrite else ""
        raise ConflictError("安装预检失败:\n - " + "\n - ".join(conflicts) + suffix)


def build_receipt(manifest: dict, inventories: dict[str, dict[str, str]]) -> dict:
    return {
        "schema_version": 1,
        "package_name": str(manifest.get("name", "zhuanli-flow")),
        "version": str(manifest.get("version", "")),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "installed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "skills": {
            name: {
                "tree_sha256": tree_sha256(inventory),
                "files": inventory,
            }
            for name, inventory in sorted(inventories.items())
        },
    }


def write_receipt_atomic(path: Path, receipt: dict) -> None:
    payload = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def remove_real_tree(path: Path) -> None:
    if is_link_like(path):
        raise RuntimeError(f"拒绝删除链接或 reparse point: {path}")
    shutil.rmtree(path)


def apply_install(
    target_root: Path,
    manifest: dict,
    inventories: dict[str, dict[str, str]],
) -> list[str]:
    names = skill_names(manifest)
    target_root.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix=".zhuanli-flow-stage-", dir=target_root))
    rollback_root = target_root / f".zhuanli-flow-rollback-{uuid.uuid4().hex}"
    installed: list[str] = []
    moved_old: list[str] = []
    warnings: list[str] = []
    try:
        for name in names:
            staged = stage_root / name
            shutil.copytree(SKILLS_ROOT / name, staged)
            if file_inventory(staged) != inventories[name]:
                raise RuntimeError(f"临时复制校验失败: {name}")

        rollback_root.mkdir()
        for name in names:
            target = target_root / name
            if target.exists():
                os.replace(target, rollback_root / name)
                moved_old.append(name)
            os.replace(stage_root / name, target)
            installed.append(name)

        write_receipt_atomic(target_root / RECEIPT_NAME, build_receipt(manifest, inventories))
    except Exception:
        rollback_errors: list[str] = []
        for name in reversed(installed):
            target = target_root / name
            try:
                if target.exists():
                    remove_real_tree(target)
            except OSError as exc:
                rollback_errors.append(f"无法移除失败安装 {target}: {exc}")
        for name in reversed(moved_old):
            original = rollback_root / name
            target = target_root / name
            try:
                if original.exists() and not target.exists():
                    os.replace(original, target)
            except OSError as exc:
                rollback_errors.append(f"无法恢复 {target}: {exc}")
        if rollback_errors:
            print("回滚未完全成功:", file=sys.stderr)
            for error in rollback_errors:
                print(f" - {error}", file=sys.stderr)
            print(f"恢复数据可能保留在: {rollback_root}", file=sys.stderr)
        elif rollback_root.exists():
            shutil.rmtree(rollback_root)
        raise
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root, ignore_errors=True)

    try:
        shutil.rmtree(rollback_root)
    except OSError as exc:
        warnings.append(f"安装成功，但无法清理临时回滚目录 {rollback_root}: {exc}")
    return warnings


def load_receipt(target_root: Path) -> dict:
    receipt_path = target_root / RECEIPT_NAME
    if not path_lexists(receipt_path):
        raise ConflictError(f"安装收据不存在: {receipt_path}")
    if is_link_like(receipt_path) or not receipt_path.is_file():
        raise ConflictError(f"安装收据必须是普通文件: {receipt_path}")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取安装收据: {exc}") from exc
    if not isinstance(receipt, dict):
        raise RuntimeError("安装收据根节点必须是对象")
    return receipt


def verify_receipt(target_root: Path, manifest: dict, receipt: dict) -> list[str]:
    errors: list[str] = []
    expected_names = skill_names(manifest)
    if receipt.get("schema_version") != 1:
        errors.append(f"不支持的收据版本: {receipt.get('schema_version')}")
    if receipt.get("package_name") != manifest.get("name"):
        errors.append("收据 package_name 与当前发行包不一致")
    if receipt.get("version") != manifest.get("version"):
        errors.append(f"收据版本 {receipt.get('version')} 与当前发行包版本 {manifest.get('version')} 不一致")
    if receipt.get("manifest_sha256") != sha256_file(MANIFEST_PATH):
        errors.append("收据中的 manifest SHA-256 与当前发行包不一致")

    recorded_skills = receipt.get("skills")
    if not isinstance(recorded_skills, dict):
        return errors + ["收据 skills 必须是对象"]
    if set(recorded_skills) != set(expected_names):
        errors.append("收据中的 Skill 集合与 manifest 不一致")

    for name in expected_names:
        target = target_root / name
        recorded = recorded_skills.get(name)
        if not isinstance(recorded, dict):
            errors.append(f"收据缺少 Skill: {name}")
            continue
        if is_link_like(target):
            errors.append(f"已安装 Skill 不能是链接或 reparse point: {target}")
            continue
        try:
            actual_inventory = file_inventory(target)
        except (OSError, ValueError) as exc:
            errors.append(f"无法校验 {name}: {exc}")
            continue
        expected_inventory = recorded.get("files")
        if not isinstance(expected_inventory, dict) or actual_inventory != expected_inventory:
            errors.append(f"Skill 文件集合或内容已变化: {name}")
            continue
        if tree_sha256(actual_inventory) != recorded.get("tree_sha256"):
            errors.append(f"Skill 目录摘要不一致: {name}")
    return errors


def apply_uninstall(target_root: Path, names: list[str]) -> None:
    holding_root = target_root / f".zhuanli-flow-uninstall-{uuid.uuid4().hex}"
    moved: list[str] = []
    receipt_path = target_root / RECEIPT_NAME
    receipt_moved = False
    holding_root.mkdir()
    try:
        for name in names:
            os.replace(target_root / name, holding_root / name)
            moved.append(name)
        os.replace(receipt_path, holding_root / RECEIPT_NAME)
        receipt_moved = True
    except Exception:
        if receipt_moved and not receipt_path.exists():
            os.replace(holding_root / RECEIPT_NAME, receipt_path)
        for name in reversed(moved):
            original = holding_root / name
            target = target_root / name
            if original.exists() and not target.exists():
                os.replace(original, target)
        if holding_root.exists():
            holding_root.rmdir()
        raise
    shutil.rmtree(holding_root)


def command_install(args: argparse.Namespace, manifest: dict) -> int:
    target_root = target_root_from_args(args)
    inventories = source_inventories(manifest)
    preflight_install(target_root, skill_names(manifest), args.overwrite)
    print(f"目标目录: {target_root}")
    print(f"将安装 {len(inventories)} 个 Skill，版本 {manifest.get('version')}")
    if not args.apply:
        print("Dry run only. Add --apply to install.")
        return 0
    warnings = apply_install(target_root, manifest, inventories)
    print("Skill 安装完成。")
    for warning in warnings:
        print(f"警告: {warning}")
    return 0


def command_verify(args: argparse.Namespace, manifest: dict) -> int:
    target_root = target_root_from_args(args)
    receipt = load_receipt(target_root)
    errors = verify_receipt(target_root, manifest, receipt)
    if errors:
        raise ConflictError("安装校验失败:\n - " + "\n - ".join(errors))
    print(f"安装校验通过: {target_root} ({manifest.get('version')}, {len(skill_names(manifest))} 个 Skill)")
    return 0


def command_uninstall(args: argparse.Namespace, manifest: dict) -> int:
    target_root = target_root_from_args(args)
    receipt = load_receipt(target_root)
    errors = verify_receipt(target_root, manifest, receipt)
    if errors:
        raise ConflictError("拒绝卸载，安装内容已变化:\n - " + "\n - ".join(errors))
    names = skill_names(manifest)
    print(f"将卸载 {len(names)} 个 Skill: {target_root}")
    if not args.apply:
        print("Dry run only. Add --apply to uninstall.")
        return 0
    apply_uninstall(target_root, names)
    print("Skill 卸载完成。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="安装、校验或卸载 ZhuanliFlow 完整 Skill 套件。")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "verify", "uninstall"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--agent", choices=sorted(DEFAULT_TARGET_ROOTS), default="codex")
        subparser.add_argument("--target-root", help="覆盖 --agent 的默认 Skill 根目录")
        if command in {"install", "uninstall"}:
            subparser.add_argument("--apply", action="store_true", help="实际修改文件；默认只预览")
        if command == "install":
            subparser.add_argument("--overwrite", action="store_true", help="覆盖已有真实 Skill 目录；链接始终拒绝")
    return parser


def main() -> int:
    configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args()
    try:
        manifest = load_manifest()
        if args.command == "install":
            return command_install(args, manifest)
        if args.command == "verify":
            return command_verify(args, manifest)
        return command_uninstall(args, manifest)
    except ConflictError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"工具错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
