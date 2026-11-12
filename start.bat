@echo off
title SocialPulse

cd /d "%~dp0"

echo =============================================
echo         SocialPulse Telegram Bot
echo =============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python venv tidak ditemukan!
    pause
    exit /b 1
)

echo [INFO] Menggunakan Python dari venv...
".venv\Scripts\python.exe" --version

echo.
echo [INFO] Menjalankan bot...
echo.

".venv\Scripts\python.exe" bot.py

echo.
echo ========================================
echo Bot berhenti atau mengalami error.
echo ========================================
pause