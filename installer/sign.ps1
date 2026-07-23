#Requires -Version 5.1
<#
.SYNOPSIS
  Authenticode-sign a file (Setup.exe or uvdrop.exe) with signtool.

.PARAMETER Path
  File to sign.

.PARAMETER Thumbprint
  Certificate thumbprint. Falls back to env SIGN_CERT_THUMBPRINT.

.PARAMETER TimestampUrl
  RFC3161 timestamp server.
#>
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Thumbprint = $env:SIGN_CERT_THUMBPRINT,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Path)) { throw "File not found: $Path" }
if (-not $Thumbprint) {
  Write-Host @"
No certificate thumbprint.
Set SIGN_CERT_THUMBPRINT or pass -Thumbprint.

Examples:
  # List codesigning certs in CurrentUser\My
  Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.HasPrivateKey } |
    Format-Table Thumbprint, Subject

  `$env:SIGN_CERT_THUMBPRINT = 'YOURTHUMBPRINT'
  .\installer\sign.ps1 -Path .\installer\output\uvdrop-0.3.0-setup.exe
"@
  exit 1
}

function Find-SignTool {
  $roots = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
    "$env:ProgramFiles\Windows Kits\10\bin"
  )
  foreach ($root in $roots) {
    if (-not (Test-Path $root)) { continue }
    $found = Get-ChildItem -Path $root -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending |
      Select-Object -First 1
    if ($found) { return $found.FullName }
  }
  $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

$signtool = Find-SignTool
if (-not $signtool) {
  throw "signtool.exe not found. Install Windows SDK (Signing Tools)."
}

Write-Host "Signing $Path"
Write-Host "  signtool: $signtool"
& $signtool sign /fd SHA256 /tr $TimestampUrl /td SHA256 /sha1 $Thumbprint $Path
if ($LASTEXITCODE -ne 0) { throw "signtool failed ($LASTEXITCODE)" }
& $signtool verify /pa $Path
Write-Host "Signed OK." -ForegroundColor Green
