@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo Installing DailyDissect scheduled task...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-daily-task.ps1"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (echo Install failed, exit %ERR%.) else (echo Install done. Task name: DailyDissect)
echo.
pause
exit /b %ERR%
