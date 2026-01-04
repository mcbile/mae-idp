@echo off
chcp 65001 >nul
title MAE-IDP - Setup
color 0F

echo.
echo   ╔════════════════════════════════════════════════════╗
echo   ║                                                    ║
echo   ║   MAE-IDP - Setup                                  ║
echo   ║   Version 1.5.0                                    ║
echo   ║                                                    ║
echo   ╚════════════════════════════════════════════════════╝
echo.

:: Check Python
echo   [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found!
    echo   Please install Python 3.12+ from https://python.org
    echo   Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)
echo   [OK] Python found

:: Create venv
echo   [2/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)
echo   [OK] Virtual environment ready

:: Activate and install
echo   [3/5] Installing dependencies (2-3 min)...
call venv\Scripts\activate.bat
pip install --quiet --disable-pip-version-check -r requirements.txt
echo   [OK] Dependencies installed

:: Download Poppler
echo   [4/5] Setting up Poppler (PDF support)...
if not exist "poppler" (
    mkdir poppler 2>nul
    echo   Downloading Poppler...
    curl -L -o poppler.zip "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.02.0-0/Release-24.02.0-0.zip" --progress-bar
    echo   Extracting...
    powershell -Command "Expand-Archive -Path 'poppler.zip' -DestinationPath 'poppler_tmp' -Force"
    for /d %%i in (poppler_tmp\*) do xcopy "%%i\*" "poppler\" /E /Y /Q >nul
    del poppler.zip
    rmdir /S /Q poppler_tmp
)
echo   [OK] Poppler ready

:: Create directories
echo   [5/5] Creating data directories...
mkdir data\input 2>nul
mkdir data\output 2>nul
mkdir data\archive 2>nul
echo   [OK] Directories created

:: Check Tesseract
echo.
echo   ────────────────────────────────────────────────────
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo   [OK] Tesseract OCR found
) else (
    echo   [!] Tesseract OCR not found
    echo.
    echo   Please install Tesseract:
    echo   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo   2. Run installer, select "German" language
    echo   3. Install to: C:\Program Files\Tesseract-OCR
    echo.
    echo   Press any key to open download page...
    pause >nul
    start "" "https://github.com/UB-Mannheim/tesseract/wiki"
)

echo.
echo   ╔════════════════════════════════════════════════════╗
echo   ║                                                    ║
echo   ║   Setup Complete!                                  ║
echo   ║                                                    ║
echo   ║   Run the app:  run.bat                            ║
echo   ║                                                    ║
echo   ╚════════════════════════════════════════════════════╝
echo.
pause
