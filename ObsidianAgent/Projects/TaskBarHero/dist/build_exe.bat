@echo off
REM ===========================================================================
REM  Build a standalone TBH_SaveEditor.exe for TaskBarHero.
REM  The .exe bundles Python + pycryptodome + rich, so it runs on ANY Windows
REM  10/11 x64 machine with NO Python install required. Run this once on a build
REM  machine that has Python 3.9+; then copy out\TBH_SaveEditor.exe anywhere.
REM ===========================================================================
setlocal
cd /d "%~dp0"

where python >nul 2>&1 || (echo [ERROR] Python 3.9+ not found on PATH & exit /b 1)

echo [*] Creating isolated build venv...
python -m venv buildenv || (echo [ERROR] venv creation failed & exit /b 1)
call "buildenv\Scripts\activate.bat"

echo [*] Installing build + runtime dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller || (echo [ERROR] pip install failed & exit /b 1)

echo [*] Freezing item_id_swap.py into a one-file console exe...
pyinstaller --onefile --console --name TBH_SaveEditor ^
  --distpath out --workpath build --specpath build ^
  --collect-submodules Crypto ^
  "..\item_id_swap.py" || (echo [ERROR] PyInstaller build failed & exit /b 1)

echo.
echo [OK] Built: %~dp0out\TBH_SaveEditor.exe
echo     Copy that single file to any Windows machine and double-click it,
echo     or run it from a terminal:  TBH_SaveEditor.exe --help
endlocal
