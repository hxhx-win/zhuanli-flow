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

function Read-Utf8([string]$Path) {
  return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $ManifestPath)) {
  throw "manifest.json not found: $ManifestPath"
}

if (-not (Test-Path -LiteralPath $VersionPath)) {
  Add-CheckError 'VERSION not found.'
}

$manifest = Read-Utf8 $ManifestPath | ConvertFrom-Json
$version = ''
if (Test-Path -LiteralPath $VersionPath) {
  $version = (Read-Utf8 $VersionPath).Trim()
}

if ($manifest.version -ne $version) {
  Add-CheckError "VERSION ($version) does not match manifest.json.version ($($manifest.version))."
}

$readme = ''
if (Test-Path -LiteralPath $ReadmePath) {
  $readme = Read-Utf8 $ReadmePath
} else {
  Add-CheckError 'README.md not found.'
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

  $text = Read-Utf8 $skillMd
  $frontmatterMatch = [regex]::Match($text, '(?s)^---\s*(.*?)\s*---')
  if (-not $frontmatterMatch.Success) {
    Add-CheckError "SKILL.md frontmatter not found: skills/$skillName/SKILL.md"
  } else {
    $frontmatter = $frontmatterMatch.Groups[1].Value
    if ($frontmatter -notmatch '(?m)^name\s*:') {
      Add-CheckError "SKILL.md frontmatter missing name: skills/$skillName/SKILL.md"
    }
    if ($frontmatter -notmatch '(?m)^description\s*:') {
      Add-CheckError "SKILL.md frontmatter missing description: skills/$skillName/SKILL.md"
    }
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

$secretPattern = '(bearer\s+[A-Za-z0-9._-]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN .*PRIVATE KEY)'
$textFiles = Get-ChildItem -LiteralPath $RepoRoot -Recurse -File -Force |
  Where-Object {
    $_.FullName -notmatch '\\.git\\' -and
    $_.FullName -ne $PSCommandPath -and
    $_.Extension -notin @('.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.docx', '.pptx', '.xlsx')
  }
foreach ($file in $textFiles) {
  try {
    $content = Read-Utf8 $file.FullName
  } catch {
    continue
  }
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
