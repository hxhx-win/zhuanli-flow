# Patents Workflow Local Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可协作、可检查、可同步的 `patents-workflow` 本地开发仓库，并把 15 个声明的 skill 纳入仓库。

**Architecture:** 仓库只作为开发源，不作为 Codex 实时 skill 根目录。`manifest.json` 是唯一 skill 清单来源；同步脚本按 manifest 把 `skills/<skill-name>` 同步到 `C:\Users\spade k\.codex\skills\<skill-name>`；发布前检查脚本验证仓库是否可提交、可协作、可发布。

**Tech Stack:** PowerShell 5+、Git、JSON、Markdown、Codex skill 目录规范。

---

## 文件结构与职责

- `VERSION`：套件版本号，初始值 `1.6.0`。
- `manifest.json`：套件元数据、版本号、skill 清单、vendored dependency 标记。
- `README.md`：中文优先的项目说明、安装/同步方式、skill 清单。
- `CHANGELOG.md`：中文变更记录，初始记录 `1.6.0` 本地整理。
- `CONTRIBUTING.md`：中文贡献指南，说明修改核心专利 skill 与 vendored skill 的边界。
- `LICENSE`：本地协作阶段采用保留权利声明；公开开源前再明确替换为正式开源 license。
- `.gitignore`：排除 Python 缓存、测试缓存、临时文件、本地环境文件。
- `docs/development.md`：中文开发说明，解释版本、同步、检查、发布流程。
- `scripts/check-release.ps1`：读取 manifest 并做发布前检查。
- `scripts/sync-to-codex-skills.ps1`：默认 dry-run，同步时显式传入 `-Apply`。
- `skills/`：15 个 skill 的开发副本，不包含 `__pycache__/`、`*.pyc` 等缓存产物。

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

- [ ] **Step 1: 写入 `VERSION`**

内容：

```text
1.6.0
```

- [ ] **Step 2: 写入 `manifest.json`**

内容：

```json
{
  "name": "patents-workflow",
  "version": "1.6.0",
  "description": "中文专利工作流 skill 套件，包含专利起草主流程和支撑型可视化、绘图、Markdown skill。",
  "skills": [
    { "name": "cn-patent-repo-scout", "role": "core" },
    { "name": "cn-patent-mainline-analysis", "role": "core" },
    { "name": "cn-patent-prior-art-search", "role": "core" },
    { "name": "cn-patent-disclosure-draft", "role": "core" },
    { "name": "cn-patent-disclosure-review", "role": "core" },
    { "name": "cn-patent-formal-drafting", "role": "core" },
    { "name": "cn-patent-attorney-review", "role": "core" },
    { "name": "cn-patent-docx-export", "role": "core" },
    { "name": "cn-patent-project-drafting", "role": "core" },
    { "name": "seaborn", "role": "vendored" },
    { "name": "scientific-visualization", "role": "vendored" },
    { "name": "scientific-schematics", "role": "vendored" },
    { "name": "matplotlib", "role": "vendored" },
    { "name": "markdown-mermaid-writing", "role": "vendored" },
    { "name": "generate-image", "role": "vendored" }
  ]
}
```

- [ ] **Step 3: 写入 `.gitignore`**

内容：

```gitignore
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
venv/
env/
.env
.env.*
*.tmp
*.temp
*.log
.DS_Store
Thumbs.db
```

- [ ] **Step 4: 写入 README 和协作文档**

`README.md` 必须包含以下段落：

```markdown
# patents-workflow

`patents-workflow` 是一个中文专利工作流 skill 套件开发仓库。仓库用于协作开发、发布前检查和版本管理；Codex 实际使用的 skill 仍同步到 `C:\Users\spade k\.codex\skills`。

## 当前版本

`1.6.0`

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
```

`CHANGELOG.md` 必须包含：

```markdown
# 变更记录

## 1.6.0 - 2026-06-06

- 建立 `patents-workflow` 本地开发仓库。
- 纳入 9 个 `cn-patent-*` 核心专利工作流 skill。
- 纳入 6 个支撑型 vendored skill。
- 添加 manifest、同步脚本和发布前检查脚本。
```

`CONTRIBUTING.md` 必须包含：

```markdown
# 贡献指南

本仓库以中文协作为主。路径、命令、代码标识符、版本号、文件名和 GitHub 专有名词可保留英文。

## 修改范围

- `cn-patent-*` 是核心专利工作流 skill，可以在明确任务范围内修改。
- `seaborn`、`scientific-visualization`、`scientific-schematics`、`matplotlib`、`markdown-mermaid-writing`、`generate-image` 是支撑型 vendored skill。除非任务明确要求，默认只同步和检查，不主动改造行为。

## 提交前检查

```powershell
.\scripts\check-release.ps1
```

## 版本规则

- `1.6.x`：修复、文档、兼容性调整。
- `1.7.0`：新增能力或调整工作流契约。
- `2.0.0`：破坏性变化。
```

`LICENSE` 必须包含：

```text
Copyright (c) hxhx-win.

All rights reserved.

This repository is being prepared for collaborative development. A public open-source license has not been selected yet. Do not redistribute, sublicense, or publish this repository until the license is replaced with an explicit open-source license.
```

`docs/development.md` 必须包含：

```markdown
# 开发说明

## 仓库定位

`patents-workflow` 是开发仓库，不是 Codex 实时 skill 根目录。Codex 实际读取 `C:\Users\spade k\.codex\skills\<skill-name>`。

## 本地检查

```powershell
.\scripts\check-release.ps1
```

## 同步流程

先 dry-run：

```powershell
.\scripts\sync-to-codex-skills.ps1
```

确认输出后再实际同步：

```powershell
.\scripts\sync-to-codex-skills.ps1 -Apply
```

## 版本迭代

仓库名保持 `patents-workflow` 不变。版本通过 `VERSION`、`manifest.json`、`CHANGELOG.md`、git tag 和 GitHub Release 管理。
```

## 同步到 Codex

默认 dry-run：

```powershell
.\scripts\sync-to-codex-skills.ps1
```

实际同步：

```powershell
.\scripts\sync-to-codex-skills.ps1 -Apply
```
```

- [ ] **Step 5: 运行基本 git 检查**

Run:

```powershell
git status --short
```

Expected: 显示 Task 1 新增文件，且没有 `skills/` 内容。

- [ ] **Step 6: 提交 Task 1**

Run:

```powershell
git add VERSION manifest.json .gitignore README.md CHANGELOG.md CONTRIBUTING.md LICENSE docs/development.md
git commit -m "Add repository governance files"
```

Expected: commit 成功。

## Task 2: 复制 15 个 skill 并清理缓存

**Files:**
- Create: `skills/<skill-name>/...`

- [ ] **Step 1: 创建 `skills/` 目录**

Run:

```powershell
New-Item -ItemType Directory -Path .\skills -Force | Out-Null
```

Expected: `skills/` 存在。

- [ ] **Step 2: 按 manifest 复制 skill**

Run:

```powershell
$manifest = Get-Content -LiteralPath .\manifest.json -Raw | ConvertFrom-Json
foreach ($skill in $manifest.skills) {
  $src = Join-Path 'C:\Users\spade k\.codex\skills' $skill.name
  $dst = Join-Path '.\skills' $skill.name
  if (-not (Test-Path -LiteralPath (Join-Path $src 'SKILL.md'))) {
    throw "Source skill missing SKILL.md: $src"
  }
  if (Test-Path -LiteralPath $dst) {
    Remove-Item -LiteralPath $dst -Recurse -Force
  }
  Copy-Item -LiteralPath $src -Destination $dst -Recurse
}
```

Expected: `skills/` 下出现 manifest 声明的 15 个目录。

- [ ] **Step 3: 删除缓存产物**

Run:

```powershell
Get-ChildItem -LiteralPath .\skills -Recurse -Directory -Force |
  Where-Object { $_.Name -in @('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache') } |
  Remove-Item -Recurse -Force

Get-ChildItem -LiteralPath .\skills -Recurse -File -Force |
  Where-Object { $_.Extension -in @('.pyc', '.pyo') } |
  Remove-Item -Force
```

Expected: 命令完成，无错误。

- [ ] **Step 4: 验证缓存已清理**

Run:

```powershell
Get-ChildItem -LiteralPath .\skills -Recurse -Force |
  Where-Object { $_.FullName -match '\\(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)\\|\.py[co]$' }
```

Expected: 无输出。

- [ ] **Step 5: 验证每个 skill 有 `SKILL.md`**

Run:

```powershell
$manifest = Get-Content -LiteralPath .\manifest.json -Raw | ConvertFrom-Json
foreach ($skill in $manifest.skills) {
  $path = Join-Path '.\skills' $skill.name
  if (-not (Test-Path -LiteralPath (Join-Path $path 'SKILL.md'))) {
    throw "Missing SKILL.md: $path"
  }
}
```

Expected: 无输出、无异常。

- [ ] **Step 6: 提交 Task 2**

Run:

```powershell
git add skills
git commit -m "Import workflow skills"
```

Expected: commit 成功。

## Task 3: 实现发布前检查脚本

**Files:**
- Create: `scripts/check-release.ps1`

- [ ] **Step 1: 写入 `scripts/check-release.ps1`**

内容：

```powershell
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $RepoRoot 'manifest.json'
$VersionPath = Join-Path $RepoRoot 'VERSION'
$ReadmePath = Join-Path $RepoRoot 'README.md'
$SkillsRoot = Join-Path $RepoRoot 'skills'
$errors = New-Object System.Collections.Generic.List[string]

function Add-CheckError([string]$Message) {
  $script:errors.Add($Message) | Out-Null
}

if (-not (Test-Path -LiteralPath $ManifestPath)) {
  throw "manifest.json not found: $ManifestPath"
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$version = (Get-Content -LiteralPath $VersionPath -Raw).Trim()

if ($manifest.version -ne $version) {
  Add-CheckError "VERSION ($version) does not match manifest.json.version ($($manifest.version))."
}

$readme = ''
if (Test-Path -LiteralPath $ReadmePath) {
  $readme = Get-Content -LiteralPath $ReadmePath -Raw
} else {
  Add-CheckError "README.md not found."
}

foreach ($skill in $manifest.skills) {
  $skillName = [string]$skill.name
  $skillPath = Join-Path $SkillsRoot $skillName
  $skillMd = Join-Path $skillPath 'SKILL.md'

  if (-not (Test-Path -LiteralPath $skillPath)) {
    Add-CheckError "Skill directory not found: skills/$skillName"
    continue
  }

  if (-not (Test-Path -LiteralPath $skillMd)) {
    Add-CheckError "SKILL.md not found: skills/$skillName/SKILL.md"
    continue
  }

  $text = Get-Content -LiteralPath $skillMd -Raw
  if ($text -notmatch '(?s)^---\s.*?\bname\s*:.*?\bdescription\s*:.*?---') {
    Add-CheckError "SKILL.md frontmatter must include name and description: skills/$skillName/SKILL.md"
  }

  if ($readme -and $readme -notmatch [regex]::Escape($skillName)) {
    Add-CheckError "README.md does not mention manifest skill: $skillName"
  }
}

$cacheHits = Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force |
  Where-Object { $_.FullName -match '\\(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)(\\|$)|\.py[co]$' }
foreach ($hit in $cacheHits) {
  Add-CheckError "Cache/generated file should not be committed: $($hit.FullName)"
}

$secretPattern = '((api[_-]?key|client_secret|password)\s*[:=]\s*[''"]?[^''"\s]{8,}|bearer\s+[A-Za-z0-9._-]{20,}|sk-[A-Za-z0-9]{20,}|BEGIN .*PRIVATE KEY)'
$textFiles = Get-ChildItem -LiteralPath $RepoRoot -Recurse -File -Force |
  Where-Object {
    $_.FullName -notmatch '\\.git\\' -and
    $_.Extension -notin @('.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.docx', '.pptx', '.xlsx')
  }
foreach ($file in $textFiles) {
  $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
  if ($content -match $secretPattern) {
    Add-CheckError "Possible secret pattern found: $($file.FullName)"
  }
}

if ($errors.Count -gt 0) {
  Write-Host 'Release check failed:' -ForegroundColor Red
  foreach ($err in $errors) {
    Write-Host " - $err" -ForegroundColor Red
  }
  exit 1
}

Write-Host 'Release check passed.' -ForegroundColor Green
```

- [ ] **Step 2: 运行检查脚本**

Run:

```powershell
.\scripts\check-release.ps1
```

Expected: 输出 `Release check passed.`

- [ ] **Step 3: 提交 Task 3**

Run:

```powershell
git add scripts/check-release.ps1
git commit -m "Add release check script"
```

Expected: commit 成功。

## Task 4: 实现同步脚本

**Files:**
- Create: `scripts/sync-to-codex-skills.ps1`

- [ ] **Step 1: 写入 `scripts/sync-to-codex-skills.ps1`**

内容：

```powershell
param(
  [switch]$Apply,
  [string]$TargetRoot = 'C:\Users\spade k\.codex\skills'
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $RepoRoot 'manifest.json'
$SkillsRoot = Join-Path $RepoRoot 'skills'
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json

function Copy-SkillClean {
  param(
    [string]$Source,
    [string]$Destination
  )

  if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
  }

  New-Item -ItemType Directory -Path $Destination -Force | Out-Null

  $items = Get-ChildItem -LiteralPath $Source -Recurse -Force
  foreach ($item in $items) {
    $relative = $item.FullName.Substring($Source.Length).TrimStart('\', '/')
    if ($relative -match '(^|[\\/])(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)([\\/]|$)|\.py[co]$') {
      continue
    }

    $target = Join-Path $Destination $relative
    if ($item.PSIsContainer) {
      New-Item -ItemType Directory -Path $target -Force | Out-Null
    } else {
      $parent = Split-Path -Parent $target
      New-Item -ItemType Directory -Path $parent -Force | Out-Null
      Copy-Item -LiteralPath $item.FullName -Destination $target -Force
    }
  }
}

foreach ($skill in $manifest.skills) {
  $skillName = [string]$skill.name
  $source = Join-Path $SkillsRoot $skillName
  $destination = Join-Path $TargetRoot $skillName
  $skillMd = Join-Path $source 'SKILL.md'

  if (-not (Test-Path -LiteralPath $skillMd)) {
    throw "Source skill missing SKILL.md: $source"
  }

  if ($Apply) {
    Write-Host "Syncing $skillName -> $destination"
    Copy-SkillClean -Source $source -Destination $destination
  } else {
    Write-Host "[dry-run] Would sync $skillName -> $destination"
  }
}

if (-not $Apply) {
  Write-Host 'Dry-run complete. Re-run with -Apply to write changes.'
}
```

- [ ] **Step 2: 运行 dry-run**

Run:

```powershell
.\scripts\sync-to-codex-skills.ps1
```

Expected: 每个 skill 输出一行 `[dry-run] Would sync ...`，最后输出 `Dry-run complete. Re-run with -Apply to write changes.`

- [ ] **Step 3: 提交 Task 4**

Run:

```powershell
git add scripts/sync-to-codex-skills.ps1
git commit -m "Add Codex skill sync script"
```

Expected: commit 成功。

## Task 5: 最终验证

**Files:**
- Modify: none

- [ ] **Step 1: 运行发布前检查**

Run:

```powershell
.\scripts\check-release.ps1
```

Expected: `Release check passed.`

- [ ] **Step 2: 运行同步 dry-run**

Run:

```powershell
.\scripts\sync-to-codex-skills.ps1
```

Expected: 15 个 skill 的 dry-run 同步输出。

- [ ] **Step 3: 检查 Git 状态**

Run:

```powershell
git status --short
```

Expected: 无输出。

- [ ] **Step 4: 记录当前提交历史**

Run:

```powershell
git log --oneline --max-count=6
```

Expected: 能看到 spec、plan 和各任务提交。
