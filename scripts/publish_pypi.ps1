[CmdletBinding()]
param(
    [switch]$TestPyPI,
    [switch]$BuildOnly
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$output = Join-Path $repo 'dist\python'

function Test-WindowsTwine {
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'SilentlyContinue'
        python -c "import nh3, twine" *> $null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

function Get-WslTwinePython {
    $candidates = @(
        '/root/diffusiongemma-agent/.venv-aider/bin/python',
        '/usr/bin/python3'
    )
    foreach ($candidate in $candidates) {
        & wsl.exe --exec $candidate -m twine --version *> $null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}

function Convert-ToWslPath([string]$Path) {
    $converted = & wsl.exe --exec wslpath -a $Path
    if ($LASTEXITCODE -ne 0) { throw "Could not convert path for WSL: $Path" }
    return $converted.Trim()
}

function Invoke-TwineCheck([System.IO.FileInfo[]]$Artifacts) {
    if (Test-WindowsTwine) {
        python -m twine check @($Artifacts.FullName)
        if ($LASTEXITCODE -eq 0) { return }
    }

    $wslPython = Get-WslTwinePython
    if (-not $wslPython) {
        throw 'Twine validation failed and no WSL Python with twine is available.'
    }
    $wslArtifacts = @($Artifacts | ForEach-Object { Convert-ToWslPath $_.FullName })
    & wsl.exe --exec $wslPython -m twine check @wslArtifacts
    if ($LASTEXITCODE -ne 0) { throw 'Twine package validation failed.' }
}

function Invoke-TwineUpload([System.IO.FileInfo[]]$Artifacts, [string]$Repository) {
    if (Test-WindowsTwine) {
        $oldUsername = $env:TWINE_USERNAME
        try {
            $env:TWINE_USERNAME = '__token__'
            python -m twine upload --repository $Repository @($Artifacts.FullName)
            if ($LASTEXITCODE -eq 0) { return }
        } finally {
            $env:TWINE_USERNAME = $oldUsername
        }
    }

    $wslPython = Get-WslTwinePython
    if (-not $wslPython) { throw 'Twine upload failed and no WSL fallback is available.' }
    $wslArtifacts = @($Artifacts | ForEach-Object { Convert-ToWslPath $_.FullName })
    $oldWslEnv = $env:WSLENV
    $oldUsername = $env:TWINE_USERNAME
    try {
        $env:TWINE_USERNAME = '__token__'
        $forward = 'TWINE_USERNAME:TWINE_PASSWORD'
        $env:WSLENV = if ($oldWslEnv) { "$oldWslEnv`:$forward" } else { $forward }
        & wsl.exe --exec $wslPython -m twine upload --repository $Repository @wslArtifacts
        if ($LASTEXITCODE -ne 0) { throw 'Twine upload failed.' }
    } finally {
        $env:WSLENV = $oldWslEnv
        $env:TWINE_USERNAME = $oldUsername
    }
}

python -m pip install --disable-pip-version-check 'build>=1.2' 'twine>=6'
if ($LASTEXITCODE -ne 0) { throw 'Could not install build tools.' }
New-Item -ItemType Directory -Force -Path $output | Out-Null
Get-ChildItem $output -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq '.whl' -or $_.Name -like '*.tar.gz' } |
    Remove-Item -Force
python -m build --outdir $output $repo
if ($LASTEXITCODE -ne 0) { throw 'Python package build failed.' }
$artifacts = @(Get-ChildItem $output -File | Where-Object { $_.Extension -in '.whl', '.gz' })
if ($artifacts.Count -ne 2) { throw "Expected wheel and sdist in $output." }
Invoke-TwineCheck $artifacts
$checksums = $artifacts | Sort-Object Name | ForEach-Object {
    "$((Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant())  $($_.Name)"
}
$checksums | Set-Content -LiteralPath (Join-Path $output 'SHA256SUMS.txt') -Encoding ascii
if ($BuildOnly) { Write-Output "Built package: $output"; exit 0 }
if (-not $env:TWINE_PASSWORD) { throw 'TWINE_PASSWORD must contain a PyPI API token.' }
$repository = if ($TestPyPI) { 'testpypi' } else { 'pypi' }
Invoke-TwineUpload $artifacts $repository
exit 0
