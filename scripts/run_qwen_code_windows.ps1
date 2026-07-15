$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$QwenArgs = @($args)
$root = Split-Path -Parent $PSScriptRoot
$binary = Join-Path $root ".tools\qwen-code\node_modules\.bin\qwen.cmd"
$node22 = Join-Path $root ".tools\node-v22.17.1-win-x64\node.exe"
$entryPoint = Join-Path $root ".tools\qwen-code\node_modules\@qwen-code\qwen-code\cli-entry.js"
$repo = (Get-Location).Path
$dryRun = $false
$helpLocal = $false
$passThrough = New-Object System.Collections.Generic.List[string]

for ($index = 0; $index -lt $QwenArgs.Count; $index++) {
    $arg = $QwenArgs[$index]
    switch ($arg) {
        "--repo" {
            if ($index + 1 -ge $QwenArgs.Count) { throw "--repo requires a path" }
            $repo = $QwenArgs[$index + 1]
            $index++
            continue
        }
        "--dry-run" {
            $dryRun = $true
            continue
        }
        "--help-local" {
            $helpLocal = $true
            continue
        }
        "--no-mcp" { continue }
        "--" { continue }
        default {
            $passThrough.Add($arg)
        }
    }
}

if ($helpLocal) {
    @"
Runs the native Windows Qwen Code CLI against the local GPU model.

Usage:
  scripts\run_qwen_code_windows.ps1 --repo PATH [--dry-run] -- [qwen args]

This integration is intentionally read-only. Use Aider for edits.
"@
    exit 0
}

if (-not (Test-Path -LiteralPath $binary)) {
    throw "Qwen Code is not installed. Run npm install --prefix .tools\qwen-code @qwen-code/qwen-code@latest"
}
if (-not (Test-Path -LiteralPath $entryPoint)) {
    throw "Qwen Code entry point is missing: $entryPoint"
}
if (-not (Test-Path -LiteralPath $repo -PathType Container)) {
    throw "Repository directory does not exist: $repo"
}

$repo = (Resolve-Path -LiteralPath $repo).Path
$repoToken = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($repo)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$env:OPENAI_API_KEY = "dg-qwen-windows.$repoToken"
$env:OPENAI_BASE_URL = "http://127.0.0.1:8090/v1"
$env:OPENAI_MODEL = "diffusiongemma-26b-a4b-it-iq4xs-aider-local"
$command = @(
    "--auth-type", "openai",
    "--model", $env:OPENAI_MODEL,
    "--openaiApiKey", $env:OPENAI_API_KEY,
    "--openaiBaseUrl", $env:OPENAI_BASE_URL,
    "--telemetry=false",
    "--safe-mode"
) + $passThrough.ToArray()

if ($dryRun) {
    "repo: $repo"
    "qwen: $binary"
    "openai_base_url: $env:OPENAI_BASE_URL"
    "openai_model: $env:OPENAI_MODEL"
    "mode: read-only"
    "command: $binary $($command -join ' ')"
    exit 0
}

Push-Location -LiteralPath $repo
try {
    # Qwen Code currently writes an abort diagnostic to stderr on Windows.
    # Let the native process return its real code so callers can distinguish
    # it from a PowerShell wrapper failure.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if (Test-Path -LiteralPath $node22) {
        & $node22 $entryPoint @command
    } else {
        & $binary @command
    }
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
} finally {
    Pop-Location
}

exit $exitCode
