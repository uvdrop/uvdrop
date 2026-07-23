#Requires -Version 5.1
<#
.SYNOPSIS
  Build uvdrop payload (PyInstaller) and optionally compile Setup.exe with Inno Setup.

.PARAMETER SkipInno
  Only build dist\uvdrop\ (no ISCC).

.PARAMETER SkipFetchUv
  Do not download uv.exe if missing.

.PARAMETER Sign
  After Inno build, run sign.ps1 if SIGN_CERT_THUMBPRINT (or params) are set.
#>
param(
  [switch]$SkipInno,
  [switch]$SkipFetchUv,
  [switch]$Sign
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Get-AppVersion {
  $verFile = Join-Path $Root "src\uvdrop\version.py"
  $m = Select-String -Path $verFile -Pattern '__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
  if (-not $m) { throw "Cannot read version from src\uvdrop\version.py" }
  return $m.Matches[0].Groups[1].Value
}

function Find-ISCC {
  $candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
  )
  foreach ($p in $candidates) {
    if ($p -and (Test-Path $p)) { return $p }
  }
  $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

$Version = Get-AppVersion
Write-Host "=== uvdrop packaging v$Version ===" -ForegroundColor Cyan

# Sync version into .iss (#define MyAppVersion)
$Iss = Join-Path $Root "installer\uvdrop.iss"
$issText = Get-Content $Iss -Raw -Encoding UTF8
$issText = [regex]::Replace($issText, '#define MyAppVersion "[^"]+"', "#define MyAppVersion `"$Version`"")
Set-Content -Path $Iss -Value $issText -Encoding UTF8 -NoNewline
Write-Host "Synced installer\uvdrop.iss → MyAppVersion $Version"

# uv.exe
$UvSrc = Join-Path $Root "resources\tools\windows-x64\uv.exe"
if (-not (Test-Path $UvSrc)) {
  if ($SkipFetchUv) {
    Write-Warning "uv.exe missing at $UvSrc"
  } else {
    Write-Host "Fetching uv.exe..."
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "fetch-uv.ps1")
  }
}

Write-Host "Installing packaging deps (pip)..."
python -m pip install -U pip pyinstaller hatchling | Out-Host
python -m pip install -e . | Out-Host

$dist = Join-Path $Root "dist"
$build = Join-Path $Root "build"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }

Write-Host "PyInstaller onedir (uvdrop.spec)..."
python -m PyInstaller --noconfirm --clean uvdrop.spec
if (-not (Test-Path (Join-Path $dist "uvdrop\uvdrop.exe"))) {
  throw "PyInstaller failed: dist\uvdrop\uvdrop.exe not found"
}

# Ensure tools\uv.exe next to payload for local smoke tests (Inno also copies from resources)
$PayloadTools = Join-Path $dist "uvdrop\tools"
New-Item -ItemType Directory -Force -Path $PayloadTools | Out-Null
if (Test-Path $UvSrc) {
  Copy-Item $UvSrc (Join-Path $PayloadTools "uv.exe") -Force
}

Write-Host "Payload OK: dist\uvdrop\" -ForegroundColor Green

# Compliance files into payload (Inno/MSIX both ship these)
$PayloadRoot = Join-Path $dist "uvdrop"
foreach ($f in @("LICENSE", "THIRD_PARTY_NOTICES.md", "README.md")) {
  $src = Join-Path $Root $f
  if (Test-Path $src) { Copy-Item $src $PayloadRoot -Force }
}
$tpSrc = Join-Path $Root "third_party"
$tpDst = Join-Path $PayloadRoot "third_party"
if (Test-Path $tpSrc) {
  if (Test-Path $tpDst) { Remove-Item $tpDst -Recurse -Force }
  Copy-Item $tpSrc $tpDst -Recurse -Force
}
Write-Host "Bundled LICENSE + third_party into payload"

if ($SkipInno) {
  Write-Host "SkipInno set — done."
  exit 0
}

$iscc = Find-ISCC
if (-not $iscc) {
  Write-Host ""
  Write-Host "Inno Setup 6 (ISCC.exe) not found." -ForegroundColor Yellow
  Write-Host "Install with:"
  Write-Host "  winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements"
  Write-Host "Or see installer\PACKAGING.md"
  Write-Host "Payload is ready; re-run this script after installing Inno."
  exit 2
}

$OutDir = Join-Path $Root "installer\output"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Write-Host "Compiling Setup.exe with:`n  $iscc"
& $iscc $Iss
$Setup = Join-Path $OutDir "uvdrop-$Version-setup.exe"
if (-not (Test-Path $Setup)) {
  throw "Expected output missing: $Setup"
}
Write-Host "Setup built: $Setup ($([math]::Round((Get-Item $Setup).Length/1MB,1)) MB)" -ForegroundColor Green

if ($Sign) {
  & (Join-Path $PSScriptRoot "sign.ps1") -Path $Setup
}

Write-Host ""
Write-Host "Next: upload to GitHub Releases (tag v$Version). See installer\PACKAGING.md"
