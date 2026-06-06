#!/usr/bin/env python3
"""Patent Repo Scout - repository metadata collection.

This script only writes a project-level repo profile. Recommendation,
brainstorming, and next-step selection remain in the cn-patent-repo-scout skill.
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_VERSION = "0.2.0"

DEFAULT_EXCLUDE = {
    ".git", "build", "out", "third_party", "thirdparty", "vendor",
    "node_modules", "__pycache__", ".agents", "prebuilts", "tool"
}

DEFAULT_WEIGHTS = {
    "innovation": 0.40,
    "evidence_strength": 0.25,
    "protection_value": 0.20,
    "clarity": 0.15,
}

ALGO_KEYWORDS = re.compile(
    r"\b(optimize|solve|predict|filter|transform|encode|decode|compress|"
    r"schedule|allocate|detect|track|fuse|calibrate|interpolate|"
    r"estimate|segment|classify|cluster|inference|quantize|"
    r"stabilize|denoise|align|register|reconstruct)\b",
    re.IGNORECASE
)

DOC_PATTERNS = re.compile(
    r"(README|DESIGN|design[-_]doc|spec|experiment|benchmark|test[-_]data)",
    re.IGNORECASE
)


def load_patentignore(root: Path) -> set:
    ignore_file = root / ".patentignore"
    if not ignore_file.exists():
        return set()
    return {
        line.strip()
        for line in ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.startswith("#")
    }


def load_exclude_file(path: str) -> set:
    if not path:
        return set()
    exclude_file = Path(path)
    if not exclude_file.exists():
        raise FileNotFoundError(f"Exclude file not found: {exclude_file}")
    return {
        line.strip()
        for line in exclude_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.startswith("#")
    }


def parse_excludes(values: list) -> set:
    excludes = set()
    for value in values:
        excludes.update(part.strip() for part in value.split(",") if part.strip())
    return excludes


def is_excluded(path: Path, root: Path, excludes: set) -> bool:
    rel_parts = path.relative_to(root).parts
    return any(part in excludes for part in rel_parts)


def get_git_heat(root: Path, excludes: set) -> dict:
    heat = {}
    try:
        result = subprocess.run(
            ["git", "log", "--format=", "--numstat", "--since=1 year ago"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root, timeout=60
        )
        if result.returncode != 0:
            return heat
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2]:
                fpath = Path(parts[2])
                if len(fpath.parts) >= 2 and not any(p in excludes for p in fpath.parts):
                    module = str(Path(*fpath.parts[:3]))
                    heat[module] = heat.get(module, 0) + 1
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return heat


def get_contributors(root: Path, module_path: str) -> list:
    try:
        result = subprocess.run(
            ["git", "shortlog", "-sn", "--", module_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root, timeout=30
        )
        if result.returncode == 0:
            contributors = []
            for line in result.stdout.splitlines()[:5]:
                parts = line.strip().split("\t", 1)
                if len(parts) == 2:
                    contributors.append(parts[1].strip())
            return contributors
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def scan_module(root: Path, module_path: Path, excludes: set) -> Optional[dict]:
    files = []
    total_lines = 0
    algo_hits = 0
    func_count = 0
    has_experiment = False
    has_design_doc = False
    code_exts = {".py", ".cpp", ".c", ".h", ".hpp", ".rs", ".go", ".java", ".js", ".ts"}

    for f in module_path.rglob("*"):
        if not f.is_file() or is_excluded(f, root, excludes):
            continue
        files.append(f)
        if DOC_PATTERNS.search(f.name):
            if "test" in f.name.lower() or "bench" in f.name.lower() or "experiment" in f.name.lower():
                has_experiment = True
            else:
                has_design_doc = True
        if f.suffix in code_exts:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                total_lines += len(lines)
                algo_hits += len(ALGO_KEYWORDS.findall(content))
                func_count += len(re.findall(
                    r"^\s*(?:def |fn |func |function |void |int |bool |auto |static )\w+\s*\(",
                    content, re.MULTILINE
                ))
            except OSError:
                pass

    file_count = len(files)
    if file_count == 0:
        return None

    algo_density = algo_hits / max(total_lines, 1)
    complexity = min(1.0, (func_count / max(file_count, 1)) * 0.1 + (total_lines / 10000) * 0.3)

    return {
        "path": str(module_path.relative_to(root)),
        "file_count": file_count,
        "total_lines": total_lines,
        "func_count": func_count,
        "algo_keyword_density": round(algo_density, 4),
        "complexity_score": round(complexity, 3),
        "has_experiment": has_experiment,
        "has_design_doc": has_design_doc,
    }


def discover_modules(root: Path, excludes: set, depth: int = 3) -> list:
    modules = set()
    for item in root.rglob("*"):
        if not item.is_dir():
            continue
        rel = item.relative_to(root)
        if len(rel.parts) > depth or is_excluded(item, root, excludes):
            continue
        has_code = any(
            f.suffix in {".py", ".cpp", ".c", ".h", ".hpp", ".rs", ".go", ".java", ".js", ".ts"}
            for f in item.iterdir() if f.is_file()
        )
        if has_code and len(rel.parts) >= 2:
            modules.add(item)
    return sorted(modules)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Patent Repo Scout - scanner")
    parser.add_argument("root", nargs="?", default=".", help="Repository root directory")
    parser.add_argument("-o", "--output", default="patent/repo-scout/repo-profile.json")
    parser.add_argument("--depth", type=int, default=3, help="Module discovery depth")
    parser.add_argument("--top", type=int, default=30, help="Max modules to report")
    parser.add_argument("--exclude", action="append", default=[], help="Extra exclude names, comma-separated or repeated")
    parser.add_argument("--exclude-file", default="", help="File with extra exclude names")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root directory not found: {root}")

    excludes = DEFAULT_EXCLUDE | load_patentignore(root) | parse_excludes(args.exclude) | load_exclude_file(args.exclude_file)

    git_heat = get_git_heat(root, excludes)
    max_heat = max(git_heat.values()) if git_heat else 1

    modules = discover_modules(root, excludes, args.depth)
    results = []

    for mod in modules:
        info = scan_module(root, mod, excludes)
        if info is None:
            continue
        rel_path = info["path"]
        raw_heat = git_heat.get(rel_path, 0)
        info["git_heat"] = round(raw_heat / max_heat, 3) if max_heat else 0
        info["top_contributors"] = get_contributors(root, rel_path)
        results.append(info)

    results.sort(key=lambda m: (
        m["git_heat"] * 0.3 +
        m["algo_keyword_density"] * 100 * 0.4 +
        m["complexity_score"] * 0.2 +
        (0.1 if m["has_experiment"] else 0)
    ), reverse=True)
    results = results[:args.top]

    output = {
        "script_version": SCRIPT_VERSION,
        "scan_root": str(root),
        "scan_time": datetime.now().isoformat(),
        "exclude_patterns": sorted(excludes),
        "weights": DEFAULT_WEIGHTS,
        "modules": results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Scan complete: {len(results)} modules -> {out_path}")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
