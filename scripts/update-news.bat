@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ========================================
echo  今日一拆 · 只重跑资讯线
echo ========================================
echo.

where uv >nul 2>&1
if errorlevel 1 (
  echo 找不到 uv。请先安装 uv，并确保能在命令行里运行。
  pause
  exit /b 1
)

uv run dd update --only news --open
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
  echo 更新过程中有错误，退出码 %ERR%。请向上翻看具体原因。
) else (
  echo 全部完成。
)
echo.
pause
exit /b %ERR%
