# audit_sendmax.ps1 (paso 4: parse_mode y sanitización)
$ErrorActionPreference = "Continue"

function Section([string]$title) {
  Write-Host ""
  Write-Host "============================================================"
  Write-Host $title
  Write-Host "============================================================"
}

function Find-InFiles {
  param(
    [Parameter(Mandatory=$true)][string[]]$Paths,
    [Parameter(Mandatory=$true)][string]$Pattern
  )
  $existing = @()
  foreach ($p in $Paths) { if (Test-Path $p) { $existing += $p } else { Write-Host ("MISS " + $p) } }
  if ($existing.Count -eq 0) { return }
  Select-String -Path $existing -Pattern $Pattern -AllMatches | ForEach-Object {
    "{0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim()
  }
}

Section "4) parse_mode + escape (HTML/Markdown)"
Find-InFiles -Paths @("src\telegram_app") -Pattern "parse_mode\s*=|ParseMode\."
Find-InFiles -Paths @("src\telegram_app") -Pattern "beneficiary|beneficiario|cuenta|account|bank|banco|nota|note"
Find-InFiles -Paths @("src\telegram_app") -Pattern "html\.escape|escape_markdown|telegram\.helpers\.escape"
