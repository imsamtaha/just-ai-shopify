@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Install the Windows bot environment first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -B meta_server.py
if errorlevel 1 pause
