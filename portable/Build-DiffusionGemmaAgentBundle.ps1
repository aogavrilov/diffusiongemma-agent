[CmdletBinding()]
param(
    [string]$WslSourceRoot = '/root/diffusiongemma-agent',
    [string]$OutputDirectory = '',
    [switch]$Archive
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repo 'dist\diffusiongemma-agent-portable' }
$out = [IO.Path]::GetFullPath($OutputDirectory)
$modelName = 'diffusiongemma-26B-A4B-it-IQ3_M-from-Q4_K_M.gguf'
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'WSL2 is required to build the portable bundle.' }
if (Test-Path $out) { Remove-Item -LiteralPath $out -Recurse -Force }
New-Item -ItemType Directory -Force -Path "$out\payload\app", "$out\payload\bin", "$out\payload\models" | Out-Null

Copy-Item -Recurse -Force "$repo\scripts" "$out\payload\app\scripts"
Copy-Item -Recurse -Force "$repo\configs" "$out\payload\app\configs"
Copy-Item -Recurse -Force "$repo\docs" "$out\payload\app\docs"
Copy-Item -Force "$repo\requirements.txt" "$out\payload\app\requirements.txt"
Copy-Item -Force "$PSScriptRoot\start-runtime.sh" "$out\payload\app\start-runtime.sh"
Copy-Item -Force "$PSScriptRoot\Install-DiffusionGemmaAgent.ps1" "$out\Install-DiffusionGemmaAgent.ps1"
Copy-Item -Force "$PSScriptRoot\dg.ps1" "$out\dg.ps1"
Copy-Item -Force "$PSScriptRoot\start-runtime.sh" "$out\start-runtime.sh"
Copy-Item -Force "$PSScriptRoot\README.md" "$out\README.md"

$outWsl = (& wsl.exe --exec wslpath -a $out).Trim()
$source = $WslSourceRoot
$dest = $outWsl
$copy = @"
set -euo pipefail
cp -a '$source/server.py' '$dest/payload/app/server.py'
cp -a '$source/models/diffusiongemma/$modelName' '$dest/payload/models/$modelName'
cp -a '$source/llama.cpp-diffusion/build-gcc14-compat/bin/.' '$dest/payload/bin/'
cp -L /usr/local/cuda/targets/x86_64-linux/lib/libcudart.so.13 '$dest/payload/bin/libcudart.so.13'
cp -L /usr/local/cuda/targets/x86_64-linux/lib/libcublas.so.13 '$dest/payload/bin/libcublas.so.13'
cp -L /usr/local/cuda/targets/x86_64-linux/lib/libcublasLt.so.13 '$dest/payload/bin/libcublasLt.so.13'
while IFS= read -r -d '' link; do
  cp -L "`$link" "`$link.portable"
  rm "`$link"
  mv "`$link.portable" "`$link"
done < <(find '$dest/payload/bin' -type l -print0)
"@
& wsl.exe --exec bash -lc $copy
if ($LASTEXITCODE -ne 0) { throw 'Could not copy the working WSL runtime into the bundle.' }

$files = Get-ChildItem -LiteralPath "$out\payload" -File -Recurse | ForEach-Object {
    $isLink = [bool]($_.Attributes -band [IO.FileAttributes]::ReparsePoint)
    [ordered]@{
        path = $_.FullName.Substring($out.Length + 1).Replace('\', '/')
        bytes = $_.Length
        symlink = $isLink
        sha256 = if ($isLink) { '' } else { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    }
}
[ordered]@{ format = 1; model = $modelName; created_utc = (Get-Date).ToUniversalTime().ToString('o'); files = $files } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$out\manifest.json" -Encoding utf8

if ($Archive) {
    $archivePath = "$out.tar"
    $parent = Split-Path -Parent $out
    $name = Split-Path -Leaf $out
    & tar.exe -cf $archivePath -C $parent $name
    if ($LASTEXITCODE -ne 0) { throw 'Bundle directory was created, but tar archive creation failed.' }
    $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$archiveHash  $name.tar" | Set-Content -LiteralPath "$archivePath.sha256" -Encoding ascii
    Write-Output "Archive: $archivePath"
}
Write-Output "Portable bundle: $out"
