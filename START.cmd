@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.13 or newer from python.org, then run START.cmd again.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8787 in your browser.
echo Keep this window open while using TeamWave. Press Ctrl+C to stop.
python server.py
pause
