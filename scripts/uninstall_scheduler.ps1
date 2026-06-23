# Removes the scheduled scan task.
#   powershell -ExecutionPolicy Bypass -File scripts\uninstall_scheduler.ps1
$ErrorActionPreference = 'Stop'
$taskName = 'QuantInternshipTracker'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled task '$taskName'." -ForegroundColor Yellow
} else {
    Write-Host "No scheduled task named '$taskName' found."
}
