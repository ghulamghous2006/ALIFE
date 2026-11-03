# Manually verifies the ALIFE startup script without restarting Windows.

$ErrorActionPreference = "Stop"
$StartScript = Join-Path $PSScriptRoot "start_alife.ps1"
Write-Host "Launching ALIFE via $StartScript"
powershell -ExecutionPolicy Bypass -File $StartScript
