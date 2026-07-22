#Requires -Version 5.1
<#
.SYNOPSIS
  Build onedir payload for Inno Setup (does not compile the installer itself).
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "Installing packaging deps..."
python -m pip install -U pip pyinstaller hatchling

Write-Host "Building wheel/editable context..."
python -m pip install -e .

$UvSrc = Join-Path $Root "resources\tools\windows-x64\uv.exe"
if (-not (Test-Path $UvSrc)) {
  Write-Warning "uv.exe missing at $UvSrc — installer will skip bundling it unless you add it."
}

Write-Host "PyInstaller onedir..."
$dist = Join-Path $Root "dist"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name uvdrop `
  --paths src `
  --add-data "policies;policies" `
  --hidden-import uvdrop.ui.app `
  src/uvdrop/__main__.py

Write-Host "Done. Compile installer\uvdrop.iss with Inno Setup next."
Write-Host "Output app dir: dist\uvdrop\"
