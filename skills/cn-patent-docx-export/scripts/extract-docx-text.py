#!/usr/bin/env python3
"""Extract text from DOCX and optionally verify structure for patent export QA.

Usage:
    python3 extract-docx-text.py --extract patent.docx
    python3 extract-docx-text.py --verify patent.docx
    python3 extract-docx-text.py --extract patent.docx --max-paragraphs 50
"""
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WP_NS = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
CNIPA_PAGE_MARGINS = {
    'top': '1418',
    'left': '1418',
    'right': '850',
    'bottom': '850',
}
CNIPA_ABSTRACT_MAX_CHARS = 300
CNIPA_HEADER_CHAR_SPACING = '280'
CNIPA_FIRST_LINE_CHARS = '200'
CNIPA_FIRST_LINE_TWIPS = '560'
CLAIM_FORBIDDEN_EXPRESSIONS = (
    '如说明书所述',
    '如上所述',
    '参见说明书',
    '见说明书',
    '说明书中所述',
)

EXPECTED_HEADERS = {
    '说明书摘要',
    '摘要附图',
    '权利要求书',
    '说明书',
    '说明书附图',
}
OPTIONAL_HEADERS = {'说明书附图'}

MARKDOWN_PATTERNS = [
    (r'```', 'code fence'),
    (r'^#{1,6}\s', 'heading marker'),
    (r'`latex', 'latex fence'),
    (r'\*\*[^*]+\*\*', 'bold marker'),
]

INTERNAL_SUBHEADING_RE = re.compile(
    r'^(?:发明名称|技术领域|背景技术|发明内容|附图说明|具体实施方式|实施例[0-9一二三四五六七八九十]+|可选实施方式|替代实施方式)$'
)


def extract_text_from_xml(xml_bytes):
    """Extract text from document.xml, returning list of paragraph strings."""
    root = ET.fromstring(xml_bytes)
    paragraphs = []
    for p in root.iter(f'{{{W_NS}}}p'):
        texts = []
        for t in p.iter(f'{{{W_NS}}}t'):
            if t.text:
                texts.append(t.text)
        for mt in p.iter(f'{{{M_NS}}}t'):
            if mt.text:
                texts.append(mt.text)
        line = ''.join(texts).strip()
        if line:
            paragraphs.append(line)
    return paragraphs


def count_elements(xml_bytes, tag):
    """Count occurrences of a namespaced tag in XML."""
    root = ET.fromstring(xml_bytes)
    return len(list(root.iter(tag)))


def check_nary_bodies(xml_bytes):
    """Check m:nary elements have non-empty m:e (body) children."""
    root = ET.fromstring(xml_bytes)
    issues = []
    for i, nary in enumerate(root.iter(f'{{{M_NS}}}nary'), 1):
        e_elem = nary.find(f'{{{M_NS}}}e')
        if e_elem is None:
            issues.append(f'nary #{i}: missing m:e element')
        else:
            has_content = any(t.text for t in e_elem.iter(f'{{{M_NS}}}t') if t.text)
            if not has_content:
                has_sub = len(list(e_elem)) > 0
                if not has_sub:
                    issues.append(f'nary #{i}: m:e body is empty')
    return issues


def extract_headers(zf):
    """Extract text from all header*.xml files."""
    headers = {}
    for name in zf.namelist():
        if re.match(r'word/header\d*\.xml', name):
            xml_bytes = zf.read(name)
            root = ET.fromstring(xml_bytes)
            texts = []
            for t in root.iter(f'{{{W_NS}}}t'):
                if t.text:
                    texts.append(t.text)
            header_text = ''.join(texts).strip()
            if header_text:
                headers[name] = header_text
    return headers


def check_header_style(zf):
    """Verify headers follow official form style: centered bold 14pt Heiti text."""
    issues = []
    for name in zf.namelist():
        if not re.match(r'word/header\d*\.xml', name):
            continue
        root = ET.fromstring(zf.read(name))
        header_text = ''.join(t.text or '' for t in root.iter(f'{{{W_NS}}}t')).strip()
        if not header_text:
            continue
        p = next(root.iter(f'{{{W_NS}}}p'), None)
        if p is None:
            issues.append(f'{name}: missing paragraph')
            continue
        pPr = p.find(f'{{{W_NS}}}pPr')
        if pPr is None:
            issues.append(f'{name}: missing pPr')
            continue
        jc = pPr.find(f'{{{W_NS}}}jc')
        if jc is None or jc.get(f'{{{W_NS}}}val') != 'center':
            issues.append(f'{name}: header not centered')
        if pPr.find(f'{{{W_NS}}}pBdr') is not None:
            issues.append(f'{name}: header should not have bottom border')
        rPr = pPr.find(f'{{{W_NS}}}rPr')
        if rPr is None:
            issues.append(f'{name}: missing header paragraph rPr')
            continue
        fonts = rPr.find(f'{{{W_NS}}}rFonts')
        if fonts is None or fonts.get(f'{{{W_NS}}}eastAsia') != '黑体':
            issues.append(f'{name}: eastAsia font is not 黑体')
        if fonts is None or fonts.get(f'{{{W_NS}}}ascii') != '黑体':
            issues.append(f'{name}: ascii font is not 黑体')
        if rPr.find(f'{{{W_NS}}}b') is None:
            issues.append(f'{name}: header is not bold')
        sz = rPr.find(f'{{{W_NS}}}sz')
        if sz is None or sz.get(f'{{{W_NS}}}val') != '28':
            issues.append(f'{name}: header size is not 14pt')
        spacing = rPr.find(f'{{{W_NS}}}spacing')
        if spacing is None or spacing.get(f'{{{W_NS}}}val') != CNIPA_HEADER_CHAR_SPACING:
            issues.append(f'{name}: header character spacing is not official value {CNIPA_HEADER_CHAR_SPACING}')
    return {'pass': len(issues) == 0, 'issues': issues}


def extract_footers(zf):
    """Extract text and field markers from footer*.xml files."""
    footers = {}
    for name in zf.namelist():
        if re.match(r'word/footer\d*\.xml', name):
            xml_bytes = zf.read(name)
            root = ET.fromstring(xml_bytes)
            texts = [t.text for t in root.iter(f'{{{W_NS}}}t') if t.text]
            instr = [t.text for t in root.iter(f'{{{W_NS}}}instrText') if t.text]
            fld_chars = [e.get(f'{{{W_NS}}}fldCharType') for e in root.iter(f'{{{W_NS}}}fldChar')]
            footers[name] = {
                'text': ''.join(texts).strip(),
                'instr': ''.join(instr).strip(),
                'field_chars': [c for c in fld_chars if c],
            }
    return footers


def _resolve_rel_targets(zf):
    rels_path = 'word/_rels/document.xml.rels'
    if rels_path not in zf.namelist():
        return {}
    rels_xml = zf.read(rels_path)
    rels_root = ET.fromstring(rels_xml)
    return {rel.get('Id', ''): rel.get('Target', '') for rel in rels_root}


def _target_path(target):
    if not target:
        return ''
    return f'word/{target}' if not target.startswith('word/') else target


def _part_text(zf, path):
    if not path or path not in zf.namelist():
        return ''
    root = ET.fromstring(zf.read(path))
    return ''.join(t.text for t in root.iter(f'{{{W_NS}}}t') if t.text).strip()


def collect_doc_sections(zf):
    """Collect section metadata and text previews in document order."""
    doc_xml = zf.read('word/document.xml')
    root = ET.fromstring(doc_xml)
    rel_targets = _resolve_rel_targets(zf)
    body = root.find(f'{{{W_NS}}}body')
    if body is None:
        return []

    sections = []
    current = []

    def flush(sectPr):
        header_ref = sectPr.find(f'{{{W_NS}}}headerReference') if sectPr is not None else None
        footer_ref = sectPr.find(f'{{{W_NS}}}footerReference') if sectPr is not None else None
        pg_num = sectPr.find(f'{{{W_NS}}}pgNumType') if sectPr is not None else None
        header_rid = header_ref.get(f'{{{R_NS}}}id') if header_ref is not None else ''
        footer_rid = footer_ref.get(f'{{{R_NS}}}id') if footer_ref is not None else ''
        header_text = _part_text(zf, _target_path(rel_targets.get(header_rid, '')))
        sections.append({
            'header': header_text,
            'footer_rid': footer_rid,
            'page_start': pg_num.get(f'{{{W_NS}}}start') if pg_num is not None else '',
            'paragraphs': list(current),
        })
        current.clear()

    for elem in body:
        if elem.tag == f'{{{W_NS}}}p':
            texts = [t.text for t in elem.iter(f'{{{W_NS}}}t') if t.text]
            text = ''.join(texts).strip()
            if text:
                current.append(text)
            pPr = elem.find(f'{{{W_NS}}}pPr')
            sectPr = pPr.find(f'{{{W_NS}}}sectPr') if pPr is not None else None
            if sectPr is not None:
                flush(sectPr)
        elif elem.tag == f'{{{W_NS}}}sectPr':
            flush(elem)
    return sections


def check_image_rels(zf):
    """Check word/_rels/document.xml.rels for image relationships."""
    rels_path = 'word/_rels/document.xml.rels'
    if rels_path not in zf.namelist():
        return []
    xml_bytes = zf.read(rels_path)
    root = ET.fromstring(xml_bytes)
    images = []
    for rel in root:
        rel_type = rel.get('Type', '')
        if 'image' in rel_type.lower():
            images.append(rel.get('Target', ''))
    return images


def check_media_files(zf):
    """List files in word/media/."""
    return [n for n in zf.namelist() if n.startswith('word/media/')]


def check_markdown_residuals(paragraphs):
    """Detect markdown syntax residuals in extracted text."""
    issues = []
    for i, para in enumerate(paragraphs, 1):
        for pattern, desc in MARKDOWN_PATTERNS:
            if re.search(pattern, para, re.MULTILINE):
                issues.append(f'para {i}: {desc} found: {para[:60]}')
                break
    return issues


def check_claim_numbering(paragraphs):
    """Verify claims are numbered sequentially (1. 2. 3. ...)."""
    claim_nums = []
    for para in paragraphs:
        m = re.match(r'^(\d+)\.\s', para)
        if m and ('特征在于' in para or '所述' in para or '根据权利要求' in para):
            claim_nums.append(int(m.group(1)))
    if not claim_nums:
        return {'found': False, 'sequential': False, 'count': 0}
    expected = list(range(claim_nums[0], claim_nums[0] + len(claim_nums)))
    return {
        'found': True,
        'sequential': claim_nums == expected and claim_nums[0] == 1,
        'count': len(claim_nums),
        'actual': claim_nums if claim_nums != expected or claim_nums[0] != 1 else None,
    }


def check_page_layout(zf):
    """Verify A4 page size and margins from body sectPr."""
    doc_xml = zf.read('word/document.xml')
    root = ET.fromstring(doc_xml)
    body = root.find(f'{{{W_NS}}}body')
    if body is None:
        return {'pass': False, 'error': 'no w:body element'}
    sectPr = body.find(f'{{{W_NS}}}sectPr')
    if sectPr is None:
        return {'pass': False, 'error': 'no body sectPr'}

    pgSz = sectPr.find(f'{{{W_NS}}}pgSz')
    pgMar = sectPr.find(f'{{{W_NS}}}pgMar')

    result = {'pass': True, 'issues': []}
    if pgSz is not None:
        w = pgSz.get(f'{{{W_NS}}}w', '')
        h = pgSz.get(f'{{{W_NS}}}h', '')
        result['pgSz'] = {'w': w, 'h': h}
        if w != '11906' or h != '16838':
            result['issues'].append(f'page size not A4: w={w}, h={h}')
    else:
        result['issues'].append('missing pgSz')

    if pgMar is not None:
        margins = {}
        for attr in ('top', 'right', 'bottom', 'left', 'header', 'footer'):
            margins[attr] = pgMar.get(f'{{{W_NS}}}{attr}', '')
        result['pgMar'] = margins
        if margins.get('top') != '1418':
            result['issues'].append(f'top margin {margins.get("top")} != 1418')
        if margins.get('left') != '1418':
            result['issues'].append(f'left margin {margins.get("left")} != 1418')
        if margins.get('right') != CNIPA_PAGE_MARGINS['right']:
            result['issues'].append(f'right margin {margins.get("right")} != {CNIPA_PAGE_MARGINS["right"]}')
        if margins.get('bottom') != CNIPA_PAGE_MARGINS['bottom']:
            result['issues'].append(f'bottom margin {margins.get("bottom")} != {CNIPA_PAGE_MARGINS["bottom"]}')
    else:
        result['issues'].append('missing pgMar')

    if result['issues']:
        result['pass'] = False
    return result


def check_paragraph_formatting(xml_bytes, sample_size=30):
    """Check body paragraph formatting strictly."""
    root = ET.fromstring(xml_bytes)
    body = root.find(f'{{{W_NS}}}body')
    if body is None:
        return {'pass': False, 'error': 'no body'}

    formatted = 0
    checked = 0
    issues = []

    def indent_values(pPr):
        if pPr is None:
            return None, None
        ind = pPr.find(f'{{{W_NS}}}ind')
        if ind is None:
            return None, None
        return ind.get(f'{{{W_NS}}}firstLineChars'), ind.get(f'{{{W_NS}}}firstLine')

    def add_issue(text, pPr, issue):
        detail = {'text': text[:50], 'issue': issue}
        if pPr is not None:
            spacing = pPr.find(f'{{{W_NS}}}spacing')
            ind = pPr.find(f'{{{W_NS}}}ind')
            jc = pPr.find(f'{{{W_NS}}}jc')
            detail['line'] = spacing.get(f'{{{W_NS}}}line') if spacing is not None else None
            detail['firstLineChars'] = ind.get(f'{{{W_NS}}}firstLineChars') if ind is not None else None
            detail['firstLine'] = ind.get(f'{{{W_NS}}}firstLine') if ind is not None else None
            detail['jc'] = jc.get(f'{{{W_NS}}}val') if jc is not None else None
        issues.append(detail)

    for p in body:
        if p.tag != f'{{{W_NS}}}p':
            continue
        texts = [t.text for t in p.iter(f'{{{W_NS}}}t') if t.text]
        text = ''.join(texts).strip()
        if not text:
            continue
        # Math-bearing paragraphs are body text and must follow the same
        # firstLineChars=200 / jc=both / line=360 rules. Do not skip them.

        pPr = p.find(f'{{{W_NS}}}pPr')
        if pPr is not None:
            jc = pPr.find(f'{{{W_NS}}}jc')
            if jc is not None and jc.get(f'{{{W_NS}}}val') == 'center':
                first_line_chars, first_line = indent_values(pPr)
                if first_line_chars not in (None, '0') or first_line not in (None, '0'):
                    add_issue(text, pPr, 'centered title/caption must not have first-line indent')
                continue

        if INTERNAL_SUBHEADING_RE.match(text):
            # Internal headings are intentionally bold paragraphs without first-line indent.
            first_line_chars, first_line = indent_values(pPr)
            if first_line_chars not in (None, '0') or first_line not in (None, '0'):
                add_issue(text, pPr, 'heading must not have first-line indent')
            continue
        # Claims (paragraphs that begin with the inline N. prefix) follow the
        # same body formatting rules as any other paragraph: line=360,
        # firstLineChars=200, jc=both. Do not skip them.

        checked += 1
        ok = True
        if pPr is None:
            ok = False
        else:
            spacing = pPr.find(f'{{{W_NS}}}spacing')
            if spacing is None or spacing.get(f'{{{W_NS}}}line') != '360':
                ok = False
            elif spacing.get(f'{{{W_NS}}}before', '0') != '0' or spacing.get(f'{{{W_NS}}}after', '0') != '0':
                ok = False
            ind = pPr.find(f'{{{W_NS}}}ind')
            if ind is None or ind.get(f'{{{W_NS}}}firstLineChars') != '200':
                ok = False
            jc = pPr.find(f'{{{W_NS}}}jc')
            if jc is None or jc.get(f'{{{W_NS}}}val') != 'both':
                ok = False

        if ok:
            formatted += 1
        else:
            add_issue(text, pPr, 'body paragraph formatting mismatch')

    ratio = formatted / checked if checked > 0 else 0
    return {
        'pass': len(issues) == 0,
        'formatted': formatted,
        'checked': checked,
        'ratio': round(ratio, 3),
        'sample_issues': issues,
    }


def check_section_order(zf):
    """Verify section headers appear in correct order."""
    doc_xml = zf.read('word/document.xml')
    root = ET.fromstring(doc_xml)
    R_NS_LOCAL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

    body = root.find(f'{{{W_NS}}}body')
    if body is None:
        return {'pass': False, 'error': 'no body'}

    header_rids = []
    for elem in body.iter(f'{{{W_NS}}}headerReference'):
        htype = elem.get(f'{{{W_NS}}}type', '')
        rid = elem.get(f'{{{R_NS_LOCAL}}}id', '')
        if htype == 'default' and rid:
            header_rids.append(rid)

    rels_path = 'word/_rels/document.xml.rels'
    if rels_path not in zf.namelist():
        return {'pass': False, 'error': 'no rels file'}

    rels_xml = zf.read(rels_path)
    rels_root = ET.fromstring(rels_xml)
    rid_to_target = {}
    for rel in rels_root:
        rid_to_target[rel.get('Id', '')] = rel.get('Target', '')

    ordered_headers = []
    for rid in header_rids:
        target = rid_to_target.get(rid, '')
        if not target:
            continue
        hdr_path = f'word/{target}' if not target.startswith('word/') else target
        if hdr_path in zf.namelist():
            hdr_xml = zf.read(hdr_path)
            hdr_root = ET.fromstring(hdr_xml)
            texts = [t.text for t in hdr_root.iter(f'{{{W_NS}}}t') if t.text]
            header_text = ''.join(texts).strip()
            if header_text:
                ordered_headers.append(header_text)

    expected_order = [
        '说明书摘要',
        '摘要附图',
        '权利要求书',
        '说明书',
        '说明书附图',
    ]

    found_in_order = []
    seen = set()
    for h in ordered_headers:
        if h in expected_order and h not in seen:
            found_in_order.append(h)
            seen.add(h)

    expected_filtered = [h for h in expected_order if h in found_in_order]

    is_correct = found_in_order == expected_filtered
    return {
        'pass': is_correct,
        'found_order': ordered_headers,
        'expected': expected_order,
    }


def check_residual_styles(xml_bytes):
    """Detect residual pandoc styles in body paragraphs."""
    root = ET.fromstring(xml_bytes)
    body = root.find(f'{{{W_NS}}}body')
    if body is None:
        return {'pass': True, 'count': 0}

    pandoc_styles = {'Heading1', 'Heading2', 'Heading3', 'Heading4', 'Heading5',
                     'Compact', 'BodyText', 'FirstParagraph', 'SourceCode'}
    found = {}

    for p in body:
        if p.tag != f'{{{W_NS}}}p':
            continue
        has_math = p.find(f'.//{{{M_NS}}}oMath') is not None
        if has_math:
            continue
        pPr = p.find(f'{{{W_NS}}}pPr')
        if pPr is None:
            continue
        pStyle = pPr.find(f'{{{W_NS}}}pStyle')
        if pStyle is None:
            continue
        style_val = pStyle.get(f'{{{W_NS}}}val', '')
        if style_val in pandoc_styles or style_val.startswith('Heading'):
            found[style_val] = found.get(style_val, 0) + 1

    return {
        'pass': len(found) == 0,
        'count': sum(found.values()),
        'styles': found if found else None,
    }


HEADER_CONTENT_MARKERS = {
    '说明书摘要': ['本发明', '公开', '技术领域', '方法', '系统', '装置'],
    '摘要附图': ['图1', '图 1', '摘要附图'],
    '权利要求书': ['其特征在于', '权利要求', '所述'],
    '说明书': ['技术领域', '背景技术', '发明内容', '发明名称'],
}


def check_header_content_alignment(zf):
    """Verify each section's header matches its content by checking marker keywords."""
    doc_xml = zf.read('word/document.xml')
    root = ET.fromstring(doc_xml)
    R_NS_LOCAL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

    body = root.find(f'{{{W_NS}}}body')
    if body is None:
        return {'pass': False, 'error': 'no body'}

    # Collect sections: each section ends at a sectPr in a paragraph's pPr
    current_texts = []
    sections = []  # list of (header_rid, joined_text)
    section_rids = []

    for elem in body:
        if elem.tag == f'{{{W_NS}}}p':
            texts = [t.text for t in elem.iter(f'{{{W_NS}}}t') if t.text]
            text = ''.join(texts).strip()
            if text:
                current_texts.append(text)
            pPr = elem.find(f'{{{W_NS}}}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{{{W_NS}}}sectPr')
                if sectPr is not None:
                    hdrRef = sectPr.find(f'{{{W_NS}}}headerReference')
                    rid = hdrRef.get(f'{{{R_NS_LOCAL}}}id') if hdrRef is not None else ''
                    section_rids.append(rid)
                    sections.append(' '.join(current_texts[:5]))
                    current_texts = []
        elif elem.tag == f'{{{W_NS}}}sectPr':
            hdrRef = elem.find(f'{{{W_NS}}}headerReference')
            rid = hdrRef.get(f'{{{R_NS_LOCAL}}}id') if hdrRef is not None else ''
            section_rids.append(rid)
            sections.append(' '.join(current_texts[:5]))

    # Resolve rIds to header text
    rels_path = 'word/_rels/document.xml.rels'
    if rels_path not in zf.namelist():
        return {'pass': False, 'error': 'no rels file'}
    rels_xml = zf.read(rels_path)
    rels_root = ET.fromstring(rels_xml)
    rid_to_target = {}
    for rel in rels_root:
        rid_to_target[rel.get('Id', '')] = rel.get('Target', '')

    mismatches = []
    for i, (rid, content_preview) in enumerate(zip(section_rids, sections)):
        target = rid_to_target.get(rid, '')
        if not target:
            continue
        hdr_path = f'word/{target}' if not target.startswith('word/') else target
        if hdr_path not in zf.namelist():
            continue
        hdr_xml = zf.read(hdr_path)
        hdr_root = ET.fromstring(hdr_xml)
        hdr_texts = [t.text for t in hdr_root.iter(f'{{{W_NS}}}t') if t.text]
        header_text = ''.join(hdr_texts).strip()

        markers = HEADER_CONTENT_MARKERS.get(header_text, [])
        if not markers:
            continue
        if not any(m in content_preview for m in markers):
            mismatches.append({
                'section': i + 1,
                'header': header_text,
                'content_preview': content_preview[:80],
                'expected_markers': markers,
            })

    return {
        'pass': len(mismatches) == 0,
        'mismatches': mismatches if mismatches else None,
    }


def check_footer_page_numbers(zf):
    sections = collect_doc_sections(zf)
    footers = extract_footers(zf)
    rel_targets = _resolve_rel_targets(zf)
    issues = []
    for index, section in enumerate(sections, 1):
        rid = section.get('footer_rid', '')
        target = rel_targets.get(rid, '')
        footer = footers.get(_target_path(target))
        if not footer:
            issues.append(f'section {index}: missing footer')
            continue
        has_page_field = 'PAGE' in footer.get('instr', '') or footer.get('text', '').isdigit()
        if not has_page_field:
            issues.append(f'section {index}: footer has no PAGE field')
    return {'pass': len(issues) == 0, 'issues': issues}


def check_section_page_restart(zf):
    sections = collect_doc_sections(zf)
    issues = []
    for index, section in enumerate(sections, 1):
        if section.get('page_start') != '1':
            issues.append(f'section {index} ({section.get("header", "")}): page start is {section.get("page_start")}')
    return {'pass': len(issues) == 0, 'issues': issues, 'sections': len(sections)}


def check_abstract_rules(zf):
    sections = collect_doc_sections(zf)
    for section in sections:
        if section.get('header') == '说明书摘要':
            text = ''.join(section.get('paragraphs', [])).strip()
            normalized = re.sub(r'\s+', '', text)
            issues = []
            if len(normalized) > CNIPA_ABSTRACT_MAX_CHARS:
                issues.append(f'abstract length {len(normalized)} > {CNIPA_ABSTRACT_MAX_CHARS}')
            if any(p in {'摘要', '说明书摘要'} for p in section.get('paragraphs', [])):
                issues.append('abstract contains title text')
            return {'pass': len(issues) == 0, 'length': len(normalized), 'issues': issues}
    return {'pass': False, 'error': 'abstract section not found'}


def check_claim_sentence_rules(zf):
    sections = collect_doc_sections(zf)
    issues = []
    claims = []
    for section in sections:
        if section.get('header') == '权利要求书':
            current = None
            for para in section.get('paragraphs', []):
                match = re.match(r'^([0-9]+)[\.、]\s*(.*)', para)
                if match:
                    if current is not None:
                        claims.append(current)
                    current = match.group(2).strip()
                else:
                    # Continuation paragraph (formula or "其中..." explanation)
                    # for the current claim. Concatenate so the trailing 。 lands
                    # on the explanation paragraph rather than the claim head.
                    if current is not None and para.strip():
                        current = current + ' ' + para.strip()
            if current is not None:
                claims.append(current)
            break
    for idx, claim in enumerate(claims, 1):
        if not claim.endswith('。'):
            issues.append(f'claim {idx}: missing final Chinese period')
        if '。' in claim[:-1]:
            issues.append(f'claim {idx}: period before claim end')
        for expression in CLAIM_FORBIDDEN_EXPRESSIONS:
            if expression in claim:
                issues.append(f'claim {idx}: forbidden expression {expression}')
    return {'pass': len(issues) == 0, 'count': len(claims), 'issues': issues}


def check_spec_required_parts(zf):
    sections = collect_doc_sections(zf)
    required = {'技术领域', '背景技术', '发明内容', '具体实施方式'}
    found = set()
    for section in sections:
        if section.get('header') == '说明书':
            for para in section.get('paragraphs', []):
                if para in required:
                    found.add(para)
    missing = sorted(required - found)
    return {'pass': len(missing) == 0, 'found': sorted(found), 'missing': missing}


def check_figure_caption_rules(zf):
    sections = collect_doc_sections(zf)
    figure_nums = []
    for section in sections:
        if section.get('header') == '说明书附图':
            for para in section.get('paragraphs', []):
                match = re.match(r'^图\s*([0-9]+)', para)
                if match:
                    figure_nums.append(int(match.group(1)))
    if not figure_nums:
        return {'pass': True, 'found': False, 'count': 0}
    expected = list(range(1, len(figure_nums) + 1))
    return {
        'pass': figure_nums == expected,
        'found': True,
        'count': len(figure_nums),
        'actual': figure_nums,
        'expected': expected,
    }


def check_split_exports(split_output_dir):
    if not split_output_dir:
        return {'pass': True, 'skipped': True}
    split_dir = Path(split_output_dir)
    expected = ['说明书摘要.docx', '权利要求书.docx', '说明书.docx']
    issues = []
    for name in expected:
        path = split_dir / name
        if not path.exists():
            issues.append(f'missing split file: {name}')
            continue
        try:
            report = verify_docx(path)
        except Exception as exc:
            issues.append(f'cannot verify {name}: {exc}')
            continue
        if not report.get('checks', {}).get('section_page_restart', {}).get('pass', False):
            issues.append(f'{name}: page does not restart at 1')
    return {'pass': len(issues) == 0, 'skipped': False, 'issues': issues}


def verify_docx(docx_path, split_output_dir=''):
    """Run full verification and return structured report."""
    report = {'file': str(docx_path), 'checks': {}, 'verdict': 'PASS'}

    try:
        zf = zipfile.ZipFile(str(docx_path), 'r')
    except Exception as e:
        return {'file': str(docx_path), 'checks': {}, 'verdict': 'FAIL',
                'error': f'Cannot open DOCX: {e}'}

    doc_xml = zf.read('word/document.xml')
    paragraphs = extract_text_from_xml(doc_xml)

    md_issues = check_markdown_residuals(paragraphs)
    report['checks']['markdown_residuals'] = {
        'pass': len(md_issues) == 0,
        'issues': md_issues[:10],
    }

    headers = extract_headers(zf)
    found_headers = set(headers.values())
    missing = (EXPECTED_HEADERS - OPTIONAL_HEADERS) - found_headers
    report['checks']['section_headers'] = {
        'pass': len(missing) == 0,
        'found': list(found_headers),
        'missing': list(missing),
    }
    report['checks']['header_style'] = check_header_style(zf)

    formula_count = count_elements(doc_xml, f'{{{M_NS}}}oMath')
    formula_para_count = count_elements(doc_xml, f'{{{M_NS}}}oMathPara')
    report['checks']['formulas'] = {
        'pass': formula_count > 0,
        'oMath_count': formula_count,
        'oMathPara_count': formula_para_count,
    }

    nary_issues = check_nary_bodies(doc_xml)
    has_rad = count_elements(doc_xml, f'{{{M_NS}}}rad') > 0
    has_f = count_elements(doc_xml, f'{{{M_NS}}}f') > 0
    has_sub = count_elements(doc_xml, f'{{{M_NS}}}sSub') > 0
    report['checks']['formula_quality'] = {
        'pass': len(nary_issues) == 0,
        'nary_issues': nary_issues,
        'has_radical': has_rad,
        'has_fraction': has_f,
        'has_subscript': has_sub,
    }

    drawing_count = count_elements(doc_xml, f'{{{WP_NS}}}inline') + \
                    count_elements(doc_xml, f'{{{WP_NS}}}anchor')
    image_rels = check_image_rels(zf)
    media_files = check_media_files(zf)
    report['checks']['figures'] = {
        'pass': True,
        'drawing_nodes': drawing_count,
        'image_relationships': len(image_rels),
        'media_files': len(media_files),
    }

    claims = check_claim_numbering(paragraphs)
    report['checks']['claim_numbering'] = {
        'pass': claims.get('sequential', False) or not claims.get('found', False),
        'details': claims,
    }

    page_layout = check_page_layout(zf)
    report['checks']['page_layout'] = page_layout

    para_fmt = check_paragraph_formatting(doc_xml)
    report['checks']['paragraph_formatting'] = para_fmt

    section_order = check_section_order(zf)
    report['checks']['section_order'] = section_order

    residual = check_residual_styles(doc_xml)
    report['checks']['residual_styles'] = residual

    alignment = check_header_content_alignment(zf)
    report['checks']['header_content_alignment'] = alignment

    report['checks']['footer_page_numbers'] = check_footer_page_numbers(zf)
    report['checks']['section_page_restart'] = check_section_page_restart(zf)
    report['checks']['abstract_rules'] = check_abstract_rules(zf)
    report['checks']['claim_sentence_rules'] = check_claim_sentence_rules(zf)
    report['checks']['spec_required_parts'] = check_spec_required_parts(zf)
    report['checks']['figure_caption_rules'] = check_figure_caption_rules(zf)

    for check in report['checks'].values():
        if not check.get('pass', True):
            report['verdict'] = 'WARN' if report['verdict'] == 'PASS' else report['verdict']
    if not report['checks']['section_headers']['pass']:
        report['verdict'] = 'FAIL'
    if not report['checks'].get('header_style', {}).get('pass', True):
        report['verdict'] = 'FAIL'
    if report['checks'].get('markdown_residuals', {}).get('issues'):
        report['verdict'] = 'FAIL'
    if not report['checks'].get('page_layout', {}).get('pass', True):
        report['verdict'] = 'FAIL'
    if not report['checks'].get('paragraph_formatting', {}).get('pass', True):
        report['verdict'] = 'FAIL'
    if not report['checks'].get('header_content_alignment', {}).get('pass', True):
        report['verdict'] = 'FAIL'
    for key in ('footer_page_numbers', 'section_page_restart', 'abstract_rules',
                'claim_sentence_rules', 'spec_required_parts'):
        if not report['checks'].get(key, {}).get('pass', True):
            report['verdict'] = 'FAIL'

    zf.close()
    if split_output_dir:
        report['checks']['split_export'] = check_split_exports(split_output_dir)
        if not report['checks']['split_export']['pass']:
            report['verdict'] = 'FAIL'
    return report


def main():
    parser = argparse.ArgumentParser(description='Extract/verify patent DOCX')
    parser.add_argument('docx', help='Path to DOCX file')
    parser.add_argument('--extract', action='store_true', help='Extract text only')
    parser.add_argument('--verify', action='store_true', help='Run verification')
    parser.add_argument('--split-output-dir', default='', help='Optional split DOCX directory to verify')
    parser.add_argument('--max-paragraphs', type=int, default=0, help='Limit output')
    args = parser.parse_args()

    if not args.extract and not args.verify:
        args.extract = True

    docx_path = Path(args.docx)
    if not docx_path.exists():
        print(f"ERROR: File not found: {docx_path}", file=sys.stderr)
        sys.exit(1)

    if args.extract:
        zf = zipfile.ZipFile(str(docx_path), 'r')
        doc_xml = zf.read('word/document.xml')
        paragraphs = extract_text_from_xml(doc_xml)
        zf.close()
        limit = args.max_paragraphs if args.max_paragraphs > 0 else len(paragraphs)
        for p in paragraphs[:limit]:
            print(p)

    if args.verify:
        report = verify_docx(docx_path, args.split_output_dir)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report['verdict'] == 'FAIL':
            sys.exit(1)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    main()
