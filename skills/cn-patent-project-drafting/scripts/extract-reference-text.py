#!/usr/bin/env python3
"""Extract text from reference documents (PDF, DOCX, DOC).

Usage:
    python3 scripts/extract-reference-text.py --path <file> --max-paragraphs 80 \
        [--output-path <path>] [--project-root .] \
        [--pdf-tool-path <path>] [--pdf-tool-config-path <path>]
"""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def read_text_multi_encoding(path: Path) -> str:
    """Read a text file trying UTF-8-sig, then GBK/CP936, then latin-1 fallback."""
    for enc in ("utf-8-sig", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # Should never reach here because latin-1 decodes everything
    return path.read_bytes().decode("latin-1", errors="replace")


def resolve_existing_tool_path(tool_path: str, source_label: str) -> Optional[Dict]:
    """Validate that tool_path exists on disk.

    Returns a tool dict on success, raises RuntimeError if the path is given
    but does not exist, returns None if tool_path is empty/None.
    """
    if not tool_path or not tool_path.strip():
        return None
    expanded = os.path.expandvars(os.path.expanduser(tool_path.strip()))
    resolved = Path(expanded)
    if not resolved.exists():
        raise RuntimeError(
            "PDF extraction tool path from {} does not exist: {}. "
            "Provide an existing tool path, choose an installation directory and authorize "
            "install, or provide extracted text.".format(source_label, tool_path)
        )
    return {
        "kind": "external",
        "name": "external-pdf-text-tool",
        "path": str(resolved.resolve()),
        "module": "",
        "source": source_label,
    }


# ---------------------------------------------------------------------------
# Project config lookup
# ---------------------------------------------------------------------------

def _get_object_property(obj: Optional[Dict], names: List[str]) -> str:
    """Return the first non-empty string value found among the given key names."""
    if obj is None:
        return ""
    for name in names:
        val = obj.get(name)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _get_nested_object_property(obj: Optional[Dict], container_name: str, names: List[str]) -> str:
    """Return a property from a nested container object."""
    if obj is None:
        return ""
    container = obj.get(container_name)
    if not isinstance(container, dict):
        return ""
    return _get_object_property(container, names)


def get_project_pdf_tool_path(root: str, config_path: str) -> str:
    """Search project config files for a PDF tool path.

    Checks patent-pdf-tools.json and patent-iteration-state.json under
    <root>/.agents/. Supports multiple key formats and nested containers.
    """
    candidates: List[str] = []
    if config_path and config_path.strip():
        candidates.append(config_path.strip())
    else:
        root_path = Path(root).resolve()
        if root_path.exists():
            candidates.append(str(root_path / ".agents" / "config" / "patent-pdf-tools.json"))
            candidates.append(
                str(root_path / ".agents" / "outputs" / "state" / "patent-iteration-state.json")
            )

    for candidate in candidates:
        p = Path(candidate)
        if not p.exists():
            continue
        try:
            text = read_text_multi_encoding(p)
            obj = json.loads(text)
        except Exception:
            continue

        # Direct top-level keys
        direct = _get_object_property(
            obj,
            ["pdf_text_tool_path", "pdftotext_path", "pdfToolPath", "tool_path"],
        )
        if direct:
            return direct

        # Nested container keys
        for container_name in ("pdf_extraction", "pdfExtraction", "pdf_tools", "pdfTools"):
            nested = _get_nested_object_property(
                obj,
                container_name,
                ["tool_path", "toolPath", "pdf_text_tool_path", "pdftotext_path"],
            )
            if nested:
                return nested

    return ""


# ---------------------------------------------------------------------------
# Python PDF module detection
# ---------------------------------------------------------------------------

def test_python_pdf_module(module_name: str) -> bool:
    """Return True if the given module (pypdf or PyPDF2) can be imported."""
    return importlib.util.find_spec(module_name) is not None


# ---------------------------------------------------------------------------
# PDF tool resolution chain
# ---------------------------------------------------------------------------

def resolve_pdf_text_tool(
    explicit_path: str,
    root: str,
    config_path: str,
) -> Optional[Dict]:
    """Resolve the best available PDF text extraction tool.

    Resolution order:
    1. Explicit --pdf-tool-path argument
    2. Environment variables: CN_PATENT_PDF_TEXT_TOOL, PDF_TEXT_TOOL_PATH, PDFTOTEXT_PATH
    3. pdftotext on PATH
    4. Python pypdf / PyPDF2 modules
    5. Project config file
    """
    # 1. Explicit path
    tool = resolve_existing_tool_path(explicit_path, "--pdf-tool-path")
    if tool is not None:
        return tool

    # 2. Environment variables
    for env_name in ("CN_PATENT_PDF_TEXT_TOOL", "PDF_TEXT_TOOL_PATH", "PDFTOTEXT_PATH"):
        env_val = os.environ.get(env_name, "")
        tool = resolve_existing_tool_path(env_val, "environment variable {}".format(env_name))
        if tool is not None:
            return tool

    # 3. pdftotext on PATH
    pdftotext_path = shutil.which("pdftotext")
    if pdftotext_path:
        return {
            "kind": "pdftotext",
            "name": "pdftotext",
            "path": pdftotext_path,
            "module": "",
            "source": "PATH",
        }

    # 4. Python PDF modules (pypdf preferred over PyPDF2)
    for module_name in ("pypdf", "PyPDF2"):
        if test_python_pdf_module(module_name):
            return {
                "kind": "python",
                "name": "python-{}".format(module_name),
                "path": sys.executable,
                "module": module_name,
                "source": "PATH",
            }

    # 5. Project config
    project_tool_path = get_project_pdf_tool_path(root, config_path)
    tool = resolve_existing_tool_path(project_tool_path, "current project PDF tool config")
    if tool is not None:
        return tool

    return None


# ---------------------------------------------------------------------------
# PDF extraction backends
# ---------------------------------------------------------------------------

def invoke_pdf_text_executable(tool_path: str, file_path: str, use_layout: bool) -> List[str]:
    """Call an external PDF text tool, writing output to a temp file."""
    tmp_path = Path(tempfile.gettempdir()) / "patent-pdf-{}.txt".format(uuid.uuid4().hex)
    try:
        if use_layout:
            result = subprocess.run([tool_path, "-layout", file_path, str(tmp_path)])
        else:
            result = subprocess.run([tool_path, file_path, str(tmp_path)])
        if result.returncode != 0:
            raise RuntimeError(f"PDF extraction tool failed with exit code {result.returncode}.")

        if not tmp_path.exists():
            return []
        text = read_text_multi_encoding(tmp_path)
        return [line for line in text.splitlines() if line.strip()]
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def invoke_python_pdf_text(module_name: str, file_path: str) -> List[str]:
    """Extract text from a PDF using pypdf or PyPDF2."""
    lines: List[str] = []
    try:
        if module_name == "pypdf":
            from pypdf import PdfReader  # type: ignore
        else:
            from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                lines.extend(line for line in text.splitlines() if line.strip())
    except Exception as exc:
        raise RuntimeError("Python PDF extraction failed: {}".format(exc)) from exc
    return lines


def invoke_pdf_text_extraction(file_path: str, tool: Optional[Dict]) -> List[str]:
    """Dispatch PDF extraction to the appropriate backend."""
    if tool is None:
        raise RuntimeError(
            "PDF extraction toolchain is required before patent evidence extraction "
            "because PDF input was detected: {}. "
            "No usable PDF text extractor was found. "
            "Choose one: provide --pdf-tool-path or CN_PATENT_PDF_TEXT_TOOL/PDFTOTEXT_PATH, "
            "choose an installation directory and authorize installing a PDF text extractor, "
            "or provide an already extracted text version.".format(file_path)
        )

    if tool["kind"] == "python":
        return invoke_python_pdf_text(tool["module"], file_path)

    use_layout = tool["kind"] == "pdftotext"
    return invoke_pdf_text_executable(tool["path"], file_path, use_layout)


# ---------------------------------------------------------------------------
# DOCX / DOC extraction
# ---------------------------------------------------------------------------

def get_word_paragraphs(file_path: str, limit: int) -> List[str]:
    """Extract paragraphs using Windows Word COM automation (Windows only)."""
    if platform.system() != "Windows":
        raise RuntimeError(
            ".doc extraction via Word COM is only available on Windows."
        )
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "win32com is not available. Install pywin32 to use Word COM extraction."
        ) from exc

    word = None
    doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(file_path, False, True)
        items: List[str] = []
        for paragraph in doc.Paragraphs:
            text = paragraph.Range.Text.replace("\r", "").replace("\x07", "").strip()
            if not text:
                continue
            items.append(text)
            if limit > 0 and len(items) >= limit:
                break
        return items
    finally:
        if doc is not None:
            try:
                doc.Close(0)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def invoke_docx_extractor(file_path: str, limit: int) -> Optional[List[str]]:
    """Try calling cn-patent-docx-export's extract-docx-text script.

    Returns None if the script is not found (caller should fall back).
    """
    script_dir = Path(__file__).parent
    candidates = [
        script_dir / ".." / ".." / "cn-patent-docx-export" / "scripts" / "extract-docx-text.py",
    ]
    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.exists():
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(resolved),
                 "--path", file_path,
                 "--max-paragraphs", str(limit)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
            )
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            return lines
        except Exception:
            return None
    return None


def extract_docx(file_path: str, limit: int) -> List[str]:
    """Extract paragraphs from a .docx file using python-docx."""
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "python-docx is not installed. Run: pip install python-docx"
        ) from exc
    doc = Document(file_path)
    lines: List[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        lines.append(text)
        if limit > 0 and len(lines) >= limit:
            break
    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract text from reference documents (PDF, DOCX, DOC)."
    )
    parser.add_argument("--path", required=True, help="Path to the input file.")
    parser.add_argument(
        "--max-paragraphs", type=int, default=80,
        help="Maximum number of paragraphs/lines to extract (0 = unlimited).",
    )
    parser.add_argument(
        "--output-path", default="",
        help="Write output to this file instead of stdout.",
    )
    parser.add_argument(
        "--project-root", default=".",
        help="Project root for config lookup.",
    )
    parser.add_argument(
        "--pdf-tool-path", default="",
        help="Explicit path to a PDF text extraction tool.",
    )
    parser.add_argument(
        "--pdf-tool-config-path", default="",
        help="Explicit path to PDF tool config JSON.",
    )
    args = parser.parse_args()

    resolved = Path(args.path).resolve()
    if not resolved.exists():
        print("ERROR: File not found: {}".format(resolved), file=sys.stderr)
        sys.exit(1)

    ext = resolved.suffix.lower()
    lines: List[str] = []
    backend = ""

    try:
        if ext == ".docx":
            # Priority: docx-export script → python-docx → Windows Word COM
            try:
                result = invoke_docx_extractor(str(resolved), args.max_paragraphs)
                if result is not None and len(result) > 0:
                    lines = result
                    backend = "cn-patent-docx-export/docx extractor"
            except Exception:
                lines = []

            if not lines:
                try:
                    lines = extract_docx(str(resolved), args.max_paragraphs)
                    if lines:
                        backend = "python-docx"
                except Exception:
                    lines = []

            if not lines and platform.system() == "Windows":
                lines = get_word_paragraphs(str(resolved), args.max_paragraphs)
                if lines:
                    backend = "Word COM"

        elif ext == ".doc":
            # Windows only: Word COM
            lines = get_word_paragraphs(str(resolved), args.max_paragraphs)
            if lines:
                backend = "Word COM"

        elif ext == ".pdf":
            tool = resolve_pdf_text_tool(
                args.pdf_tool_path,
                args.project_root,
                args.pdf_tool_config_path,
            )
            lines = invoke_pdf_text_extraction(str(resolved), tool)
            if lines and tool is not None:
                backend = "{} ({})".format(tool["name"], tool["source"])

        else:
            print("ERROR: Unsupported reference format: {}".format(ext), file=sys.stderr)
            sys.exit(1)

    except RuntimeError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        sys.exit(1)

    # Apply paragraph limit
    if args.max_paragraphs > 0 and len(lines) > args.max_paragraphs:
        lines = lines[: args.max_paragraphs]

    content = "\n".join(lines)

    if not content.strip():
        msg = "No extractable text found in reference file: {}".format(resolved)
        if ext == ".pdf":
            msg += (
                ". The PDF may be scanned or image-only, or it may have no text layer. "
                "Stop the patent workflow and provide an OCR toolchain, a text-layer PDF, "
                "an already extracted text version, or explicit user confirmation to exclude this PDF."
            )
        elif ext in (".doc", ".docx"):
            msg += ". Word COM extraction may be unavailable in the current environment."
        print("ERROR: {}".format(msg), file=sys.stderr)
        sys.exit(1)

    if args.output_path:
        out = Path(args.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        if backend:
            print("[extract-reference-text] Backend: {}".format(backend))
        print("[extract-reference-text] Output written to: {}".format(out))
    else:
        if backend:
            print("[extract-reference-text] Backend: {}".format(backend), file=sys.stderr)
        print(content)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
