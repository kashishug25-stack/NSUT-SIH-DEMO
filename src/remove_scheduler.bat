@echo off
setlocal
set "TASK_NAME=Skylytics Scraper - Every 6 Hours"
schtasks /Delete /TN "%TASK_NAME%" /F
if errorlevel 1 (
    echo.
    echo [INFO] The Skylytics scheduled task was not found or could not be removed.
    exit /b 1
)
echo.
echo [SUCCESS] Skylytics 6-hour automation removed.
echo.
exit /b 0
