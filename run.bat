@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Set Tesseract path
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"
)

:: Set Poppler path
if exist "%~dp0poppler\Library\bin" (
    set "PATH=%~dp0poppler\Library\bin;%PATH%"
) else if exist "%~dp0poppler\bin" (
    set "PATH=%~dp0poppler\bin;%PATH%"
)

:: Run app
call venv\Scripts\activate.bat
python app\mae.py
