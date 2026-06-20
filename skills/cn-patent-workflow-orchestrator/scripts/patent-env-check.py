#!/usr/bin/env python3
"""Detect available tools and output capability matrix as JSON."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import platform
from pathlib import Path


def check_command(name, version_flag="--version"):
    """Probe a command by name. Treat Ubuntu snap stubs (which exit non-zero with
    'requires the chromium snap') as unavailable so noise is not reported as ready."""
    path = shutil.which(name)
    if not path:
        return {"available": False, "version": None, "path": None}
    try:
        result = subprocess.run([path, version_flag], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
    except Exception:
        return {"available": True, "version": "unknown", "path": path}
    output = (result.stdout or result.stderr or "").strip()
    version = output.split('\n')[0] if output else "unknown"
    if result.returncode != 0 and ("snap" in output.lower() or "not found" in output.lower()):
        return {"available": False, "version": version, "path": path}
    return {"available": True, "version": version, "path": path}


def _find_puppeteer_chrome():
    """Locate the chrome binary that npm i -g @mermaid-js/mermaid-cli auto-downloads
    into the Puppeteer cache. Used by render-mermaid-figures.py for actual rendering;
    this is the same source of truth on Linux and macOS."""
    cache_roots = [
        Path.home() / ".cache" / "puppeteer" / "chrome",
        Path.home() / "Library" / "Caches" / "puppeteer" / "chrome",
    ]
    for cache_root in cache_roots:
        if not cache_root.is_dir():
            continue
        version_dirs = sorted(
            (d for d in cache_root.iterdir() if d.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        )
        for version_dir in version_dirs:
            for sub in version_dir.iterdir():
                if not sub.is_dir():
                    continue
                linux_chrome = sub / "chrome"
                if linux_chrome.is_file():
                    return linux_chrome
                win_chrome = sub / "chrome.exe"
                if win_chrome.is_file():
                    return win_chrome
                for app in sub.glob("*.app"):
                    macos_dir = app / "Contents" / "MacOS"
                    if not macos_dir.is_dir():
                        continue
                    for binary in macos_dir.iterdir():
                        if binary.is_file():
                            return binary
    return None


def find_chromium():
    """Mermaid rendering goes through mmdc → Puppeteer → Chrome. The single
    cross-platform source of truth is the Puppeteer cache populated by mmdc's
    install. Fall back to system chrome on PATH only if the cache is missing."""
    pup = _find_puppeteer_chrome()
    if pup is not None:
        try:
            result = subprocess.run([str(pup), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            output = (result.stdout or result.stderr or "").strip()
            return {"available": True, "version": output.split('\n')[0] if output else "puppeteer-cache",
                    "path": str(pup), "source": "puppeteer-cache"}
        except Exception:
            return {"available": True, "version": "puppeteer-cache", "path": str(pup), "source": "puppeteer-cache"}
    for name in ("google-chrome", "chromium", "chromium-browser"):
        cap = check_command(name)
        if cap["available"]:
            cap["source"] = "PATH"
            return cap
    return {"available": False, "version": None, "path": None,
            "hint": "run `npm i -g @mermaid-js/mermaid-cli` to populate ~/.cache/puppeteer"}


def find_libreoffice():
    """LibreOffice ships as `libreoffice` on Linux and `soffice` everywhere; mac
    only exposes it inside /Applications/LibreOffice.app, never on PATH."""
    for name in ("libreoffice", "soffice"):
        cap = check_command(name)
        if cap["available"]:
            return cap
    if platform.system() == "Darwin":
        for p in (Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
                  Path.home() / "Applications" / "LibreOffice.app" / "Contents" / "MacOS" / "soffice"):
            if p.is_file():
                try:
                    result = subprocess.run([str(p), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
                    output = (result.stdout or result.stderr or "").strip()
                    return {"available": True, "version": output.split('\n')[0] if output else "unknown", "path": str(p)}
                except Exception:
                    return {"available": True, "version": "unknown", "path": str(p)}
    return {"available": False, "version": None, "path": None}


def check_python_package(name):
    try:
        mod = __import__(name)
        version = getattr(mod, '__version__', 'installed')
        return {"available": True, "version": version}
    except ImportError:
        return {"available": False, "version": None}


PANDOC_MIN_VERSION = (2, 0)


def _parse_pandoc_version(version_str):
    """Pull MAJOR.MINOR.PATCH out of `pandoc 2.5` / `pandoc.exe 3.1.9` lines."""
    import re
    m = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', version_str or '')
    if not m:
        return None
    return tuple(int(g) for g in m.groups(default='0'))


def check_pandoc():
    """pandoc + version check. The export script uses tex_math_dollars+raw_tex
    which requires pandoc >= 2.0; older versions silently mis-render formulas."""
    cap = check_command("pandoc")
    if not cap["available"]:
        return cap
    parsed = _parse_pandoc_version(cap.get("version", ""))
    cap["parsed_version"] = parsed
    cap["version_ok"] = bool(parsed and parsed >= PANDOC_MIN_VERSION)
    cap["min_required"] = ".".join(str(x) for x in PANDOC_MIN_VERSION)
    return cap


REQUIRED_FONTS = {
    "songti": ["SimSun", "宋体", "Songti SC", "STSong", "NSimSun", "FangSong"],
    "times_new_roman": ["Times New Roman", "Times", "Liberation Serif"],
    "cambria_math": ["Cambria Math", "Latin Modern Math", "STIX Two Math", "STIX Math"],
}


def _list_fonts_via_fc_list():
    """Linux/mac (with brew fontconfig) — use fc-list and return a single big string."""
    fc = shutil.which("fc-list")
    if not fc:
        return None
    try:
        result = subprocess.run([fc, ":", "family"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def _list_fonts_via_macos_system_profiler():
    """macOS without fontconfig — fall back to system_profiler SPFontsDataType."""
    if platform.system() != "Darwin":
        return None
    sp = shutil.which("system_profiler")
    if not sp:
        return None
    try:
        result = subprocess.run([sp, "SPFontsDataType"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def check_fonts():
    """Detect whether the fonts the export script writes into DOCX (`宋体`,
    `Times New Roman`, `Cambria Math`) are installed locally. Mismatches do not
    block export, but Word will silently substitute fonts and CNIPA submissions
    may be rejected on form review."""
    catalog = _list_fonts_via_fc_list() or _list_fonts_via_macos_system_profiler()
    if catalog is None:
        return {
            "available": False,
            "reason": "no fc-list (Linux/brew) or system_profiler (macOS) available",
            "songti": False,
            "times_new_roman": False,
            "cambria_math": False,
            "missing": list(REQUIRED_FONTS.keys()),
        }
    catalog_lower = catalog.lower()
    presence = {}
    for slot, names in REQUIRED_FONTS.items():
        presence[slot] = any(n.lower() in catalog_lower for n in names)
    missing = [slot for slot, found in presence.items() if not found]
    result = {"available": len(missing) == 0, "source": "fc-list" if shutil.which("fc-list") else "system_profiler"}
    result.update(presence)
    result["missing"] = missing
    return result


def check_word_com():
    if platform.system() != "Windows":
        return {"available": False, "reason": "not Windows"}
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Quit()
        return {"available": True}
    except Exception:
        return {"available": False, "reason": "Word COM not accessible"}


# ---------------------------------------------------------------------------
# Input-side material readability scan
# ---------------------------------------------------------------------------

# readability per extension. Keep aligned with
# cn-patent-repo-scout/references/material-readability.md.
EXT_READABILITY = {
    "full": {
        ".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml", ".csv", ".tsv",
        ".log", ".ini", ".cfg", ".xml", ".svg", ".html", ".htm", ".tex", ".bib",
        ".ipynb",
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".kt", ".c", ".h",
        ".cpp", ".hpp", ".cc", ".rs", ".sh", ".bash", ".zsh", ".rb", ".php",
        ".swift", ".m", ".mm", ".lua", ".pl", ".sql", ".vue", ".scala", ".cs",
    },
    "partial": {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
        ".docx", ".pptx", ".xlsx", ".pdf",
    },
    "unreadable": {
        ".doc", ".ppt", ".xls", ".odt", ".odp", ".ods", ".rtf",
        ".epub", ".mobi", ".azw3",
        ".dwg", ".dxf",
        ".mp4", ".mov", ".mkv", ".mp3", ".wav", ".m4a", ".flv",
        ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2",
    },
}

# Per-extension required tools. Driver decides install commands per OS.
EXT_TOOLS = {
    ".pdf": {
        "needs": ["pdftotext"],
        "missing_dim": "页图像与文本",
        "tier": "minimum",
    },
    ".docx": {
        "needs": ["python_docx"],
        "missing_dim": "嵌入图、复杂表格、公式",
        "tier": "minimum",
    },
    ".pptx": {
        "needs": ["python_pptx"],
        "missing_dim": "嵌入图、版式、备注",
        "tier": "office",
    },
    ".xlsx": {
        "needs": ["openpyxl"],
        "missing_dim": "公式、图表",
        "tier": "office",
    },
    ".png": {
        "needs": ["tesseract"],
        "missing_dim": "图像内文字（视觉内容已加载到模型上下文，扫描件文字仍需 OCR）",
        "tier": "ocr",
    },
    ".jpg": {"needs": ["tesseract"], "missing_dim": "图像内文字", "tier": "ocr"},
    ".jpeg": {"needs": ["tesseract"], "missing_dim": "图像内文字", "tier": "ocr"},
    ".doc": {"needs": ["libreoffice"], "missing_dim": "全部内容（旧二进制 .doc）", "tier": "office"},
    ".ppt": {"needs": ["libreoffice"], "missing_dim": "全部内容（旧二进制 .ppt）", "tier": "office"},
    ".xls": {"needs": ["libreoffice"], "missing_dim": "全部内容（旧二进制 .xls）", "tier": "office"},
    ".odt": {"needs": ["libreoffice"], "missing_dim": "全部内容", "tier": "office"},
    ".rtf": {"needs": ["libreoffice"], "missing_dim": "全部内容", "tier": "office"},
}

# Install commands keyed by (tool, package_manager).
INSTALL_COMMANDS = {
    "pdftotext": {
        "apt": "sudo apt-get install -y poppler-utils",
        "dnf": "sudo dnf install -y poppler-utils",
        "brew": "brew install poppler",
        "winget": "winget install --id oschwartz10612.Poppler",
        "choco": "choco install poppler",
        "scoop": "scoop install poppler",
    },
    "libreoffice": {
        "apt": "sudo apt-get install -y libreoffice --no-install-recommends",
        "dnf": "sudo dnf install -y libreoffice",
        "brew": "brew install --cask libreoffice",
        "winget": "winget install --id TheDocumentFoundation.LibreOffice",
        "choco": "choco install libreoffice-fresh",
        "scoop": "scoop bucket add extras && scoop install libreoffice",
    },
    "tesseract": {
        "apt": "sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim",
        "dnf": "sudo dnf install -y tesseract tesseract-langpack-chi_sim",
        "brew": "brew install tesseract tesseract-lang",
        "winget": "winget install --id UB-Mannheim.TesseractOCR",
        "choco": "choco install tesseract tesseract-languages",
        "scoop": "scoop install tesseract",
    },
    "pandoc": {
        "apt": "sudo apt-get install -y pandoc",
        "dnf": "sudo dnf install -y pandoc",
        "brew": "brew install pandoc",
        "winget": "winget install --id JohnMacFarlane.Pandoc",
        "choco": "choco install pandoc",
        "scoop": "scoop install pandoc",
    },
    "python_docx": {"pip": "pip install python-docx"},
    "python_pptx": {"pip": "pip install python-pptx"},
    "openpyxl": {"pip": "pip install openpyxl pandas"},
}


def detect_package_manager():
    """Pick the first usable package manager for the current OS."""
    sysname = platform.system()
    candidates = {
        "Linux": ["apt", "dnf", "pacman", "apk"],
        "Darwin": ["brew"],
        "Windows": ["winget", "choco", "scoop"],
    }.get(sysname, [])
    bin_map = {"apt": "apt-get"}
    for pm in candidates:
        if shutil.which(bin_map.get(pm, pm)):
            return pm
    return None


def _walk_source(root, exclude):
    root = Path(root)
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for name in filenames:
            yield Path(dirpath) / name


def scan_source_materials(source_root, exclude=None, max_examples=5):
    """Enumerate file extensions under source_root, classify readability,
    and return per-extension records. unreadable/partial extensions also carry
    install commands for the detected package manager."""
    exclude = set(exclude or [".git", "node_modules", "__pycache__", "dist", "build", "venv", ".venv"])
    if not source_root or not Path(source_root).exists():
        return {"scanned": False, "source_root": source_root, "extensions": []}

    pkg_mgr = detect_package_manager()
    counts = {}
    examples = {}
    for path in _walk_source(source_root, exclude):
        ext = path.suffix.lower() or "(noext)"
        counts[ext] = counts.get(ext, 0) + 1
        examples.setdefault(ext, []).append(str(path.relative_to(source_root)))

    records = []
    for ext, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if ext in EXT_READABILITY["full"]:
            readability = "full"
        elif ext in EXT_READABILITY["partial"]:
            readability = "partial"
        elif ext in EXT_READABILITY["unreadable"]:
            readability = "unreadable"
        else:
            readability = "unknown"
        rec = {
            "ext": ext,
            "count": count,
            "examples": examples[ext][:max_examples],
            "readability": readability,
        }
        cfg = EXT_TOOLS.get(ext)
        if cfg and readability != "full":
            rec["missing_dim"] = cfg["missing_dim"]
            rec["tier"] = cfg["tier"]
            install = []
            for tool in cfg["needs"]:
                cmd_map = INSTALL_COMMANDS.get(tool, {})
                cmd = cmd_map.get(pkg_mgr) if pkg_mgr else None
                if not cmd and "pip" in cmd_map:
                    cmd = cmd_map["pip"]
                if cmd:
                    install.append({"tool": tool, "command": cmd})
            if install:
                rec["install_recommendation"] = install
        records.append(rec)
    return {
        "scanned": True,
        "source_root": str(source_root),
        "package_manager": pkg_mgr,
        "extensions": records,
    }


def determine_backends(caps):
    if caps["word_com"]["available"]:
        docx_backend = "word_com"
    elif caps["pandoc"]["available"]:
        docx_backend = "pandoc"
    else:
        docx_backend = "blocked"

    if caps["word_com"]["available"]:
        formula_backend = "word_com_omml"
    elif caps["pandoc"]["available"]:
        formula_backend = "pandoc_builtin"
    elif caps["latex2mathml"]["available"]:
        formula_backend = "latex2mathml_fallback"
    else:
        formula_backend = "blocked"

    if caps["mmdc"]["available"] and caps["chromium"]["available"]:
        figure_backend = "mmdc_png"
    elif caps["mmdc"]["available"]:
        figure_backend = "mmdc_svg_fallback"
    else:
        figure_backend = "mmd_source_only"

    if caps["pdftotext"]["available"]:
        pdf_backend = "pdftotext"
    elif caps["pypdf"]["available"]:
        pdf_backend = "pypdf"
    elif caps.get("PyPDF2", {}).get("available"):
        pdf_backend = "PyPDF2"
    else:
        pdf_backend = "blocked"

    return docx_backend, formula_backend, figure_backend, pdf_backend


def main():
    chromium = find_chromium()
    caps = {
        "python3": {"available": True, "version": platform.python_version(), "path": sys.executable},
        "pandoc": check_pandoc(),
        "pdftotext": check_command("pdftotext", "-v"),
        "pypdf": check_python_package("pypdf"),
        "PyPDF2": check_python_package("PyPDF2"),
        "node": check_command("node"),
        "mmdc": check_command("mmdc"),
        "chromium": chromium,
        "libreoffice": find_libreoffice(),
        "word_com": check_word_com(),
        "latex2mathml": check_python_package("latex2mathml"),
        "lxml": check_python_package("lxml"),
        "python_docx": check_python_package("docx"),
        "imagemagick": check_command("convert"),
        "fonts": check_fonts(),
    }

    docx_backend, formula_backend, figure_backend, pdf_backend = determine_backends(caps)

    blocked = []
    warnings = []
    if docx_backend == "blocked":
        blocked.append("DOCX export (no pandoc or Word COM)")
    if caps["pandoc"]["available"] and caps["pandoc"].get("version_ok") is False:
        blocked.append(
            f"pandoc too old: {caps['pandoc'].get('version')} < {caps['pandoc'].get('min_required')} "
            f"(tex_math_dollars+raw_tex needs pandoc >= 2.0)"
        )
    if formula_backend == "blocked":
        blocked.append("Formula rendering (no pandoc, Word COM, or latex2mathml)")
    if pdf_backend == "blocked":
        blocked.append("PDF text extraction (no pdftotext, pypdf, or PyPDF2)")
    if not caps["libreoffice"]["available"] and platform.system() != "Windows":
        blocked.append(".doc file reading (no LibreOffice, only .docx supported)")
    if not caps["fonts"]["available"]:
        warnings.append(
            f"DOCX fonts missing locally: {caps['fonts'].get('missing')}. The exported "
            f"docx is field-level compliant (w:rFonts records the names) and renders "
            f"correctly on machines that have the fonts (e.g. CNIPA reviewer Windows). "
            f"Local preview / printed PDF on this machine will substitute fonts. "
            f"Install 宋体/SimSun, Times New Roman, Cambria Math if you need WYSIWYG preview."
        )

    result = {
        "platform": platform.system().lower(),
        "python_version": platform.python_version(),
        "capabilities": caps,
        "docx_backend": docx_backend,
        "formula_backend": formula_backend,
        "figure_backend": figure_backend,
        "pdf_backend": pdf_backend,
        "blocked_features": blocked,
        "warnings": warnings,
    }

    parser = argparse.ArgumentParser(description='Detect available tools and output capability matrix as JSON.')
    parser.add_argument('--output-path', default='', help='Optional output JSON path')
    parser.add_argument('--source-root', default='',
                        help='Optional source-material root to scan for input-side readability '
                             '(e.g. project root with pdf/docx/png materials).')
    parser.add_argument('--readability-report', default='',
                        help='Optional path to existing repo-scout readability-report.md; if present, its '
                             'user_choice is recorded so the user is not asked twice.')
    args = parser.parse_args()

    # Input-side scan: enumerate file extensions under source_root, classify
    # readability, and record install commands. Only runs if --source-root given.
    if args.source_root:
        source_scan = scan_source_materials(args.source_root)
        result["source_materials"] = source_scan
        partials = [r for r in source_scan.get("extensions", []) if r["readability"] == "partial"]
        unreadables = [r for r in source_scan.get("extensions", []) if r["readability"] == "unreadable"]
        if unreadables:
            warnings.append(
                f"输入侧不可完整读取的资料: "
                + ", ".join(f"{r['ext']}×{r['count']}" for r in unreadables)
                + "。在 source_materials.extensions[].install_recommendation 中查看安装命令。"
            )
        if partials:
            warnings.append(
                f"输入侧仅能部分读取的资料: "
                + ", ".join(f"{r['ext']}×{r['count']}" for r in partials)
                + "。建议安装对应解析器以拿到完整内容。"
            )
    else:
        result["source_materials"] = {"scanned": False,
                                      "hint": "rerun with --source-root <path> to scan input materials"}

    # Honor an existing repo-scout readability-report.md so the user is not
    # asked the same question twice.
    if args.readability_report:
        rp = Path(args.readability_report)
        if rp.is_file():
            result["readability_report"] = {
                "path": str(rp),
                "exists": True,
                "hint": "Reuse the user_choice from this file before re-prompting.",
            }
        else:
            result["readability_report"] = {"path": str(rp), "exists": False}

    output_path = None
    if args.output_path:
        output_path = Path(args.output_path)

    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding='utf-8')
        print(f"[patent-env-check] Written to: {output_path}")
    print(json_str)

    if warnings:
        print(f"\n⚠ WARNINGS ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    if blocked:
        print(f"\n⚠ BLOCKED FEATURES ({len(blocked)}):", file=sys.stderr)
        for b in blocked:
            print(f"  - {b}", file=sys.stderr)
        sys.exit(1 if docx_backend == "blocked" else 0)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
