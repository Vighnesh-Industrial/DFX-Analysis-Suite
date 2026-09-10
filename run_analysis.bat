@echo off
REM ---------------------------------------------------------------------
REM Analyse a CAD file and open the report.
REM
REM   Double-click this file          - analyses the sample bracket
REM   Drag a .step file onto this file - analyses that file
REM   run_analysis.bat "C:\path\to\part.step"
REM
REM Needs no virtual environment and no installed packages.
REM ---------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set PYTHON=
if exist ".venv\Scripts\python.exe" set PYTHON=".venv\Scripts\python.exe"
if not defined PYTHON (
    py -3 --version >nul 2>&1 && set PYTHON=py -3
)
if not defined PYTHON (
    python --version >nul 2>&1 && set PYTHON=python
)
if not defined PYTHON (
    echo ERROR: Python was not found.
    echo Install Python 3.8 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation.
    pause >nul
    exit /b 1
)

set TARGET=%~1
if "%TARGET%"=="" set TARGET=example_parts\sample_bracket.STEP

REM If a matching .stl sits beside the file, use it: that is what gives
REM wall thickness, true volume and shaded pictures.
set MESH=
if not "%~1"=="" (
    if exist "%~dpn1.stl" set MESH=--mesh "%~dpn1.stl"
)
if "%~1"=="" set MESH=--mesh "example_parts\sample_bracket.stl"

echo.
echo Analysing %TARGET%
if defined MESH echo Using the matching STL for wall thickness.
echo.

%PYTHON% analyze.py "%TARGET%" %MESH% --output "DFX_Report.txt" --html "DFX_Report.html"
if errorlevel 1 (
    echo.
    echo The analysis reported a problem - read the message above.
    echo.
    pause >nul
    exit /b 1
)

echo.
echo Opening the report in your browser...
start "" "DFX_Report.html"
echo.
echo Saved next to this file:
echo   DFX_Report.html  - the one to read, and to print as PDF
echo   DFX_Report.txt   - the same thing as plain text
echo.
echo Press any key to close this window.
pause >nul
endlocal
