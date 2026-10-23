@echo off
setlocal

set "REPO_DIR=%~dp0.."
cd /d "%REPO_DIR%"

echo.
echo ================================================
echo  TradingView Codex Mode
echo ================================================
echo.
echo This launcher starts TradingView Desktop with the
echo debug/CDP port required by Codex.
echo.

npm.cmd run tv -- launch --kill_existing true
if errorlevel 1 (
    echo.
    echo Launch failed. Press any key to close.
    pause >nul
    exit /b 1
)

echo.
echo Checking connection...
npm.cmd run doctor

echo.
echo If doctor shows ready=true, Codex can read TradingView.
echo You may keep this window open while trading.
echo.
pause
