$ErrorActionPreference = "Stop"
$forward = @("-Compact") + @($args)
& (Join-Path $PSScriptRoot "run_opencode_windows.ps1") @forward
exit $LASTEXITCODE
