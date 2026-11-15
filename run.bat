@echo off
setlocal enabledelayedexpansion
title Smart Railway Seat Allocation Simulator

cd /d "%~dp0"

echo =======================================================
echo    Smart Railway Seat Allocation Simulator (College)
echo =======================================================
echo.

set "PY_EXE="

:: 1. Check venv in D:\Downloads\railway allotment
if exist "D:\Downloads\railway allotment\.venv\Scripts\python.exe" (
    set "PY_EXE=D:\Downloads\railway allotment\.venv\Scripts\python.exe"
    goto found_py
)

:: 2. Check relative path to sibling railway allotment venv
if exist "%~dp0..\..\railway allotment\.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0..\..\railway allotment\.venv\Scripts\python.exe"
    goto found_py
)

:: 3. Check parent relative path
if exist "%~dp0..\railway allotment\.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0..\railway allotment\.venv\Scripts\python.exe"
    goto found_py
)

:: 4. Check local .venv
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    goto found_py
)

:: 5. Check system python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_EXE=python"
    goto found_py
)

:: 6. Check py launcher
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_EXE=py -3"
    goto found_py
)

:found_py
if "%PY_EXE%"=="" (
    echo [ERROR] Python environment not found!
    echo Please install Python or run inside a configured virtual environment.
    pause
    exit /b 1
)

echo [OK] Using Python: %PY_EXE%
echo [INFO] Starting Flask Server on port 5000...
echo [INFO] Opening web browser at http://127.0.0.1:5000 ...

start http://127.0.0.1:5000
"%PY_EXE%" app.py
pause

