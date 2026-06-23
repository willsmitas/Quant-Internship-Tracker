# Runs one scan cycle. This is what Windows Task Scheduler invokes every 6 hours.
# Safe to run by hand any time:  powershell -ExecutionPolicy Bypass -File scripts\run_scan.ps1
$ErrorActionPreference = 'Continue'
$proj = Split-Path -Parent $PSScriptRoot   # scripts\.. = project root

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error 'Python not found on PATH (need py or python).'; exit 1 }

& $py (Join-Path $proj 'src\run.py')
exit $LASTEXITCODE
