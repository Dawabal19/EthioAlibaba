@echo off
chcp 65001 >nul
title EthioAlibaba Telegram Bot
echo ========================================
echo   EthioAlibaba Telegram Bot Starting...
echo ========================================
echo.
echo   Commands in Telegram:
echo   /start
echo   /orders
echo   /track ETHXXXX
echo   /status ETHXXXX NewStatus
echo.
echo   To stop: press Ctrl+C
echo ========================================
echo.

cd /d "%~dp0"

python bot_polling.py
if errorlevel 1 (
    py bot_polling.py
)

pause
