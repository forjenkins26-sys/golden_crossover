@echo off
REM START_BOT.BAT - Launch RSI Hybrid Bot
REM Double-click to start the bot automatically

REM Set UTF-8 encoding for proper emoji/character display
chcp 65001 >nul

REM Navigate to the bot directory
cd /d "d:\golden_crossover"

REM Set Python encoding to UTF-8
set PYTHONIOENCODING=utf-8

REM Start the bot with Python
python rsi_hybrid_bot.py

REM Keep window open if bot crashes
pause
