# Registers an idempotent Windows logon task that starts ALIFE in a visible window.
# Does not require administrator privileges for the current user.

$ErrorActionPreference = "Stop"

$TaskName = "ALIFE Auto Start"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StartScript = Join-Path $PSScriptRoot "start_alife.ps1"

if (-not (Test-Path $StartScript)) {
    throw "Missing startup script: $StartScript"
}

$argument = "-NoExit -ExecutionPolicy Bypass -File `"$StartScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null

Write-Host "Registered Windows startup task: $TaskName"
Write-Host "ALIFE will open a visible PowerShell window when you sign in."
Write-Host "Disable later with: powershell -File `"$PSScriptRoot\disable_startup.ps1`""
