# Registers a Windows Scheduled Task that runs the scan every 6 hours.
# Run once:  powershell -ExecutionPolicy Bypass -File scripts\install_scheduler.ps1
# Re-running updates the existing task (-Force).
$ErrorActionPreference = 'Stop'
$taskName = 'QuantInternshipTracker'
$scanScript = Join-Path $PSScriptRoot 'run_scan.ps1'

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scanScript`""

# Start ~2 minutes from now, then repeat every 6 hours indefinitely.
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) `
    -RepetitionInterval (New-TimeSpan -Hours 6)

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force `
    -Description 'Scrapes quant internships every 6 hours and updates the local tracker DB + digest.' | Out-Null

Write-Host "Registered scheduled task '$taskName' (runs every 6 hours)." -ForegroundColor Green
Write-Host "Manage it in Task Scheduler, or run scripts\uninstall_scheduler.ps1 to remove it."
