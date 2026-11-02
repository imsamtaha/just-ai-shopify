$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$botPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $botPython)) {
    Write-Error 'Run setup-windows.ps1 first.'
    exit 1
}
& $botPython bot.py
exit $LASTEXITCODE
