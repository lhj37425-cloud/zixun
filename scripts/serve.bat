@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ========================================
echo  Daily Dissect - local server
echo ========================================
echo.
echo Keep this window open. Use the "抓取这一天"
echo button in the page. Close this window (or
echo press Ctrl+C) to stop the server.
echo.

where uv >nul 2>&1
if errorlevel 1 (
  echo uv not found. Install uv first: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

uv run dd serve --open
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
  echo Server failed, exit %ERR%.
) else (
  echo Server stopped.
)
echo.
pause
exit /b %ERR%
