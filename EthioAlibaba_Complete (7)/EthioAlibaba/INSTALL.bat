@echo off
chcp 65001 >nul
title EthioAlibaba - Install
echo ========================================
echo   EthioAlibaba - Package Install
echo ========================================
echo.

cd /d "%~dp0"

echo Installing Python packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Trying with py command...
    py -m pip install -r requirements.txt
)

echo.
echo ========================================
echo   Done! Now double-click START.bat
echo ========================================
pause
