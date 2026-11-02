@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

if not exist "package.json" goto missing_project
where npm.cmd >nul 2>&1
if errorlevel 1 goto missing_npm
if /i "%~1"=="--check" goto check
if not "%~1"=="" goto usage

echo Starting JUST AI Shopify from "%CD%"
if not exist "node_modules\.bin\shopify.cmd" (
  call npm.cmd ci
  if errorlevel 1 goto failed
)
if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  if errorlevel 1 goto failed
)

call npm.cmd run setup
if errorlevel 1 goto failed
call npm.cmd run config:link
if errorlevel 1 goto failed
call npm.cmd run dev
if errorlevel 1 goto failed
popd
exit /b 0

:check
echo Project directory: "%CD%"
call npm.cmd prefix
if errorlevel 1 goto failed
popd
exit /b 0

:missing_project
echo ERROR: Keep Start-Shopify.cmd in the repository beside package.json.
popd
exit /b 1

:missing_npm
echo ERROR: Install Node.js and npm, then reopen PowerShell.
popd
exit /b 1

:usage
echo Usage: Start-Shopify.cmd [--check]
echo --check verifies the project folder without starting Shopify or changing files.
popd
exit /b 1

:failed
set "shopify_launch_exit=%errorlevel%"
echo.
echo ERROR: The command above failed. The launcher has stopped.
popd
exit /b %shopify_launch_exit%
