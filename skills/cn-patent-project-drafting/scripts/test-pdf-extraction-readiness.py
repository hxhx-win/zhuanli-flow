#!/usr/bin/env python3
"""Test PDF text extraction readiness for patent reference files."""
import argparse, subprocess, sys, tempfile, shutil, uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Test PDF text extraction readiness')
    parser.add_argument('--path', nargs='+', required=True, help='PDF files or directories')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--pdf-tool-path', default='', help='Explicit PDF tool path')
    parser.add_argument('--pdf-tool-config-path', default='', help='PDF tool config path')
    parser.add_argument('--max-files', type=int, default=100, help='Max PDF files to check')
    args = parser.parse_args()

    # Collect PDF files from paths (resolve, recurse dirs, filter .pdf, dedupe, limit)
    pdf_files = []
    for p in args.path:
        path = Path(p).resolve()
        if path.is_dir():
            pdf_files.extend(path.rglob('*.pdf'))
        elif path.suffix.lower() == '.pdf':
            pdf_files.append(path)
    pdf_files = list(dict.fromkeys(pdf_files))[:args.max_files]

    if not pdf_files:
        print("[test-pdf-extraction-readiness] No PDF files detected.")
        return

    # Find extract-reference-text.py
    extract_script = Path(__file__).parent / 'extract-reference-text.py'
    if not extract_script.exists():
        print(f"ERROR: extract-reference-text.py not found at {extract_script}", file=sys.stderr)
        sys.exit(1)

    # Create temp dir for outputs
    temp_root = Path(tempfile.mkdtemp(prefix='patent-pdf-readiness-'))
    try:
        for pdf in pdf_files:
            out_file = temp_root / (uuid.uuid4().hex + '.txt')
            cmd = [sys.executable, str(extract_script),
                   '--path', str(pdf),
                   '--max-paragraphs', '3',
                   '--output-path', str(out_file),
                   '--project-root', args.project_root]
            if args.pdf_tool_path:
                cmd.extend(['--pdf-tool-path', args.pdf_tool_path])
            if args.pdf_tool_config_path:
                cmd.extend(['--pdf-tool-config-path', args.pdf_tool_config_path])

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
                print(f"ERROR: PDF extraction preflight failed for '{pdf}'. {error_msg}", file=sys.stderr)
                sys.exit(1)
    finally:
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)

    print(f"[test-pdf-extraction-readiness] PDF text extraction ready for {len(pdf_files)} file(s).")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
