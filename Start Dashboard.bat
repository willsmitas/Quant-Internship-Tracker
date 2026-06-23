@echo off
title Quant Internship Tracker
cd /d "%~dp0"

REM Resolve the Python launcher (prefer the py launcher, fall back to python).
set "PY=py"
where py >nul 2>nul || set "PY=python"

echo ============================================================
echo   Quant Internship Tracker
echo   Starting the dashboard at http://127.0.0.1:5050
echo   Your browser will open automatically in a few seconds.
echo.
echo   Keep this window OPEN while using the dashboard.
echo   Close it (or press Ctrl+C) to stop the server.
echo ============================================================
echo.

REM Open the browser a few seconds after the server has had time to start.
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:5050'"

REM Run the dashboard (this blocks and keeps the window open until you stop it).
%PY% "%~dp0dashboard\app.py"

echo.
echo Dashboard stopped.
pause
