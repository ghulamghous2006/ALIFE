# Removes the ALIFE logon startup task if it exists.

$ErrorActionPreference = "Stop"
$TaskName = "ALIFE Auto Start"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $existing) {
    Write-Host "No ALIFE startup task is currently registered."
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed Windows startup task: $TaskName"
