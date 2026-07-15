[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("read", "edit")]
    [string]$Mode,
    [Parameter(Mandatory = $true)]
    [string]$TaskBase64,
    [ValidateRange(1, 4)]
    [int]$MaxFiles = 1
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if ($root -notmatch "^([A-Za-z]):\\(.*)$") {
    throw "The DG delegate requires a drive-rooted Windows checkout: $root"
}

$drive = $Matches[1].ToLowerInvariant()
$tail = $Matches[2].Replace("\", "/")
$wslRoot = "/mnt/$drive/$tail"
$cwd = (Get-Location).Path
$wslRepo = (& wsl.exe --exec wslpath -a $cwd).Trim()
if (-not $wslRepo) {
    throw "Could not convert the current directory to a WSL path: $cwd"
}

try {
    $task = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($TaskBase64))
} catch {
    throw "TaskBase64 is not valid UTF-8 base64."
}

$wslArgs = @(
    "--exec",
    "env",
    "DG_AGENT_PYTHON=/root/diffusiongemma-agent/.venv-wsl/bin/python",
    "$wslRoot/scripts/dg_agent.sh"
)
if ($Mode -eq "read") {
    $wslArgs += @(
        "agent",
        "--repo", $wslRepo,
        "--task", $task,
        "--mode", "read",
        "--max-steps", "1",
        "--max-tokens", "128",
        "--timeout", "180"
    )
} else {
    $wslArgs += @(
        "autonomous",
        "--",
        "--repo", $wslRepo,
        "--task", $task,
        "--max-files", "$MaxFiles",
        "--max-steps", "3",
        "--wall-timeout", "420",
        "--aider-timeout", "300",
        "--repair-attempts", "1",
        "--auto-test"
    )
}

& wsl.exe @wslArgs
exit $LASTEXITCODE
