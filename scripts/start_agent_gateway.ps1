[CmdletBinding()]
param(
    [int]$Port = 8090,
    [string]$BackendBase = 'http://127.0.0.1:4100/v1',
    [string]$BackendModel = 'diffusiongemma-26b-a4b-it-iq3m-fullgpu'
)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($root -notmatch '^[A-Za-z]:\\') {
    throw "The gateway launcher requires a drive-rooted Windows path, got: $root"
}
$drive = $root.Substring(0, 1).ToLowerInvariant()
$wslRoot = '/mnt/' + $drive + '/' + $root.Substring(3).Replace('\', '/')
$healthUrl = "http://127.0.0.1:$Port/healthz"

try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
    if ($health.ok) {
        Write-Output "DG agent gateway is already healthy at $healthUrl"
        exit 0
    }
} catch {
    # The port is free or contains an unhealthy process; start the gateway below.
}

$logDir = Join-Path $root 'runlogs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$script = "cd '$wslRoot' && DG_AIDER_PROXY_PORT=$Port DG_AIDER_BACKEND_BASE='$BackendBase' DG_AIDER_BACKEND_MODEL='$BackendModel' exec ./scripts/run_agent_gateway_wsl.sh"
$arguments = "--exec bash -lc `"$script`""
$process = Start-Process -FilePath wsl.exe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'agent_gateway_wsl.out.log') -RedirectStandardError (Join-Path $logDir 'agent_gateway_wsl.err.log') -PassThru

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health.ok) {
            $process.Id | Set-Content -NoNewline (Join-Path $logDir 'agent_gateway_wsl.pid')
            Write-Output "DG agent gateway is healthy at $healthUrl (PID $($process.Id))"
            exit 0
        }
    } catch {
        if ($process.HasExited) {
            break
        }
    }
}

throw "DG agent gateway failed to become healthy. See $logDir\\agent_gateway_wsl.err.log"
