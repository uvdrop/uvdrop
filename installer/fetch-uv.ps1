#Requires -Version 5.1
<#
.SYNOPSIS
  Download official uv.exe into resources/tools/windows-x64/
#>
param(
  [string]$Version = "latest"
)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DestDir = Join-Path $Root "resources\tools\windows-x64"
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
$Dest = Join-Path $DestDir "uv.exe"

if ($Version -eq "latest") {
  $Api = "https://api.github.com/repos/astral-sh/uv/releases/latest"
  Write-Host "Fetching latest uv release metadata..."
  $rel = Invoke-RestMethod -Uri $Api -Headers @{ "User-Agent" = "uvdrop-fetch-uv" }
  $asset = $rel.assets | Where-Object { $_.name -match "uv-x86_64-pc-windows-msvc\.zip$" } | Select-Object -First 1
  if (-not $asset) { throw "Could not find Windows x64 uv zip in latest release" }
  $Url = $asset.browser_download_url
  Write-Host "Release: $($rel.tag_name)"
} else {
  $tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
  $Url = "https://github.com/astral-sh/uv/releases/download/$tag/uv-x86_64-pc-windows-msvc.zip"
}

$Zip = Join-Path $env:TEMP "uv-windows-x64.zip"
Write-Host "Downloading $Url"
Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing

$Extract = Join-Path $env:TEMP "uvdrop-uv-extract"
if (Test-Path $Extract) { Remove-Item $Extract -Recurse -Force }
Expand-Archive -Path $Zip -DestinationPath $Extract -Force

$Found = Get-ChildItem -Path $Extract -Filter uv.exe -Recurse | Select-Object -First 1
if (-not $Found) { throw "uv.exe not found inside zip" }
Copy-Item $Found.FullName $Dest -Force
Write-Host "Installed: $Dest ($([math]::Round((Get-Item $Dest).Length/1MB,1)) MB)"
