[CmdletBinding()]
param(
    [string]$WslRoot = '',
    [switch]$NoStart,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$bundle = Split-Path -Parent $PSCommandPath
$model = 'diffusiongemma-26B-A4B-it-IQ3_M-from-Q4_K_M.gguf'
$pythonArchive = "$bundle\payload\python\cpython-3.12.13.tar.gz"
foreach ($required in @("$bundle\payload\app\server.py", "$bundle\payload\bin\llama-diffusion-gemma-visual-server", "$bundle\payload\models\$model", $pythonArchive, "$bundle\manifest.json")) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Incomplete portable bundle: $required is missing." }
}
$manifest = Get-Content -LiteralPath "$bundle\manifest.json" -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -LiteralPath "$bundle\manifest.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$modelEntry = $manifest.files | Where-Object path -eq "payload/models/$model" | Select-Object -First 1
if (-not $modelEntry -or [int64]$modelEntry.bytes -ne (Get-Item -LiteralPath "$bundle\payload\models\$model").Length) {
    throw 'The bundled GGUF size does not match manifest.json.'
}
$modelBytes = [int64]$modelEntry.bytes
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

$quotedBundle = $bundleWsl
$quotedRoot = $WslRoot
$setup = @"
set -euo pipefail
mkdir -p '$quotedRoot/runtime/bin' '$quotedRoot/models/diffusiongemma'
if ! grep -Fqx '$manifestHash' '$quotedRoot/runtime/installed-manifest.sha256' 2>/dev/null; then
  cp -a '$quotedBundle/payload/app/.' '$quotedRoot/'
  cp -a '$quotedBundle/payload/bin/.' '$quotedRoot/runtime/bin/'
  if [ ! -f '$quotedRoot/models/diffusiongemma/$model' ] || [ `$(stat -c %s '$quotedRoot/models/diffusiongemma/$model') -ne $modelBytes ]; then
    cp -a '$quotedBundle/payload/models/.' '$quotedRoot/models/diffusiongemma/'
  fi
fi
if [ ! -x '$quotedRoot/python/bin/python3.12' ] || \
   ! '$quotedRoot/python/bin/python3.12' -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)' >/dev/null 2>&1; then
  rm -rf '$quotedRoot/python'
  mkdir -p '$quotedRoot/python'
  tar -xzf '$quotedBundle/payload/python/cpython-3.12.13.tar.gz' -C '$quotedRoot/python'
fi
'$quotedRoot/python/bin/python3.12' -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)' || exit 43
if [ ! -x '$quotedRoot/.venv-runtime/bin/python' ] || \
   ! '$quotedRoot/.venv-runtime/bin/python' -c 'import aider, fastapi, haystack, pydantic, uvicorn' >/dev/null 2>&1; then
  if ! timeout 15 bash -c 'cat < /dev/null > /dev/tcp/pypi.org/443'; then
    exit 42
  fi
  rm -rf '$quotedRoot/.venv-runtime'
  '$quotedRoot/python/bin/python3.12' -m venv '$quotedRoot/.venv-runtime'
  '$quotedRoot/.venv-runtime/bin/python' -m pip install --disable-pip-version-check --upgrade 'pip==25.0.1'
  '$quotedRoot/.venv-runtime/bin/python' -m pip install --disable-pip-version-check --prefer-binary \
    'aider-chat==0.86.2' \
    'fastapi==0.128.8' \
    'haystack-ai==2.31.0' \
    'pydantic==2.12.5' \
    'uvicorn[standard]==0.51.0'
fi
chmod +x '$quotedRoot/runtime/bin/'* '$quotedRoot/scripts/'*.sh '$quotedRoot/start-runtime.sh'
printf '%s\n' '$manifestHash' > '$quotedRoot/runtime/installed-manifest.sha256'
"@
& wsl.exe --exec bash -lc $setup
if ($LASTEXITCODE -eq 42) { throw 'WSL cannot reach PyPI. Pause or reconfigure the VPN/proxy for WSL, then retry; the downloaded model files will be reused.' }
if ($LASTEXITCODE -eq 43) { throw 'The bundled Python runtime is incompatible. Download the current runtime bundle and retry.' }
if ($LASTEXITCODE -ne 0) { throw "WSL runtime installation failed (exit $LASTEXITCODE). The downloaded model files were kept and will be reused." }

[ordered]@{ format = 1; runtime_version = '0.1.2'; bundle = $bundle; wsl_root = $WslRoot; model = $model; installed_at = (Get-Date).ToUniversalTime().ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath "$bundle\installed.json" -Encoding utf8
if (-not $NoStart) { & "$bundle\dg.ps1" -StartOnly }
Write-Output "Installed. Use: & '$bundle\dg.ps1' -Repo C:\path\to\repo -Task 'fix ... and run tests'"
