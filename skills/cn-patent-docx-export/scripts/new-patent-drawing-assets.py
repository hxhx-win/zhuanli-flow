#!/usr/bin/env python3
"""Validate and record patent figure assets from a drafting-stage manifest.

This script does not generate or render images. Figure assets must be produced
before DOCX export by the agent invoking the backend named in each manifest entry.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

COMMON_REQUIRED = [
    'figureNumber', 'caption', 'figureType', 'preferredBackend', 'primarySkill',
    'imagePath', 'evidenceSource', 'generationStatus'
]

VALID_STATUSES = {
    'planned', 'generated', 'missing', 'skipped-with-authorization', 'existing-asset'
}

BACKEND_REQUIREMENTS = {
    'mermaid-mmdc': [['mermaidPath', 'mermaidSource', 'sourcePath'], 'renderCommand'],
    'scientific-visualization': ['dataPath', 'plotSpec', 'scriptPath', 'stylePreset', 'outputFormats'],
    'matplotlib': ['dataPath', 'scriptPath', 'plotType', 'axisLabels', 'stylePreset'],
    'seaborn': ['dataPath', 'scriptPath', 'plotType', 'semanticMapping', 'stylePreset'],
    'scientific-schematics': [['prompt', 'promptPath'], 'technicalConstraints', 'reviewLogPath'],
    'imagegen': ['userAuthorization', ['prompt', 'promptPath'], 'nonEvidenceNotice'],
    'generate-image': ['userAuthorization', ['prompt', 'promptPath'], 'nonEvidenceNotice'],
    'existing-asset': ['sourceAssetPath', 'licenseOrSourceNote', 'copyTo'],
}


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        print(f'ERROR: Invalid JSON: {path}: {exc}', file=sys.stderr)
        sys.exit(1)


def has_any(entry: dict, names: list) -> bool:
    return any(entry.get(name) for name in names)


def check_requirement(entry: dict, req) -> bool:
    if isinstance(req, list):
        return has_any(entry, req)
    return bool(entry.get(req))


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATENT_THEME = SKILL_ROOT / 'references' / 'mermaid-patent-theme.json'

PATH_PLACEHOLDERS = {
    '{cn-patent-docx-export}': str(SKILL_ROOT),
    '{patent-theme}': str(DEFAULT_PATENT_THEME),
}


def expand_placeholders(value: str) -> str:
    if not isinstance(value, str):
        return value
    for token, replacement in PATH_PLACEHOLDERS.items():
        if token in value:
            value = value.replace(token, replacement)
    return value


def resolve_path(value: str, base_dir: Path) -> str:
    if not value:
        return value
    value = expand_placeholders(value)
    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return str(path)


def normalize_paths(entry: dict, base_dir: Path) -> None:
    for key in (
        'imagePath', 'mermaidPath', 'sourcePath', 'dataPath', 'scriptPath',
        'promptPath', 'reviewLogPath', 'sourceAssetPath', 'copyTo',
        'themeConfigPath',
    ):
        if entry.get(key):
            entry[key] = resolve_path(entry[key], base_dir)


def validate_entry(entry: dict, index: int, base_dir: Path) -> list:
    errors = []
    label = f'entries[{index}]'

    for key in COMMON_REQUIRED:
        if not entry.get(key):
            errors.append(f'{label}: missing required field {key}')

    status = entry.get('generationStatus')
    if status and status not in VALID_STATUSES:
        errors.append(f'{label}: invalid generationStatus {status}')

    backend = entry.get('preferredBackend')
    requirements = BACKEND_REQUIREMENTS.get(backend)
    if backend and not requirements:
        errors.append(f'{label}: unknown preferredBackend {backend}')
    elif requirements:
        for req in requirements:
            if not check_requirement(entry, req):
                if isinstance(req, list):
                    errors.append(f'{label}: one of {req} is required for {backend}')
                else:
                    errors.append(f'{label}: {req} is required for {backend}')

    normalize_paths(entry, base_dir)

    image_path = Path(entry['imagePath']) if entry.get('imagePath') else None
    if status == 'skipped-with-authorization':
        if not entry.get('userAuthorization'):
            errors.append(f'{label}: skipped-with-authorization requires userAuthorization')
    elif image_path and not image_path.exists():
        errors.append(f'{label}: imagePath does not exist: {image_path}')

    if backend == 'existing-asset':
        source_asset = Path(entry['sourceAssetPath']) if entry.get('sourceAssetPath') else None
        if source_asset and not source_asset.exists():
            errors.append(f'{label}: sourceAssetPath does not exist: {source_asset}')

    return errors


def validate_manifest(manifest_path: Path, output_dir: str) -> Path:
    manifest = read_json(manifest_path)
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        print('ERROR: manifest must contain entries list', file=sys.stderr)
        sys.exit(1)

    base_dir = manifest_path.parent
    output_path = Path(output_dir).resolve() / 'figure-manifest.json' if output_dir else manifest_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    errors = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f'entries[{index}]: must be an object')
            continue
        errors.extend(validate_entry(entry, index, base_dir))

    manifest['validatedFromManifest'] = str(manifest_path)
    manifest['validatedAt'] = datetime.now().isoformat(timespec='seconds')
    manifest['validator'] = 'new-patent-drawing-assets.py'
    manifest['renderer'] = manifest.get('renderer', 'external-backends')

    if errors:
        print('ERROR: Figure manifest validation failed:', file=sys.stderr)
        for error in errors:
            print(f'  - {error}', file=sys.stderr)
        sys.exit(1)

    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    plan_path = output_path.parent / 'figure-generation-plan.md'
    lines = [
        '# 附图资产校验记录',
        '',
        f'- Manifest：{output_path}',
        '- 说明：本脚本只校验与登记已生成图片资产，不生成、不渲染、不补图。',
        '',
        '## 附图条目',
    ]
    for entry in entries:
        lines.append(f'- {entry.get("caption", "未命名附图")}')
        lines.append(f'  - 后端：{entry.get("preferredBackend", "")}；主 skill：{entry.get("primarySkill", "")}')
        lines.append(f'  - 状态：{entry.get("generationStatus", "")}')
        lines.append(f'  - 图片路径：{entry.get("imagePath", "")}')
    plan_path.write_text('\n'.join(lines), encoding='utf-8')

    print(f'Figure manifest validated: {output_path}')
    print(f'Figure plan: {plan_path}')
    print(f'Figure count: {len(entries)}')
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Validate patent figure assets from manifest')
    parser.add_argument('--manifest-input', required=True, help='Drafting-stage figure-manifest.json path')
    parser.add_argument('--output-dir', default='', help='Optional directory for normalized manifest copy')
    args = parser.parse_args()

    manifest_path = Path(args.manifest_input).resolve()
    if not manifest_path.exists():
        print(f'ERROR: Manifest file not found: {manifest_path}', file=sys.stderr)
        sys.exit(1)

    validate_manifest(manifest_path, args.output_dir)


if __name__ == '__main__':
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
