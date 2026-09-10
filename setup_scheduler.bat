@echo off
setlocal

REM Skylytics - install/update the Windows Task Scheduler job.
REM Runs the full 3-source scraper every 6 hours.
REM Headed browser scraping requires the Windows user to be logged in.

cd /d "%~dp0"

set "TASK_NAME=Skylytics Scraper - Every 6 Hours"
set "SCRIPT=%~dp0run_scheduler.bat"

echo.
echo ================================================
echo   Skylytics Scheduler Setup
echo ================================================
echo.
echo Installing: %TASK_NAME%
echo.

schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
schtasks /Create /TN "%TASK_NAME%" /TR "%ComSpec% /c ""%SCRIPT%""" /SC HOURLY /MO 6 /IT /F

if errorlevel 1 (
    echo.
    echo [ERROR] Could not create the scheduled task.
    echo Try right-clicking this BAT and choosing "Run as administrator".
    echo.
    exit /b 1
)

echo.
echo [SUCCESS] Skylytics is now scheduled every 6 hours.
echo.
echo The scraper runs independently of the frontend.
echo Windows must have the user logged in because the scrapers use headed Chrome.
echo.
exit /b 0
