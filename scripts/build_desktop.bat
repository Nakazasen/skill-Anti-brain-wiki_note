@echo off
setlocal

cd /d "%~dp0.."

echo Cleaning old builds...
if exist build rd /s /q build
if exist dist rd /s /q dist

echo Building ABW Desktop Admin...
echo This will create a single-folder distribution in dist/ABW-Admin-v1.0.1

py -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "ABW-Admin-v1.0.1" ^
    --paths "src" ^
    --add-data "ui/main.py;ui" ^
    --add-data "ui/release_support.py;ui" ^
    --collect-all "abw" ^
    --hidden-import "abw.api" ^
    --hidden-import "uvicorn" ^
    --hidden-import "fastapi" ^
    --hidden-import "starlette" ^
    --hidden-import "requests" ^
    "ui/run_abw_desktop.py"

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    exit /b %ERRORLEVEL%
)

echo.
echo Build successful! 
echo Executable is at: dist\ABW-Admin-v1.0.1\ABW-Admin-v1.0.1.exe
echo Note: Ensure your environment has all dependencies installed before running this script.
pause
