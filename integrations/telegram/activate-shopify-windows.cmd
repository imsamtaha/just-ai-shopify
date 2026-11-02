@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup-windows.ps1 first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" configure.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" configure_shopify.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" doctor.py --live
if errorlevel 1 goto failed
".venv\Scripts\python.exe" shopify_doctor.py --live
if errorlevel 1 goto failed
".venv\Scripts\python.exe" activate.py
exit /b %errorlevel%
:failed
echo Setup or verification did not pass. No bot was started by this launcher.
pause
exit /b 1
