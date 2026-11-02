@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Run setup-windows.ps1 first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" activate.py %*
set "activation_result=%errorlevel%"
if not "%activation_result%"=="0" pause
exit /b %activation_result%
