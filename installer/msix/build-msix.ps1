#Requires -Version 5.1
<#
.SYNOPSIS
  Pack dist\uvdrop into an .msix (shared payload with Inno).

.PARAMETER SignLocal
  Create a self-signed cert and sign for local sideload testing.
  Store submission packages do NOT need CA signing (Store re-signs).
#>
param(
  [switch]$SignLocal
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$MsixDir = Join-Path $Root "installer\msix"
$Payload = Join-Path $Root "dist\uvdrop"
$Stage = Join-Path $MsixDir "stage"
$OutDir = Join-Path $MsixDir "output"
$ManifestSrc = Join-Path $MsixDir "AppxManifest.xml"

function Get-AppVersion {
  $verFile = Join-Path $Root "src\uvdrop\version.py"
  $m = Select-String -Path $verFile -Pattern '__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
  if (-not $m) { throw "Cannot read version" }
  return $m.Matches[0].Groups[1].Value
}

function Find-MakeAppx {
  $roots = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
    "$env:ProgramFiles\Windows Kits\10\bin"
  )
  foreach ($root in $roots) {
    if (-not (Test-Path $root)) { continue }
    $found = Get-ChildItem -Path $root -Filter MakeAppx.exe -Recurse -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -match "\\x64\\" } |
      Sort-Object FullName -Descending |
      Select-Object -First 1
    if ($found) { return $found.FullName }
  }
  $cmd = Get-Command MakeAppx.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

function Find-SignTool {
  $roots = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
    "$env:ProgramFiles\Windows Kits\10\bin"
  )
  foreach ($root in $roots) {
    if (-not (Test-Path $root)) { continue }
    $found = Get-ChildItem -Path $root -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -match "\\x64\\" } |
      Sort-Object FullName -Descending |
      Select-Object -First 1
    if ($found) { return $found.FullName }
  }
  return $null
}

function Ensure-PlaceholderPng([string]$Path, [int]$W, [int]$H) {
  if (Test-Path $Path) { return }
  # Minimal valid 1x1 PNG expanded via .NET if available; else skip and warn
  Add-Type -AssemblyName System.Drawing
  $bmp = New-Object System.Drawing.Bitmap $W, $H
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::FromArgb(11, 110, 79))
  $g.Dispose()
  $dir = Split-Path $Path -Parent
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
}

$Version = Get-AppVersion
# MSIX Identity Version needs 4-part
$IdentityVersion = "$Version.0"
Write-Host "=== uvdrop MSIX v$Version ===" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $Payload "uvdrop.exe"))) {
  throw "Missing dist\uvdrop\uvdrop.exe — run installer\build.ps1 -SkipInno first"
}

$makeappx = Find-MakeAppx
if (-not $makeappx) {
  throw "MakeAppx.exe not found. Install Windows SDK (App packaging tools)."
}

if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage, $OutDir | Out-Null

Write-Host "Staging payload..."
Copy-Item -Path (Join-Path $Payload "*") -Destination $Stage -Recurse -Force

# Manifest with synced version
$manifestText = Get-Content $ManifestSrc -Raw -Encoding UTF8
$manifestText = [regex]::Replace($manifestText, 'Version="[0-9.]+"', "Version=`"$IdentityVersion`"")
Set-Content -Path (Join-Path $Stage "AppxManifest.xml") -Value $manifestText -Encoding UTF8

$assets = Join-Path $Stage "Assets"
Ensure-PlaceholderPng (Join-Path $assets "StoreLogo.png") 50 50
Ensure-PlaceholderPng (Join-Path $assets "Square150x150Logo.png") 150 150
Ensure-PlaceholderPng (Join-Path $assets "Square44x44Logo.png") 44 44
Ensure-PlaceholderPng (Join-Path $assets "Wide310x150Logo.png") 310 150
Ensure-PlaceholderPng (Join-Path $assets "SplashScreen.png") 620 300

$msix = Join-Path $OutDir "uvdrop-$Version.msix"
if (Test-Path $msix) { Remove-Item $msix -Force }

Write-Host "MakeAppx pack..."
& $makeappx pack /d $Stage /p $msix /o
if (-not (Test-Path $msix)) { throw "MakeAppx failed" }

if ($SignLocal) {
  $signtool = Find-SignTool
  if (-not $signtool) { throw "signtool.exe required for -SignLocal" }
  $certName = "CN=uvdrop-local-dev"
  $existing = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $certName } | Select-Object -First 1
  if (-not $existing) {
    Write-Host "Creating self-signed cert $certName ..."
    $existing = New-SelfSignedCertificate -Type CodeSigningCert -Subject $certName -CertStoreLocation Cert:\CurrentUser\My
  }
  Write-Host "Signing locally (sideload only)..."
  & $signtool sign /fd SHA256 /a /n "uvdrop-local-dev" $msix
  Write-Host "Install with: Add-AppxPackage `"$msix`""
} else {
  Write-Host "Unsigned package ready for Partner Center (Store will re-sign)." -ForegroundColor Green
}

Write-Host "Output: $msix ($([math]::Round((Get-Item $msix).Length/1MB,1)) MB)"
