@echo off
REM Analyse a CAD file from the command line.
REM
REM   run_analysis.bat                         analyses the sample bracket
REM   run_analysis.bat "C:\path\to\part.step"  analyses your own file
REM
REM This needs no virtual environment and no installed packages.
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
    echo ERROR: Python was not found. Install it from https://www.python.org/downloads/
    pause >nul
    exit /b 1
)

set TARGET=%~1
if "%TARGET%"=="" set TARGET=example_parts\sample_bracket.STEP

echo Analysing %TARGET%
echo.
%PYTHON% analyze.py "%TARGET%" --output "DFX_Report.txt"

echo.
pause >nul
endlocal
