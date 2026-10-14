@echo off
REM ─ Change directory to where this .bat lives ─
cd /d "%~dp0"

git pull origin main

REM ─ Get previous month (zero-padded) and its year ─
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddMonths(-1).ToString('MM')"') do set PREV_MONTH=%%i
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddMonths(-1).ToString('yyyy')"') do set PREV_YEAR=%%i

echo Running for %PREV_YEAR%-%PREV_MONTH%

REM ─ Run your Python script ─
python main.py --month "%PREV_MONTH%" --year "%PREV_YEAR%"

REM ─ Pause so the console stays open for the user to see any output/errors ─
echo.
echo Press any key to exit
pause >nul