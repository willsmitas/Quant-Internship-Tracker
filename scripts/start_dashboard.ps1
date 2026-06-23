# Starts the local dashboard web app, then open the printed URL in your browser.
#   powershell -ExecutionPolicy Bypass -File scripts\start_dashboard.ps1
$ErrorActionPreference = 'Continue'
$proj = Split-Path -Parent $PSScriptRoot

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error 'Python not found on PATH (need py or python).'; exit 1 }

& $py (Join-Path $proj 'dashboard\app.py')
