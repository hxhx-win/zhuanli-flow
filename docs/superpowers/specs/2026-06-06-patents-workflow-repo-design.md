# 专利工作流仓库设计

日期：2026-06-06

## 目标

创建一个本地开发仓库，用于维护专利工作流 skill 套件。该仓库负责协作开发、发布前检查、版本发布，以及后续上传 GitHub。Codex 仍从 `C:\Users\spade k\.codex\skills` 发现 skill，因此该仓库不作为实时 skill 根目录，而是通过同步脚本把仓库中的 skill 同步到 Codex 的实际 skill 目录。

## 仓库身份

使用固定仓库名：

```text
C:\Users\spade k\patents-workflow
```

套件初始版本为 `1.6.0`。后续从 `1.6.0` 迭代到 `1.7.0`、`2.0.0` 等版本时，仍在同一个仓库内演进。常规版本迭代不新建 `patents-workflow-v1.7` 这类版本化仓库。

版本状态保存在：

- `VERSION`
- `manifest.json`
- `CHANGELOG.md`
- git tag，例如 `v1.6.0`、`v1.7.0`
- 后续 GitHub Release

## Skill 范围

初始套件包含 15 个从 `C:\Users\spade k\.codex\skills` 复制而来的 skill。

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

随仓库托管的支撑型 skill：

- `seaborn`
- `scientific-visualization`
- `scientific-schematics`
- `matplotlib`
- `markdown-mermaid-writing`
- `generate-image`

支撑型 skill 按 vendored dependencies 处理。它们会随套件复制、检查和同步，但默认不作为功能改造目标。除非后续任务明确要求，否则不主动修改这些通用支撑 skill 的行为。

## 目录结构

```text
patents-workflow/
  README.md
  LICENSE
  CONTRIBUTING.md
  CHANGELOG.md
  VERSION
  manifest.json
  .gitignore
  docs/
    development.md
    superpowers/
      specs/
        2026-06-06-patents-workflow-repo-design.md
  scripts/
    sync-to-codex-skills.ps1
    check-release.ps1
  skills/
    cn-patent-repo-scout/
    cn-patent-mainline-analysis/
    cn-patent-prior-art-search/
    cn-patent-disclosure-draft/
    cn-patent-disclosure-review/
    cn-patent-formal-drafting/
    cn-patent-attorney-review/
    cn-patent-docx-export/
    cn-patent-project-drafting/
    seaborn/
    scientific-visualization/
    scientific-schematics/
    matplotlib/
    markdown-mermaid-writing/
    generate-image/
```

每个 skill 都是 `skills/` 的直接子目录，并且每个 skill 目录内必须直接包含自己的 `SKILL.md`。同步后，每个 skill 会被复制到 `C:\Users\spade k\.codex\skills\<skill-name>`，从而保持 Codex 现有的 skill 发现机制不变。

## 同步策略

`scripts/sync-to-codex-skills.ps1` 负责从开发仓库同步到 Codex 实际使用的 skill 目录。

默认行为是 dry-run，只报告将要复制、删除或覆盖的内容。只有显式传入执行参数时，脚本才会写入 `C:\Users\spade k\.codex\skills`。

预期行为：

- 从 `manifest.json` 读取 skill 列表
- 只复制 manifest 中声明的 skill 目录
- 排除缓存和生成物，例如 `__pycache__/`、`*.pyc`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`
- 如果源 skill 目录缺少 `SKILL.md`，拒绝执行
- 不触碰 `C:\Users\spade k\.codex\skills` 中不属于本套件的其他 skill

## 发布前检查策略

`scripts/check-release.ps1` 负责在协作开发或发布前校验仓库状态。

必须检查：

- manifest 中声明的每个 skill 都存在于 `skills/`
- 每个 skill 都包含 `SKILL.md`
- 每个 `SKILL.md` 的 frontmatter 都包含 `name` 和 `description`
- 仓库中不存在 `__pycache__/` 或 `*.pyc`
- 仓库中不存在明显的 secret 模式
- README 中声明的 skill 列表与 `manifest.json` 一致
- `VERSION` 与 `manifest.json.version` 一致

第一版实现可以保持检查逻辑简单、确定、可重复。仓库稳定后再逐步加入更严格的校验。

## 发布路径

第 1 阶段只做本地仓库整理。

第 2 阶段可以推送到名为 `patents-workflow` 的 GitHub private repository，并邀请协作者参与。

第 3 阶段再准备公开开源，届时需要补齐或确认：

- license 选择
- 专利和法律免责声明
- 贡献规则
- issue 与 pull request 模板
- release checklist
- CI 检查
- 如有必要，补充 security policy

## 非目标

本次整理不重新设计专利工作流本身。不把所有 skill 合并成一个父级 skill。不让 `patents-workflow` 仓库直接成为 Codex 的实时 skill 根目录。不默认改动支撑型 skill 的行为。

## 验收标准

第一版实现完成时，应满足：

- 本地 git 仓库已存在
- 15 个声明的 skill 已复制到 `skills/`，且不包含缓存产物
- 仓库治理文件已存在
- 同步脚本和发布前检查脚本已存在
- 发布前检查通过
- Codex 实际 skill 发现布局保持兼容
