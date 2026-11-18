@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo Uninstalling DailyDissect scheduled task...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-daily-task.ps1"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (echo Uninstall failed, exit %ERR%.) else (echo Done.)
echo.
pause
exit /b %ERR%
