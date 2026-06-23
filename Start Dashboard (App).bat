@echo off
REM Launches the dashboard as a native desktop window (no web browser).
cd /d "%~dp0"

REM Prefer the windowless launcher so no console window lingers.
set "PYW=pyw"
where pyw >nul 2>nul || set "PYW=pythonw"

start "" "%PYW%" "%~dp0desktop.py"
