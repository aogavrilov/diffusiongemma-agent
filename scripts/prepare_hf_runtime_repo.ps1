[CmdletBinding()]
param(
    [string]$Source = '',
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Source) { $Source = Join-Path $repo 'dist\diffusiongemma-agent-portable' }
if (-not $Output) { $Output = Join-Path $repo 'dist\hf-runtime-repo' }
$sourcePath = (Resolve-Path $Source).Path
$outputPath = [IO.Path]::GetFullPath($Output)
$distRoot = [IO.Path]::GetFullPath((Join-Path $repo 'dist'))
if (-not $outputPath.StartsWith($distRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Output must stay under $distRoot"
}
if (Test-Path -LiteralPath $outputPath) {
    Remove-Item -LiteralPath $outputPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

Get-ChildItem -LiteralPath $sourcePath -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($sourcePath.Length + 1)
    $destination = Join-Path $outputPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    try {
        New-Item -ItemType HardLink -Path $destination -Target $_.FullName -ErrorAction Stop | Out-Null
    } catch {
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
    }
}

Copy-Item -LiteralPath (Join-Path $repo 'packaging\hf\README.md') -Destination (Join-Path $outputPath 'README.md') -Force
Copy-Item -LiteralPath (Join-Path $repo 'packaging\hf\runtime-index.json') -Destination (Join-Path $outputPath 'runtime-index.json') -Force
$licenses = Join-Path $outputPath 'LICENSES'
New-Item -ItemType Directory -Force -Path $licenses | Out-Null
Get-ChildItem -LiteralPath (Join-Path $repo 'packaging\hf\LICENSES') -File |
    Copy-Item -Destination $licenses -Force
Copy-Item -LiteralPath (Join-Path $repo 'LICENSE') -Destination (Join-Path $licenses 'APACHE-2.0.txt') -Force
$cudaEula = Join-Path $repo 'packaging\hf\LICENSES\NVIDIA-CUDA-EULA.txt'
if (-not (Test-Path -LiteralPath $cudaEula)) { throw "CUDA EULA is missing: $cudaEula" }

$pythonSource = Join-Path $repo 'dist\python'
$pythonArtifacts = @(Get-ChildItem -LiteralPath $pythonSource -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq '.whl' -or $_.Name -like '*.tar.gz' -or $_.Name -eq 'SHA256SUMS.txt' })
if ($pythonArtifacts.Count -lt 3) {
    throw 'Python release artifacts are missing. Run scripts\publish_pypi.ps1 -BuildOnly first.'
}
$pythonTarget = Join-Path $outputPath 'python'
New-Item -ItemType Directory -Force -Path $pythonTarget | Out-Null
$pythonArtifacts | Copy-Item -Destination $pythonTarget -Force

$manifest = Get-Content -LiteralPath (Join-Path $outputPath 'manifest.json') -Raw | ConvertFrom-Json
$model = Join-Path $outputPath "payload\models\$($manifest.model)"
if (-not (Test-Path -LiteralPath $model)) { throw "Model is missing from staging: $model" }
[ordered]@{
    status = 'ready'
    output = $outputPath
    files = @(Get-ChildItem -LiteralPath $outputPath -Recurse -File).Count
    bytes = (Get-ChildItem -LiteralPath $outputPath -Recurse -File | Measure-Object Length -Sum).Sum
    model = $manifest.model
} | ConvertTo-Json
