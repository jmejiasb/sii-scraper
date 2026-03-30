@echo off
REM ─ Change directory to where this .bat lives ─
cd /d "%~dp0"

git pull origin main

REM ─ Run your Python script ─
python main.py

REM ─ Pause so the console stays open for the user to see any output/errors ─
echo.
echo Press any key to exit
pause >nul