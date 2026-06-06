# patents-workflow

`patents-workflow` 是中文专利工作流 skill 套件开发仓库。仓库用于协作开发、发布前检查和版本管理。

## 当前版本

`1.6.0`

## 工作方式

本仓库使用 Windows directory junction 管理 live skill：

```text
C:\Users\spade k\.codex\skills\<skill-name>
  -> C:\Users\spade k\patents-workflow\skills\<skill-name>
```

你可以继续在 `C:\Users\spade k\.codex\skills` 下直接修改和试用 skill；实际文件位于 `patents-workflow\skills`，Git 会直接看到变更。

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
- `cn-patent-project-drafting`

支撑型 vendored skill：

- `seaborn`
- `scientific-visualization`
- `scientific-schematics`
- `matplotlib`
- `markdown-mermaid-writing`
- `generate-image`

## 本地检查

```powershell
.\scripts\check-release.ps1
.\scripts\check-live-links.ps1
```

## 版本迭代

仓库名保持 `patents-workflow` 不变。版本通过 `VERSION`、`manifest.json`、`CHANGELOG.md`、git tag 和 GitHub Release 管理。
