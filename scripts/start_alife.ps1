# Starts ALIFE in a visible terminal using the project virtual environment.
# This script does not restart or shut down Windows.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "data"
$LogFile = Join-Path $LogDir "startup.log"
$LockFile = Join-Path $LogDir "alife.lock"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

function Write-StartupLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$timestamp | $Message"
}

Write-StartupLog "start_alife.ps1 began in $ProjectRoot"

if (-not (Test-Path $Python)) {
    Write-StartupLog "ERROR: Python virtualenv not found at $Python"
    Write-Host "ALIFE cannot start: virtual environment is missing at $Python"
    Write-Host "Create it with: py -3 -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

if (Test-Path $LockFile) {
    $existingPid = (Get-Content $LockFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Write-StartupLog "ALIFE already running with PID $existingPid"
        Write-Host "ALIFE is already running (PID $existingPid)."
        exit 0
    }
}

Set-Location $ProjectRoot
Write-StartupLog "Launching python -m app.main"
& $Python -m app.main
$exitCode = $LASTEXITCODE
Write-StartupLog "ALIFE exited with code $exitCode"
exit $exitCode
