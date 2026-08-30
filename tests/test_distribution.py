import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "install-skills.py"
BUILDER = REPO_ROOT / "scripts" / "build-release.py"
MANIFEST = json.loads((REPO_ROOT / "manifest.json").read_text(encoding="utf-8"))
SKILL_NAMES = [str(item["name"]) for item in MANIFEST["skills"]]


def run_python(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def load_installer_module():
    scripts_path = str(REPO_ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("install_skills_for_test", INSTALLER)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载安装器模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerTests(unittest.TestCase):
    def test_default_roots_cover_codex_and_claude(self) -> None:
        module = load_installer_module()
        self.assertEqual(module.DEFAULT_TARGET_ROOTS["codex"].parts[-2:], (".codex", "skills"))
        self.assertEqual(module.DEFAULT_TARGET_ROOTS["claude"].parts[-2:], (".claude", "skills"))

    def test_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            result = run_python(INSTALLER, "install", "--target-root", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.exists())

    def test_full_install_verify_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installed = run_python(INSTALLER, "install", "--target-root", str(target), "--apply")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual({path.name for path in target.iterdir() if path.is_dir()}, set(SKILL_NAMES))
            self.assertTrue((target / ".patents-workflow-install.json").is_file())

            verified = run_python(INSTALLER, "verify", "--target-root", str(target))
            self.assertEqual(verified.returncode, 0, verified.stderr)

            preview = run_python(INSTALLER, "uninstall", "--target-root", str(target))
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue((target / SKILL_NAMES[0]).exists())

            removed = run_python(INSTALLER, "uninstall", "--target-root", str(target), "--apply")
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse((target / ".patents-workflow-install.json").exists())
            self.assertTrue(all(not (target / name).exists() for name in SKILL_NAMES))

    def test_existing_directory_requires_explicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            existing = target / SKILL_NAMES[0]
            existing.mkdir(parents=True)
            marker = existing / "user.txt"
            marker.write_text("keep", encoding="utf-8")

            refused = run_python(INSTALLER, "install", "--target-root", str(target), "--apply")
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

            replaced = run_python(
                INSTALLER,
                "install",
                "--target-root",
                str(target),
                "--apply",
                "--overwrite",
            )
            self.assertEqual(replaced.returncode, 0, replaced.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(run_python(INSTALLER, "verify", "--target-root", str(target)).returncode, 0)

    def test_modified_install_refuses_verify_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            self.assertEqual(
                run_python(INSTALLER, "install", "--target-root", str(target), "--apply").returncode,
                0,
            )
            changed = target / SKILL_NAMES[0] / "SKILL.md"
            changed.write_text(changed.read_text(encoding="utf-8") + "\nmodified\n", encoding="utf-8")
            self.assertEqual(run_python(INSTALLER, "verify", "--target-root", str(target)).returncode, 2)
            refused = run_python(INSTALLER, "uninstall", "--target-root", str(target), "--apply")
            self.assertEqual(refused.returncode, 2)
            self.assertTrue(all((target / name).exists() for name in SKILL_NAMES))

    def test_extra_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            self.assertEqual(
                run_python(INSTALLER, "install", "--target-root", str(target), "--apply").returncode,
                0,
            )
            (target / SKILL_NAMES[0] / "extra.txt").write_text("extra", encoding="utf-8")
            self.assertEqual(run_python(INSTALLER, "verify", "--target-root", str(target)).returncode, 2)

    def test_link_target_is_always_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            target.mkdir()
            external = root / "external"
            external.mkdir()
            marker = external / "marker.txt"
            marker.write_text("safe", encoding="utf-8")
            link = target / SKILL_NAMES[0]
            try:
                if os.name == "nt":
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(link), str(external)],
                        text=True,
                        capture_output=True,
                    )
                    if result.returncode != 0:
                        self.skipTest(f"当前 Windows 环境无法创建 junction: {result.stderr or result.stdout}")
                else:
                    os.symlink(external, link, target_is_directory=True)
                refused = run_python(
                    INSTALLER,
                    "install",
                    "--target-root",
                    str(target),
                    "--apply",
                    "--overwrite",
                )
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(marker.read_text(encoding="utf-8"), "safe")
            finally:
                if os.path.lexists(link):
                    if os.name == "nt":
                        link.rmdir()
                    else:
                        link.unlink()

    def test_install_failure_restores_existing_directories(self) -> None:
        module = load_installer_module()
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            target.mkdir()
            for name in SKILL_NAMES:
                existing = target / name
                existing.mkdir()
                (existing / "sentinel.txt").write_text(name, encoding="utf-8")
            manifest = module.load_manifest()
            inventories = module.source_inventories(manifest)
            original_replace = module.os.replace
            stage_moves = 0

            def fail_once(source, destination):
                nonlocal stage_moves
                source_path = Path(source)
                if source_path.parent.name.startswith(".patents-workflow-stage-"):
                    stage_moves += 1
                    if stage_moves == 2:
                        raise OSError("injected install failure")
                return original_replace(source, destination)

            with mock.patch.object(module.os, "replace", side_effect=fail_once):
                with self.assertRaises(OSError):
                    module.apply_install(target, manifest, inventories)
            for name in SKILL_NAMES:
                self.assertEqual((target / name / "sentinel.txt").read_text(encoding="utf-8"), name)
            self.assertFalse((target / module.RECEIPT_NAME).exists())
            self.assertFalse(any(path.name.startswith(".patents-workflow-") for path in target.iterdir()))


class ReleaseBuildTests(unittest.TestCase):
    def test_release_is_deterministic_and_curated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw)
            first = run_python(BUILDER, "--output-dir", str(output))
            self.assertEqual(first.returncode, 0, first.stderr)
            archive = output / "patents-workflow-v2.1.0-full.zip"
            first_bytes = archive.read_bytes()
            first_hash = hashlib.sha256(first_bytes).hexdigest()

            second = run_python(BUILDER, "--output-dir", str(output))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_bytes, archive.read_bytes())
            checksum = (output / f"{archive.name}.sha256").read_text(encoding="utf-8")
            self.assertEqual(checksum, f"{first_hash}  {archive.name}\n")

            prefix = "patents-workflow-2.1.0/"
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())
            self.assertIn(prefix + "scripts/install-skills.py", names)
            self.assertIn(prefix + "LICENSE", names)
            self.assertIn(prefix + "THIRD_PARTY_NOTICES.md", names)
            self.assertIn(prefix + "third_party/provenance.json", names)
            for skill_name in SKILL_NAMES:
                self.assertIn(prefix + f"skills/{skill_name}/SKILL.md", names)
            forbidden = ("scripts/dev/", ".git/", "exports/", "grill-me-sessions/", "__pycache__", RECEIPT_NAME)
            for name in names:
                self.assertFalse(any(part in name for part in forbidden), name)


RECEIPT_NAME = ".patents-workflow-install.json"


if __name__ == "__main__":
    unittest.main()
