# patents-workflow junction 设置实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `patents-workflow` 开发仓库，并把 `.codex\skills` 下 15 个 live skill 替换为指向仓库 skill 目录的 Windows directory junction。

**Architecture:** `patents-workflow\skills\<skill-name>` 是真实文件位置；`C:\Users\spade k\.codex\skills\<skill-name>` 是 junction。用户可以继续在 `.codex\skills` 下修改和试用，Git 会在 `patents-workflow` 仓库中直接看到变更。

**Tech Stack:** PowerShell、Git、Windows directory junction、Markdown、JSON。

---

## Task 1: 创建仓库治理文件

**Files:**
- Create: `VERSION`
- Create: `manifest.json`
- Create: `.gitignore`
- Create: `README.md`
- Create: `CHANGELOG.md`
- Create: `CONTRIBUTING.md`
- Create: `LICENSE`
- Create: `docs/development.md`

- [ ] 写入版本、manifest、README、贡献指南、变更记录、保留权利声明和开发说明。
- [ ] README 必须说明：`.codex\skills\<skill-name>` 是 junction，真实文件在 `patents-workflow\skills\<skill-name>`。
- [ ] 提交：`添加仓库治理文件`

## Task 2: 导入并清理 skill

**Files:**
- Create: `skills/<skill-name>/...`

- [ ] 从 `C:\Users\spade k\.codex\skills` 复制 manifest 声明的 15 个 skill 到 `skills/`。
- [ ] 删除 `__pycache__/`、`*.pyc`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`。
- [ ] 验证每个 `skills/<skill-name>/SKILL.md` 存在。
- [ ] 提交：`导入 workflow skill`

## Task 3: 创建检查脚本

**Files:**
- Create: `scripts/check-release.ps1`
- Create: `scripts/check-live-links.ps1`

- [ ] `check-release.ps1` 检查 manifest、VERSION、README、SKILL.md frontmatter、缓存产物和明显 secret。
- [ ] `check-live-links.ps1` 检查 `.codex\skills` 下 15 个 live 目录是否为 junction，且目标指向仓库 `skills/`。
- [ ] 运行两个检查脚本，确认 release check 在创建 junction 前可通过，live links check 在创建 junction 前应报告尚未链接。
- [ ] 提交：`添加仓库检查脚本`

## Task 4: 替换 live 目录为 junction

**Files:**
- Modify outside repo: `C:\Users\spade k\.codex\skills\<skill-name>`

- [ ] 创建备份目录：`C:\Users\spade k\.codex\skills\.patents-workflow-backup-<timestamp>`。
- [ ] 对 manifest 中 15 个 skill：确认仓库源目录存在且有 `SKILL.md`。
- [ ] 将 `.codex\skills\<skill-name>` 原目录移动到备份目录。
- [ ] 用 `New-Item -ItemType Junction` 创建同名 junction，指向 `patents-workflow\skills\<skill-name>`。
- [ ] 运行 `scripts/check-live-links.ps1`，确认全部 live 目录是 junction。

## Task 5: 最终验证

- [ ] 运行 `scripts/check-release.ps1`。
- [ ] 运行 `scripts/check-live-links.ps1`。
- [ ] 运行 `git status --short`，确认只有预期变更。
- [ ] 提交文档和脚本的最终修订：`改用 junction 管理 live skill`
