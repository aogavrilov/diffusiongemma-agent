$ErrorActionPreference = "Stop"
# OpenCode can write non-fatal status messages to stderr. Preserve its process
# exit code instead of letting PowerShell promote those messages to exceptions.
$PSNativeCommandUseErrorActionPreference = $false
$rawArgs = @($args)
$disableMcp = $false
$compactAgent = $false
$workingDirectory = (Get-Location).Path
$openCodeArgs = New-Object System.Collections.Generic.List[string]

for ($index = 0; $index -lt $rawArgs.Count; $index++) {
    $arg = $rawArgs[$index]
    switch ($arg) {
        "-NoMcp" { $disableMcp = $true; continue }
        "--no-mcp" { $disableMcp = $true; continue }
        "-Compact" { $compactAgent = $true; $disableMcp = $true; continue }
        "--compact" { $compactAgent = $true; $disableMcp = $true; continue }
        "-WorkingDirectory" {
            if ($index + 1 -ge $rawArgs.Count) { throw "-WorkingDirectory requires a path" }
            $workingDirectory = $rawArgs[$index + 1]
            $index++
            continue
        }
        "--working-directory" {
            if ($index + 1 -ge $rawArgs.Count) { throw "--working-directory requires a path" }
            $workingDirectory = $rawArgs[$index + 1]
            $index++
            continue
        }
        default { $openCodeArgs.Add($arg) }
    }
}

$root = Split-Path -Parent $PSScriptRoot
$binary = Join-Path $root ".tools\opencode\node_modules\.bin\opencode.cmd"
$baseConfig = Join-Path $root "configs\opencode.dg.json"
if ($compactAgent) {
    $baseConfig = Join-Path $root "configs\opencode.dg-agent.json"
}

if ($workingDirectory) {
    if (-not (Test-Path -LiteralPath $workingDirectory -PathType Container)) {
        throw "OpenCode working directory does not exist: $workingDirectory"
    }
    Set-Location -LiteralPath $workingDirectory
}

if (-not (Test-Path -LiteralPath $binary)) {
    throw "OpenCode is not installed. Run .\scripts\install_opencode_windows.ps1 first."
}
if (-not (Test-Path -LiteralPath $baseConfig)) {
    throw "OpenCode provider config is missing: $baseConfig"
}

function ConvertTo-WslPath([string]$PathValue) {
    $full = [IO.Path]::GetFullPath($PathValue)
    if ($full -notmatch "^([A-Za-z]):\\(.*)$") {
        throw "Only local Windows drive paths can be passed to WSL: $full"
    }
    return "/mnt/$($Matches[1].ToLower())/$($Matches[2].Replace('\', '/'))"
}

$config = Get-Content -LiteralPath $baseConfig -Raw | ConvertFrom-Json
$config.provider.'diffusiongemma-local'.options.apiKey = "dg-opencode-windows"
if (-not $disableMcp) {
    $wslRoot = ConvertTo-WslPath $root
    $wslRepo = ConvertTo-WslPath (Get-Location).Path
    $mcpCommand = "DG_AGENT_PYTHON=/root/diffusiongemma-agent/.venv-wsl/bin/python DG_MCP_REPO='$wslRepo' exec '$wslRoot/scripts/run_mcp_server.sh'"
    $mcp = [ordered]@{
        dg_agent = [ordered]@{
            type = "local"
            command = @("wsl.exe", "--exec", "bash", "-lc", $mcpCommand)
            enabled = $true
        }
    }
    $config | Add-Member -NotePropertyName mcp -NotePropertyValue $mcp -Force
}

$configPath = Join-Path $env:TEMP "diffusiongemma-opencode-$PID.json"
try {
    $config | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $configPath -Encoding utf8
    $previousConfig = $env:OPENCODE_CONFIG
    $previousBashTimeout = $env:OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS
    $env:OPENCODE_CONFIG = $configPath
    if ($compactAgent) {
        # The delegated Aider session has a 420s wall limit. OpenCode's default
        # Bash timeout is shorter, so preserve the delegated result instead of
        # turning a still-running verified edit into a false success.
        $env:OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS = "450000"
    }
    if ($openCodeArgs.Count -gt 0 -and $openCodeArgs[0] -eq "run") {
        $capturedOutput = @(& $binary @openCodeArgs 2>&1 | ForEach-Object { $_.ToString() })
        $exitCode = $LASTEXITCODE
        $capturedOutput | ForEach-Object { Write-Output $_ }
        $combinedOutput = $capturedOutput -join "`n"
        if ($exitCode -eq 0 -and $combinedOutput -match "DG task runner finished: failed|Session status: failed|Agent status: failed") {
            [Console]::Error.WriteLine("OpenCode delegated task failed; see the tool result and DG session report.")
            $exitCode = 1
        }
    } else {
        & $binary @openCodeArgs
        $exitCode = $LASTEXITCODE
    }
} finally {
    if ($null -eq $previousConfig) {
        Remove-Item Env:OPENCODE_CONFIG -ErrorAction SilentlyContinue
    } else {
        $env:OPENCODE_CONFIG = $previousConfig
    }
    if ($null -eq $previousBashTimeout) {
        Remove-Item Env:OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS -ErrorAction SilentlyContinue
    } else {
        $env:OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS = $previousBashTimeout
    }
    Remove-Item -LiteralPath $configPath -Force -ErrorAction SilentlyContinue
}

exit $exitCode
