@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist "logs" mkdir "logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%I"
set "LOG=logs\daily-%TODAY%.log"

>> "%LOG%" echo ===== %DATE% %TIME% start =====

set "UV="
where uv >nul 2>&1
if not errorlevel 1 for /f "delims=" %%I in ('where uv') do if not defined UV set "UV=%%I"
if not defined UV if exist "%LOCALAPPDATA%\hermes\bin\uv.exe" set "UV=%LOCALAPPDATA%\hermes\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV=%USERPROFILE%\.cargo\bin\uv.exe"

if not defined UV (
  >> "%LOG%" echo ERROR: uv not found
  >> "%LOG%" echo ===== end exit 1 =====
  exit /b 1
)

>> "%LOG%" echo using uv: %UV%
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"%UV%" run dd update >> "%LOG%" 2>&1
set "ERR=%ERRORLEVEL%"
>> "%LOG%" echo ===== end exit %ERR% =====
exit /b %ERR%
