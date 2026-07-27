#Requires -Version 5.1
<#
.SYNOPSIS
  Serve examples/local-portal as a tiny HTTP catalog endpoint for local testing.

Registers as e.g. http://127.0.0.1:8765/uvdrop-catalog.json in uvdrop Settings → Catalogs.
Rewrites "base" in the JSON to this folder's absolute path so relative app paths resolve.
#>
param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path $PSScriptRoot
$CatalogSrc = Join-Path $Root "uvdrop-catalog.json"
if (-not (Test-Path $CatalogSrc)) { throw "Missing $CatalogSrc" }

$doc = Get-Content -Raw -Encoding UTF8 $CatalogSrc | ConvertFrom-Json
$doc | Add-Member -NotePropertyName base -NotePropertyValue ($Root.Path) -Force
$served = Join-Path $Root "_served-catalog.json"
($doc | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 -Path $served

Write-Host ""
Write-Host "Local catalog HTTP demo"
Write-Host "  folder : $Root"
Write-Host "  register this URL in uvdrop → Settings → Catalogs:"
Write-Host "    http://127.0.0.1:$Port/uvdrop-catalog.json"
Write-Host "  (also: http://127.0.0.1:$Port/_served-catalog.json)"
Write-Host "  Ctrl+C to stop"
Write-Host ""

# Map the pretty URL to the rewritten file via a tiny listener wrapper.
$listener = New-Object System.Net.HttpListener
$prefix = "http://127.0.0.1:$Port/"
$listener.Prefixes.Add($prefix)
$listener.Start()

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $path = $ctx.Request.Url.AbsolutePath.TrimStart("/")
    if ($path -eq "" -or $path -eq "uvdrop-catalog.json" -or $path -eq "_served-catalog.json") {
      $bytes = [System.IO.File]::ReadAllBytes($served)
      $ctx.Response.StatusCode = 200
      $ctx.Response.ContentType = "application/json; charset=utf-8"
      $ctx.Response.ContentLength64 = $bytes.Length
      $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $ctx.Response.StatusCode = 404
      $msg = [Text.Encoding]::UTF8.GetBytes('{"error":"not found"}')
      $ctx.Response.ContentType = "application/json"
      $ctx.Response.OutputStream.Write($msg, 0, $msg.Length)
    }
    $ctx.Response.Close()
  }
} finally {
  $listener.Stop()
  if (Test-Path $served) { Remove-Item $served -Force -ErrorAction SilentlyContinue }
}
