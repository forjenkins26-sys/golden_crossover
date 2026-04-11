@echo off
REM ASCII launcher for RSI Hybrid Bot
REM Sets UTF-8 encoding for proper emoji/character display

chcp 65001 > nul
set PYTHONIOENCODING=utf-8
python rsi_hybrid_bot.py
pause
