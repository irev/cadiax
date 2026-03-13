@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "POWERSHELL_EXE=powershell"

where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
    set "POWERSHELL_EXE=pwsh"
)

%POWERSHELL_EXE% -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [Cadiax] install.bat failed with exit code %EXIT_CODE%.
)

exit /b %EXIT_CODE%
