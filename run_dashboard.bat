@echo off
REM Start the DFX web dashboard, then open http://localhost:5000
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo The virtual environment is missing. Run setup.bat first.
    pause >nul
    exit /b 1
)

echo Starting the DFX dashboard on http://localhost:5000
echo Press Ctrl+C in this window to stop the server.
echo.
".venv\Scripts\python.exe" "web_dashboard\app.py"

echo.
echo Server stopped. Press any key to close.
pause >nul
endlocal
