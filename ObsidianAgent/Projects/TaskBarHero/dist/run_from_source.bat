@echo off
REM ===========================================================================
REM  Run item_id_swap.py from source on any Windows with Python 3.9+ installed.
REM  Auto-creates a venv and installs deps on first run. Passes all args through:
REM    run_from_source.bat            -> interactive TUI
REM    run_from_source.bat --help     -> CLI help
REM    run_from_source.bat --legendary
REM  (Prefer TBH_SaveEditor.exe if the target has no Python.)
REM ===========================================================================
setlocal
cd /d "%~dp0"

where python >nul 2>&1 || (echo [ERROR] Python 3.9+ not found on PATH & exit /b 1)

if not exist "runenv\Scripts\python.exe" (
  echo [*] First run: creating venv + installing deps...
  python -m venv runenv || (echo [ERROR] venv creation failed & exit /b 1)
  call "runenv\Scripts\activate.bat"
  python -m pip install -q --upgrade pip
  python -m pip install -q -r requirements.txt || (echo [ERROR] pip install failed & exit /b 1)
) else (
  call "runenv\Scripts\activate.bat"
)

python "..\item_id_swap.py" %*
endlocal
