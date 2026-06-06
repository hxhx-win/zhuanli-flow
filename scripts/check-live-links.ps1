param(
  [string]$LiveRoot = 'C:\Users\spade k\.codex\skills'
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $RepoRoot 'manifest.json'
$SkillsRoot = Join-Path $RepoRoot 'skills'
$errors = New-Object System.Collections.Generic.List[string]

function Add-CheckError([string]$Message) {
  $script:errors.Add($Message) | Out-Null
}

function Get-LinkTargetText($Item) {
  if ($Item.PSObject.Properties.Name -contains 'Target' -and $Item.Target) {
    if ($Item.Target -is [array]) {
      return [string]$Item.Target[0]
    }
    return [string]$Item.Target
  }
  if ($Item.PSObject.Properties.Name -contains 'LinkTarget' -and $Item.LinkTarget) {
    return [string]$Item.LinkTarget
  }
  return ''
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

foreach ($skill in $manifest.skills) {
  $skillName = [string]$skill.name
  $livePath = Join-Path $LiveRoot $skillName
  $repoPath = Join-Path $SkillsRoot $skillName

  if (-not (Test-Path -LiteralPath $livePath)) {
    Add-CheckError "Live skill path not found: $livePath"
    continue
  }

  $item = Get-Item -LiteralPath $livePath -Force
  $isReparsePoint = [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
  if (-not $isReparsePoint) {
    Add-CheckError "Live skill is not a junction/reparse point: $livePath"
    continue
  }

  $target = Get-LinkTargetText $item
  if (-not $target) {
    Add-CheckError "Unable to read junction target: $livePath"
    continue
  }

  $resolvedTarget = [IO.Path]::GetFullPath($target).TrimEnd('\')
  $expectedTarget = [IO.Path]::GetFullPath($repoPath).TrimEnd('\')
  if ($resolvedTarget -ne $expectedTarget) {
    Add-CheckError "Live skill target mismatch: $livePath -> $resolvedTarget, expected $expectedTarget"
  }
}

if ($errors.Count -gt 0) {
  Write-Host 'Live link check failed:' -ForegroundColor Red
  foreach ($err in $errors) {
    Write-Host " - $err" -ForegroundColor Red
  }
  exit 1
}

Write-Host 'Live link check passed.' -ForegroundColor Green
