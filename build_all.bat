@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM command_Backup - One-click dual-arch build (x86 + x64)
REM ============================================================
REM This script runs the existing Python orchestrator:
REM   command_Backup\build_all.py
REM
REM Outputs (by default):
REM   command_Backup\release\command_Backup-x86.exe
REM   command_Backup\release\command_Backup-x64.exe
REM   command_Backup\release\config.ini
REM
REM Prereqs:
REM - x64 Python configured in command_Backup\build_config.ini (python_x64)
REM - x86 Python (embedded OK) configured in command_Backup\build_config.ini (python_x86)
REM - PyInstaller installed in BOTH Python environments
REM ============================================================

REM --- Resolve repository root (directory containing this .bat) ---
set "REPO_ROOT=%~dp0"

REM Strip trailing backslash safely (avoids substring expansion pitfalls in some cmd parsing cases)
REM Example: "C:\path\to\dir\" -> "C:\path\to\dir"
if defined REPO_ROOT (
  if "%REPO_ROOT:~-1%"=="\" (
    set "REPO_ROOT=%REPO_ROOT:~0,-1%"
  )
)

REM --- Configure which Python to use to run the orchestrator itself ---
REM Recommended: x64 Python (it only orchestrates; actual builds use python_x86/python_x64 from build_config.ini)
set "PYTHON_X64=D:\Programs\Python\python.exe"

echo ============================================================
echo  command_Backup - Dual-arch build (x86 + x64)
echo ============================================================
echo Repo root : "%REPO_ROOT%"
echo Runner    : "%PYTHON_X64%"
echo.

REM --- Basic checks ---
if not exist "%PYTHON_X64%" (
  echo ERROR: x64 Python not found at:
  echo   "%PYTHON_X64%"
  echo.
  echo Fix: Edit command_Backup\build_all.bat and update PYTHON_X64,
  echo      or install Python x64 at that location.
  echo.
  pause
  exit /b 1
)

if not exist "%REPO_ROOT%\build_all.py" (
  echo ERROR: Orchestrator not found:
  echo   "%REPO_ROOT%\build_all.py"
  echo.
  echo Fix: Ensure this .bat file is located in the same directory as build_all.py
  echo      (expected: command_Backup\build_all.bat).
  echo.
  pause
  exit /b 1
)

if not exist "%REPO_ROOT%\build_config.ini" (
  echo NOTE: build_config.ini not found at:
  echo   "%REPO_ROOT%\build_config.ini"
  echo build_all.py may create a template, but you must fill python_x86/python_x64.
  echo.
)

REM --- Run orchestrator ---
echo Running:
echo   "%PYTHON_X64%" "%REPO_ROOT%\build_all.py"
echo.

"%PYTHON_X64%" "%REPO_ROOT%\build_all.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo ============================================================
  echo  BUILD FAILED (exit code %RC%)
  echo ============================================================
  echo.
  echo Troubleshooting tips:
  echo  - Verify python_x86/python_x64 paths in command_Backup\build_config.ini
  echo  - Ensure PyInstaller is installed in BOTH environments:
  echo      ^<python_x86^> -m pip install pyinstaller
  echo      ^<python_x64^> -m pip install pyinstaller
  echo  - For embedded Python, ensure python314._pth enables:
  echo      Lib
  echo      Lib\site-packages
  echo      import site
  echo.
  pause
  exit /b %RC%
)

echo ============================================================
echo  BUILD SUCCESS
echo ============================================================
echo Release folder:
echo   "%REPO_ROOT%\release"
echo.
if exist "%REPO_ROOT%\release" (
  dir /b "%REPO_ROOT%\release"
) else (
  echo NOTE: release directory not found. Check build_all.py output above.
)
echo.
pause
exit /b 0
