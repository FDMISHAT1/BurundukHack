@echo off
REM Build BurundukHack into a standalone .exe for Windows
REM Output: dist\BurundukHack.exe

echo === BurundukHack Builder ===
echo.

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: python not found. Install Python 3.10+
    exit /b 1
)

REM Create venv if needed
if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

echo [1/3] Installing dependencies...
pip install -q rich pyyaml prompt_toolkit pyinstaller

echo [2/3] Building executable...
pyinstaller burunduk.spec --clean --noconfirm

echo [3/3] Done!
echo.

if exist "dist\BurundukHack.exe" (
    echo   Output: dist\BurundukHack.exe
    echo   Run:    dist\BurundukHack.exe
    echo.
    echo   To distribute: just copy dist\BurundukHack.exe
    echo   No Python or dependencies needed on target machine!
) else (
    echo   ERROR: Build failed.
    exit /b 1
)
