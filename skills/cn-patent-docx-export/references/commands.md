# 推荐命令

> Windows 原生环境：命令中的 `python3` 请用 `python` 或 `py` 代替。

## 环境检查

```bash
python3 ../cn-patent-domain-runtime/scripts/patent-env-check.py
```

## 附图 manifest 校验

```bash
python3 scripts/new-patent-drawing-assets.py --manifest-input patent/<patent-slug>/drafts/figures/<draft-name>/figure-manifest.json
```

## DOCX 导出

```bash
python3 scripts/export-patent-draft-docx.py --input <draft>.md --output <output>.docx
```

## 带附图导出

```bash
python3 scripts/export-patent-draft-docx.py --input <draft>.md --output <output>.docx --figure-manifest patent/<patent-slug>/drafts/figures/<draft-name>/figure-manifest.json
```

## 带分片稿导出

```bash
python3 scripts/export-patent-draft-docx.py --input <draft>.md --output <output>.docx --split-output-dir patent/<patent-slug>/deliverables/split
```

## 带附图和分片稿导出

```bash
python3 scripts/export-patent-draft-docx.py --input <draft>.md --output <output>.docx --figure-manifest patent/<patent-slug>/drafts/figures/<draft-name>/figure-manifest.json --split-output-dir patent/<patent-slug>/deliverables/split
```

## 导出后验证

```bash
# 纯文本提取
python3 scripts/extract-docx-text.py --extract <output>.docx

# 结构化验证（输出 JSON 报告）
python3 scripts/extract-docx-text.py --verify <output>.docx

# 同时验证分片稿
python3 scripts/extract-docx-text.py --verify <output>.docx --split-output-dir patent/<patent-slug>/deliverables/split
```

verdict 为 PASS 时导出完成；WARN 列出待人工确认项；FAIL 必须修复后重新导出。
