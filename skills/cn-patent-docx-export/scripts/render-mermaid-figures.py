#!/usr/bin/env python3
"""Render every mermaid-mmdc entry in a patent figure-manifest.json with the
patent theme and the puppeteer --no-sandbox workaround.

Usage:
    python3 scripts/render-mermaid-figures.py \
        --manifest patent/<patent-slug>/drafts/figures/<draft-name>/figure-manifest.json
    # optional: --width 1600 --background white --rerender

The script:
  * resolves the manifest's `themeConfigPath` (see PATH_PLACEHOLDERS) so the
    manifest can stay portable and reference the bundled theme symbolically,
  * auto-creates a puppeteer config with `--no-sandbox` so mmdc works as root
    (Linux/Docker default for Anthropic Skill runs),
  * picks up every entry whose preferredBackend == "mermaid-mmdc" and renders
    its .mmd source into the manifest's imagePath,
  * updates generationStatus -> "generated" on success, leaves it untouched
    (and prints a warning) on failure.

Idempotent: if PNG already exists and `--rerender` is not passed and the .mmd
mtime is older than the .png, the entry is skipped.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THEME = SKILL_ROOT / 'references' / 'mermaid-patent-theme.json'

# Symbolic placeholders that the runtime expands into absolute paths so a
# manifest committed to git stays machine-independent.
PATH_PLACEHOLDERS = {
    '{cn-patent-docx-export}': str(SKILL_ROOT),
    '{patent-theme}': str(DEFAULT_THEME),
}


def expand_placeholders(value: str) -> str:
    if not isinstance(value, str):
        return value
    for token, replacement in PATH_PLACEHOLDERS.items():
        if token in value:
            value = value.replace(token, replacement)
    return value


def resolve_path(value, base_dir: Path) -> Path:
    value = expand_placeholders(value)
    p = Path(value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def _find_puppeteer_chrome():
    """Locate the chrome binary auto-downloaded by mmdc's Puppeteer install.
    Cache layout: ~/.cache/puppeteer/chrome/<platform>-<ver>/{chrome|*.app/Contents/MacOS/<bin>}.
    On macOS the same cache root may also live under ~/Library/Caches/."""
    cache_roots = [
        Path.home() / '.cache' / 'puppeteer' / 'chrome',
        Path.home() / 'Library' / 'Caches' / 'puppeteer' / 'chrome',
    ]
    for cache_root in cache_roots:
        if not cache_root.is_dir():
            continue
        for version_dir in sorted(
            (d for d in cache_root.iterdir() if d.is_dir()),
            key=lambda p: p.name, reverse=True,
        ):
            for sub in version_dir.iterdir():
                if not sub.is_dir():
                    continue
                linux_chrome = sub / 'chrome'
                if linux_chrome.is_file():
                    return linux_chrome
                win_chrome = sub / 'chrome.exe'
                if win_chrome.is_file():
                    return win_chrome
                for app in sub.glob('*.app'):
                    macos_dir = app / 'Contents' / 'MacOS'
                    if not macos_dir.is_dir():
                        continue
                    for binary in macos_dir.iterdir():
                        if binary.is_file():
                            return binary
    return None


def ensure_puppeteer_config() -> Path:
    """Return path to a puppeteer config with --no-sandbox and an explicit
    executablePath into the Puppeteer cache. This makes mmdc rendering
    deterministic across Linux and macOS regardless of system PATH state.

    Honor user-supplied PUPPETEER_CONFIG_PATH if it points at an existing file;
    otherwise materialize one in TMPDIR. Idempotent.
    """
    explicit = os.environ.get('PUPPETEER_CONFIG_PATH')
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    config = {'args': ['--no-sandbox']}
    chrome = _find_puppeteer_chrome()
    if chrome is not None:
        config['executablePath'] = str(chrome)
    cfg = Path(tempfile.gettempdir()) / 'puppeteer-config-cn-patent.json'
    cfg.write_text(json.dumps(config), encoding='utf-8')
    return cfg


def find_mmdc() -> str:
    mmdc = shutil.which('mmdc')
    if not mmdc:
        print('ERROR: mmdc not found on PATH. Install @mermaid-js/mermaid-cli '
              'or set PATH to include it.', file=sys.stderr)
        sys.exit(2)
    return mmdc


def needs_render(mmd: Path, png: Path, force: bool) -> bool:
    if force:
        return True
    if not png.exists():
        return True
    return mmd.stat().st_mtime > png.stat().st_mtime


def render_entry(entry: dict, base_dir: Path, theme_path: Path,
                 puppeteer_cfg: Path, width: int, background: str,
                 force: bool) -> tuple:
    figno = entry.get('figureNumber', '?')
    if entry.get('preferredBackend') != 'mermaid-mmdc':
        return ('skip', figno, 'not mermaid-mmdc')
    mmd = entry.get('mermaidPath') or entry.get('sourcePath')
    if not mmd:
        return ('skip', figno, 'no mermaidPath/sourcePath')
    mmd = resolve_path(mmd, base_dir)
    if not mmd.is_file():
        return ('error', figno, f'mermaid source missing: {mmd}')
    img = entry.get('imagePath')
    if not img:
        return ('error', figno, 'no imagePath')
    png = resolve_path(img, base_dir)
    png.parent.mkdir(parents=True, exist_ok=True)

    if not needs_render(mmd, png, force):
        return ('cached', figno, str(png))

    cmd = [find_mmdc(), '-p', str(puppeteer_cfg), '-i', str(mmd),
           '-o', str(png), '-c', str(theme_path), '-b', background,
           '-w', str(width)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        return ('error', figno, 'mmdc timeout (120s)')
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        return ('error', figno, 'mmdc failed: ' + ' | '.join(tail))
    return ('ok', figno, str(png))


def main() -> int:
    parser = argparse.ArgumentParser(description='Render mermaid-mmdc entries '
                                     'from a patent figure-manifest.json.')
    parser.add_argument('--manifest', required=True, help='Path to figure-manifest.json')
    parser.add_argument('--theme', default=None,
                        help='Override patent theme JSON path (default: bundled mermaid-patent-theme.json)')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--background', default='white')
    parser.add_argument('--rerender', action='store_true',
                        help='Re-render even if PNG already up-to-date')
    parser.add_argument('--update-manifest', action='store_true', default=True,
                        help='Update generationStatus + themeConfigPath in manifest (default)')
    parser.add_argument('--no-update-manifest', dest='update_manifest', action='store_false')
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.is_file():
        print(f'ERROR: manifest not found: {manifest_path}', file=sys.stderr)
        return 1
    base_dir = manifest_path.parent
    theme_path = Path(expand_placeholders(args.theme)) if args.theme else DEFAULT_THEME
    if not theme_path.is_file():
        print(f'ERROR: theme not found: {theme_path}', file=sys.stderr)
        return 1
    puppeteer_cfg = ensure_puppeteer_config()

    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entries = manifest.get('entries', [])

    summary = {'ok': 0, 'cached': 0, 'skip': 0, 'error': 0}
    errors = []
    for entry in entries:
        status, figno, info = render_entry(entry, base_dir, theme_path,
                                           puppeteer_cfg, args.width,
                                           args.background, args.rerender)
        summary[status] = summary.get(status, 0) + 1
        if status == 'error':
            errors.append(f'{figno}: {info}')
            print(f'[render] FAIL {figno}: {info}', file=sys.stderr)
        else:
            print(f'[render] {status.upper():7s} {figno}: {info}')
        if args.update_manifest and status in ('ok', 'cached'):
            entry['generationStatus'] = 'generated'
            # Persist symbolic theme reference so the manifest stays portable.
            entry['themeConfigPath'] = '{patent-theme}'
            mmd_name = Path(entry.get('mermaidPath') or entry.get('sourcePath') or '').name
            png_name = Path(entry.get('imagePath') or '').name
            if mmd_name and png_name:
                entry['renderCommand'] = (
                    f'mmdc -i {mmd_name} -o {png_name} '
                    f'-c {{patent-theme}} -b {args.background} -w {args.width}'
                )

    if args.update_manifest:
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

    print(f'[render] summary: ok={summary["ok"]} cached={summary["cached"]} '
          f'skip={summary["skip"]} error={summary["error"]}')
    return 0 if summary['error'] == 0 else 1


if __name__ == '__main__':
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
