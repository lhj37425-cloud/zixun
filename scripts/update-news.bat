@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ========================================
echo  Daily Dissect - news line only
echo ========================================
echo.

where uv >nul 2>&1
if errorlevel 1 (
  echo uv not found. Install uv first: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

uv run dd update --only news --open
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
  echo Update failed, exit %ERR%.
) else (
  echo Done.
)
echo.
pause
exit /b %ERR%
