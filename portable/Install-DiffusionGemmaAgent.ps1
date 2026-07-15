[CmdletBinding()]
param(
    [string]$WslRoot = '',
    [switch]$NoStart,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$bundle = Split-Path -Parent $PSCommandPath
$model = 'diffusiongemma-26B-A4B-it-IQ3_M-from-Q4_K_M.gguf'
foreach ($required in @("$bundle\payload\app\server.py", "$bundle\payload\bin\llama-diffusion-gemma-visual-server", "$bundle\payload\models\$model", "$bundle\manifest.json")) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Incomplete portable bundle: $required is missing." }
}
$manifest = Get-Content -LiteralPath "$bundle\manifest.json" -Raw | ConvertFrom-Json
$modelEntry = $manifest.files | Where-Object path -eq "payload/models/$model" | Select-Object -First 1
if (-not $modelEntry -or [int64]$modelEntry.bytes -ne (Get-Item -LiteralPath "$bundle\payload\models\$model").Length) {
    throw 'The bundled GGUF size does not match manifest.json.'
}
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'WSL2 is required. Run wsl --install, reboot if requested, then run this command again.' }
& wsl.exe --exec true
if ($LASTEXITCODE -ne 0) { throw 'A default WSL distribution must be initialized once before installation.' }
$bundleWsl = (& wsl.exe --exec wslpath -a $bundle).Trim()
if (-not $bundleWsl) { throw 'Could not translate the bundle path for WSL.' }
if (-not $WslRoot) { $WslRoot = '~/.local/share/diffusiongemma-agent' }
$WslRoot = (& wsl.exe --exec python3 -c 'import os,sys; print(os.path.abspath(os.path.expandvars(os.path.expanduser(sys.argv[1]))))' $WslRoot).Trim()
if (-not $WslRoot.StartsWith('/') -or $WslRoot -in @('/', '/root', '/home', '/usr', '/var')) {
    throw "Unsafe WSL installation path: $WslRoot"
}
if ($WslRoot.Contains("'")) { throw "WslRoot cannot contain an apostrophe." }

$runtimeBin = "$bundleWsl/payload/bin"
$ldd = & wsl.exe --exec env "LD_LIBRARY_PATH=$runtimeBin" ldd "$runtimeBin/llama-diffusion-gemma-visual-server" 2>&1
if ($LASTEXITCODE -ne 0 -or ($ldd -join "`n") -match 'not found') { throw "Portable CUDA runtime check failed:`n$($ldd -join "`n")" }
if ($VerifyOnly) { Write-Output 'Portable bundle verification passed.'; exit 0 }

& wsl.exe --exec bash -lc 'python3 -m venv /tmp/dg-venv-check && rm -rf /tmp/dg-venv-check' 2>$null
if ($LASTEXITCODE -ne 0) {
    & wsl.exe -u root --exec bash -lc 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip libgomp1 libstdc++6'
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the minimal Ubuntu Python runtime.' }
}

$quotedBundle = $bundleWsl
$quotedRoot = $WslRoot
$setup = @"
set -euo pipefail
mkdir -p '$quotedRoot'
cp -a '$quotedBundle/payload/app/.' '$quotedRoot/'
mkdir -p '$quotedRoot/runtime/bin' '$quotedRoot/models/diffusiongemma'
cp -a '$quotedBundle/payload/bin/.' '$quotedRoot/runtime/bin/'
cp -a '$quotedBundle/payload/models/.' '$quotedRoot/models/diffusiongemma/'
python3 -m venv '$quotedRoot/.venv-runtime'
'$quotedRoot/.venv-runtime/bin/python' -m pip install --upgrade pip
'$quotedRoot/.venv-runtime/bin/python' -m pip install 'fastapi>=0.111,<1' 'uvicorn[standard]>=0.30,<1' 'pydantic>=2,<3' 'aider-chat>=0.86,<1' 'haystack-ai>=2.31,<3'
chmod +x '$quotedRoot/runtime/bin/'* '$quotedRoot/scripts/'*.sh '$quotedRoot/start-runtime.sh'
"@
& wsl.exe --exec bash -lc $setup
if ($LASTEXITCODE -ne 0) { throw 'WSL runtime installation failed.' }

[ordered]@{ format = 1; runtime_version = '0.1.1'; bundle = $bundle; wsl_root = $WslRoot; model = $model; installed_at = (Get-Date).ToUniversalTime().ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath "$bundle\installed.json" -Encoding utf8
if (-not $NoStart) { & "$bundle\dg.ps1" -StartOnly }
Write-Output "Installed. Use: & '$bundle\dg.ps1' -Repo C:\path\to\repo -Task 'fix ... and run tests'"
