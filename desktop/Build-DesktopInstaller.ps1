[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repo 'dist\desktop' }
$output = [IO.Path]::GetFullPath($OutputDirectory)
$appDist = Join-Path $repo 'build\desktop'
$work = Join-Path $repo 'build\pyinstaller'
$spec = Join-Path $PSScriptRoot 'diffusiongemma_agent.spec'
$setup = Join-Path $output 'DiffusionGemmaAgentSetup-0.1.4.exe'
$makensis = @(
    'C:\Program Files (x86)\NSIS\makensis.exe',
    'C:\Program Files\NSIS\makensis.exe'
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $makensis) { throw 'NSIS 3 is required to build Setup.exe.' }

& $Python -m pip install --disable-pip-version-check 'pyinstaller>=6.15,<7'
if ($LASTEXITCODE -ne 0) { throw 'Could not install PyInstaller.' }

New-Item -ItemType Directory -Force -Path $output | Out-Null
Remove-Item -LiteralPath $appDist -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $setup -Force -ErrorAction SilentlyContinue

& $Python -m PyInstaller --noconfirm --clean --distpath $appDist --workpath $work $spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

$app = Join-Path $appDist 'DiffusionGemmaAgent\DiffusionGemmaAgent.exe'
$core = Join-Path $appDist 'DiffusionGemmaAgent\dg-agent-core.exe'
if (-not (Test-Path -LiteralPath $app) -or -not (Test-Path -LiteralPath $core)) {
    throw 'The standalone application is incomplete.'
}
& $app --smoke-test
if ($LASTEXITCODE -ne 0) { throw 'Standalone GUI smoke test failed.' }
& $core --version
if ($LASTEXITCODE -ne 0) { throw 'Standalone CLI smoke test failed.' }

& $makensis "/DAPP_SOURCE=$(Split-Path -Parent $app)" "/DOUTPUT_FILE=$setup" "/DREPO_ROOT=$repo" (Join-Path $PSScriptRoot 'installer.nsi')
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $setup)) { throw 'NSIS installer build failed.' }

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash.ToLowerInvariant()
"$hash  $([IO.Path]::GetFileName($setup))" | Set-Content -LiteralPath (Join-Path $output 'SHA256SUMS.txt') -Encoding ascii
[ordered]@{
    status = 'ready'
    setup = $setup
    bytes = (Get-Item -LiteralPath $setup).Length
    sha256 = $hash
    app = $app
    core = $core
} | ConvertTo-Json
