# patents-workflow

`patents-workflow` 是中文专利工作流 skill 套件开发仓库。仓库用于协作开发、发布前检查和版本管理。

## 当前版本

`2.0.0`

## 工作方式

本仓库使用本机 live link 管理 agent 可扫描的 skill。当前支持 Codex 和 Claude Code：

```text
~/.codex/skills/<skill-name>
  -> <repo>/skills/<skill-name>

~/.claude/skills/<skill-name>
  -> <repo>/skills/<skill-name>
```

你可以继续在对应 agent 的 live skill 目录下直接修改和试用 skill；实际文件位于当前 clone 的 `skills/` 目录，Git 会直接看到变更。

Codex 使用者首次 clone 后，在仓库根目录运行：

```bash
python scripts/link-live-skills.py --agent codex --apply
python scripts/check-live-links.py --agent codex
```

Claude Code 使用者首次 clone 后运行：

```bash
python scripts/link-live-skills.py --agent claude --apply
python scripts/check-live-links.py --agent claude
```

脚本默认使用当前用户目录，不会写死某台机器的用户路径：

- Codex: `~/.codex/skills`
- Claude Code: `~/.claude/skills`

如需指定其他 live skill 根目录：

```bash
python scripts/link-live-skills.py --live-root "<path-to-skills>" --apply
python scripts/check-live-links.py --live-root "<path-to-skills>"
```

## Skill 范围

核心专利工作流 skill：

- `cn-patent-repo-scout`
- `cn-patent-mainline-analysis`
- `cn-patent-prior-art-search`
- `cn-patent-disclosure-draft`
- `cn-patent-disclosure-review`
- `cn-patent-formal-drafting`
- `cn-patent-attorney-review`
- `cn-patent-docx-export`
- `cn-patent-domain-runtime`

支撑型 vendored skill：

- `seaborn`
- `scientific-visualization`
- `scientific-schematics`
- `matplotlib`
- `markdown-mermaid-writing`
- `generate-image`

## 本地检查

```bash
python scripts/check-release.py
python scripts/check-live-links.py
```

## 版本迭代

仓库名保持 `patents-workflow` 不变。版本通过 `VERSION`、`manifest.json`、`CHANGELOG.md`、git tag 和 GitHub Release 管理。
