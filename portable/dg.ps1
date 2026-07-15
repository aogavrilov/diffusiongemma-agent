[CmdletBinding()]
param(
    [string]$Repo = (Get-Location).Path,
    [string]$Task,
    [string]$File,
    [ValidateRange(1, 5)]
    [int]$MaxSteps = 3,
    [switch]$StartOnly,
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
$state = Get-Content -LiteralPath "$root\installed.json" -Raw | ConvertFrom-Json
$wslRoot = [string]$state.wsl_root
$backend = 'http://127.0.0.1:4100/healthz'
$gateway = 'http://127.0.0.1:8090/healthz'

function Test-Healthy([string]$Url) {
    try { return [bool](Invoke-RestMethod -Uri $Url -TimeoutSec 3).ok } catch { return $false }
}

function Start-WslComponent([string]$Name) {
    $script = "$wslRoot/scripts/run_runtime_component.sh"
    Start-Process -FilePath wsl.exe -ArgumentList @('--exec', $script, $Name) -WindowStyle Hidden | Out-Null
}

if ($Stop) {
    & wsl.exe --exec pkill -f -- "$wslRoot/server.py"
    & wsl.exe --exec pkill -f -- "$wslRoot/scripts/aider_dg_proxy.py"
    exit 0
}
if (-not (Test-Healthy $backend)) {
    Start-WslComponent 'backend'
    for ($i = 0; $i -lt 180; $i++) { if (Test-Healthy $backend) { break }; Start-Sleep -Seconds 2 }
}
if (-not (Test-Healthy $backend)) { throw "Backend did not start. See $wslRoot/runtime/backend.err.log in WSL." }
if (-not (Test-Healthy $gateway)) {
    Start-WslComponent 'gateway'
    for ($i = 0; $i -lt 30; $i++) { if (Test-Healthy $gateway) { break }; Start-Sleep -Seconds 1 }
}
if (-not (Test-Healthy $gateway)) { throw "Gateway did not start. See $wslRoot/runtime/gateway.err.log in WSL." }
if ($StartOnly) { Write-Output 'DiffusionGemma agent is ready at http://127.0.0.1:8090/v1'; exit 0 }
if (-not $Task) { throw 'Pass -Task, or use -StartOnly.' }
$wslRepo = (& wsl.exe --exec wslpath -a ([IO.Path]::GetFullPath($Repo))).Trim()
$args = @('--exec', 'env', "DG_AGENT_PYTHON=$wslRoot/.venv-runtime/bin/python", "DG_AIDER_PYTHON=$wslRoot/.venv-runtime/bin/python", "DG_HAYSTACK_PYTHON=$wslRoot/.venv-runtime/bin/python", "$wslRoot/scripts/dg_agent.sh", 'autonomous', '--', '--repo', $wslRepo, '--task', $Task, '--max-steps', [string]$MaxSteps, '--auto-test')
if ($File) { $args += @('--file', $File) }
& wsl.exe @args
exit $LASTEXITCODE
