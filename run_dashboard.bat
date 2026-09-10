@echo off
REM Start the DFX web dashboard and open it in your browser.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo The virtual environment is missing. Run setup.bat first.
    echo.
    echo Press any key to close.
    pause >nul
    exit /b 1
)

echo Starting the DFX dashboard...
echo.
echo Your browser will open at http://localhost:5000
echo Leave THIS window open while you use it.
echo Press Ctrl+C here when you are finished.
echo.

REM Give the server a moment to bind before the browser asks for the page.
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start "" http://localhost:5000"

".venv\Scripts\python.exe" "web_dashboard\app.py"

echo.
echo Server stopped. Press any key to close.
pause >nul
endlocal
