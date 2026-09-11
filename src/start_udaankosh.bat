@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo UDAANKOSH - Indian Airfare Price Intelligence
echo ================================================
python -c "import sqlite3; c=sqlite3.connect('data\airfare_intelligence.db'); print('Database quotes:', c.execute('SELECT COUNT(*) FROM raw_fare_quotes').fetchone()[0]); print('Scrape runs:', c.execute('SELECT COUNT(*) FROM scrape_runs').fetchone()[0]); c.close()"
echo.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr LISTENING ^| findstr :8000') do taskkill /PID %%P /F >nul 2>&1
 echo Starting current UDAANKOSH API at http://127.0.0.1:8000/
start "UDAANKOSH API" cmd /k "cd /d %~dp0 && python api_server.py"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000/?v=20260910-final
endlocal
