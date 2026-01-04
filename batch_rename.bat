@echo off
chcp 65001 >nul
title MAE Batch Rename

:: Проверяем аргументы
if "%~1"=="" (
    echo.
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║        MAE Batch Rename - Пакетное переименование            ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo Использование:
    echo   batch_rename.bat "ВХОДНАЯ_ПАПКА" "ВЫХОДНАЯ_ПАПКА"
    echo.
    echo Примеры:
    echo   batch_rename.bat "D:\Invoices" "D:\Sorted"
    echo   batch_rename.bat "G:\My Drive\Invoices" "D:\Sorted"
    echo.
    echo Результат:
    echo   - Файлы будут переименованы в формат: Vendor_InvoiceNumber_InternalNumber
    echo   - Отсортированы по папкам вендоров (Amazon, DHL, и т.д.)
    echo   - Нераспознанные попадут в папку _ПРОВЕРИТЬ
    echo   - Создастся Excel отчёт со всеми данными
    echo.
    pause
    exit /b 1
)

:: Пути
set ROOT=%~dp0
set VENV=%ROOT%venv
set TESSERACT=C:\Program Files\Tesseract-OCR
set POPPLER=%ROOT%poppler\Library\bin

:: Проверяем виртуальное окружение
if not exist "%VENV%\Scripts\activate.bat" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Сначала запустите install.bat
    pause
    exit /b 1
)

:: Активируем окружение и настраиваем пути
call "%VENV%\Scripts\activate.bat"
set PATH=%TESSERACT%;%POPPLER%;%PATH%

:: Запускаем скрипт
echo.
python "%ROOT%app\batch_rename.py" %*

echo.
pause
