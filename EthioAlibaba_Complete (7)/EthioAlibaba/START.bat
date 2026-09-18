@echo off
chcp 65001 >nul
title EthioAlibaba Server
echo ========================================
echo   EthioAlibaba Website Starting...
echo ========================================
echo.
echo   Homepage:  http://127.0.0.1:5000
echo   Register:  http://127.0.0.1:5000/register
echo.
echo   To stop: press Ctrl+C
echo ========================================
echo.

cd /d "%~dp0"

python app.py
if errorlevel 1 (
    py app.py
)

pause
