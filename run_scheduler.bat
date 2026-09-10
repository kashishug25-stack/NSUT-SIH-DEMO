@echo off
setlocal

REM Skylytics - run one complete 3-source scrape.
REM This file is portable: it always runs from the project root.

cd /d "%~dp0"

if not exist "logs" mkdir "logs"

echo ================================================== >> "logs\scheduler.log"
echo Skylytics scrape started: %date% %time% >> "logs\scheduler.log"
echo ================================================== >> "logs\scheduler.log"

py -3 run_all.py --source all --headed >> "logs\scheduler.log" 2>&1

set "EXIT_CODE=%ERRORLEVEL%"
echo Skylytics scrape finished: %date% %time% ^(exit code %EXIT_CODE%^) >> "logs\scheduler.log"
echo. >> "logs\scheduler.log"

exit /b %EXIT_CODE%
