[CmdletBinding()]
param(
    [string]$Version = "1.17.20"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$prefix = Join-Path $root ".tools\opencode"
$package = "opencode-ai@$Version"

if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
    throw "node.exe is required to install OpenCode. Install Node.js, then retry."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm.cmd is required to install OpenCode."
}

New-Item -ItemType Directory -Force -Path $prefix | Out-Null
& npm.cmd install --prefix $prefix --no-audit --no-fund --ignore-scripts $package
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$postInstall = Join-Path $prefix "node_modules\opencode-ai\postinstall.mjs"
if (-not (Test-Path -LiteralPath $postInstall)) {
    throw "OpenCode package is incomplete: $postInstall is missing."
}
& node.exe $postInstall
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$binary = Join-Path $prefix "node_modules\.bin\opencode.cmd"
if (-not (Test-Path -LiteralPath $binary)) {
    throw "OpenCode binary is missing after install: $binary"
}
& $binary --version
exit $LASTEXITCODE
