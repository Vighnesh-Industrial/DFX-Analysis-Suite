@echo off
REM ---------------------------------------------------------------------
REM DFX Analysis Suite - one-time setup for Windows.
REM Double-click this file, or run it from a Command Prompt.
REM
REM It never relies on "activate" or on a bare "pip" being on PATH, which
REM is the usual cause of "pip is not recognized" during setup.
REM ---------------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo.
echo === DFX Analysis Suite setup ===
echo Working folder: %CD%
echo.

REM 1. Find a Python interpreter.
set PYTHON=
py -3 --version >nul 2>&1 && set PYTHON=py -3
if not defined PYTHON (
    python --version >nul 2>&1 && set PYTHON=python
)
if not defined PYTHON (
    echo ERROR: Python was not found.
    echo Install Python 3.8 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation.
    goto :end
)
echo Using interpreter: %PYTHON%
%PYTHON% --version

REM 2. Create the virtual environment if it is not there yet.
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment in .venv ...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo ERROR: could not create the virtual environment.
        goto :end
    )
) else (
    echo Virtual environment already exists.
)

REM 3. Install the dashboard dependencies using the venv's own python.
echo.
echo Installing dependencies ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: dependency installation failed. See the message above.
    goto :end
)

REM 4. Prove the install works.
echo.
echo Running the test suite ...
".venv\Scripts\python.exe" -m unittest discover -s tests
if errorlevel 1 (
    echo.
    echo WARNING: some tests failed. The tool may still run.
)

echo.
echo === Setup complete ===
echo.
echo   Analyse the sample part:   run_analysis.bat
echo   Start the web dashboard:   run_dashboard.bat
echo.

:end
echo Press any key to close this window.
pause >nul
endlocal
