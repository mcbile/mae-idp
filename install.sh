#!/bin/bash
# MAE-IDP - Installation Script for macOS/Linux
# © 2026 McBile AI-Engine

set -e

echo "=================================="
echo "MAE-IDP - Installation"
echo "=================================="

# Определение платформы
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Platform: $OS ($ARCH)"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.10+ first:"
    if [[ "$OS" == "Darwin" ]]; then
        echo "  brew install python@3.11"
    else
        echo "  sudo apt install python3 python3-pip python3-venv"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Создание виртуального окружения
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Активация venv
source venv/bin/activate

# Установка зависимостей
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Установка системных зависимостей
echo ""
echo "Checking system dependencies..."

if [[ "$OS" == "Darwin" ]]; then
    # macOS
    if ! command -v brew &> /dev/null; then
        echo "WARNING: Homebrew not found. Install from https://brew.sh"
        echo "Then run: brew install tesseract poppler"
    else
        echo "Installing Tesseract and Poppler via Homebrew..."

        if ! command -v tesseract &> /dev/null; then
            brew install tesseract
            # Установка языков
            brew install tesseract-lang
        else
            echo "Tesseract already installed"
        fi

        if ! command -v pdftoppm &> /dev/null; then
            brew install poppler
        else
            echo "Poppler already installed"
        fi
    fi
elif [[ "$OS" == "Linux" ]]; then
    # Linux
    if command -v apt &> /dev/null; then
        echo "Debian/Ubuntu detected"
        echo "Installing via apt..."
        sudo apt update
        sudo apt install -y tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng poppler-utils libzbar0
    elif command -v dnf &> /dev/null; then
        echo "Fedora/RHEL detected"
        echo "Installing via dnf..."
        sudo dnf install -y tesseract tesseract-langpack-deu tesseract-langpack-eng poppler-utils zbar
    elif command -v pacman &> /dev/null; then
        echo "Arch Linux detected"
        echo "Installing via pacman..."
        sudo pacman -S --noconfirm tesseract tesseract-data-deu tesseract-data-eng poppler zbar
    else
        echo "WARNING: Unknown package manager"
        echo "Please install manually: tesseract, poppler-utils, zbar"
    fi
fi

# Создание папок
echo ""
echo "Creating data directories..."
mkdir -p data/input data/output data/archive

# Проверка установки
echo ""
echo "=================================="
echo "Verifying installation..."
echo "=================================="

if command -v tesseract &> /dev/null; then
    TESS_VER=$(tesseract --version 2>&1 | head -n1)
    echo "✓ Tesseract: $TESS_VER"
else
    echo "✗ Tesseract: NOT FOUND"
fi

if command -v pdftoppm &> /dev/null; then
    echo "✓ Poppler: installed"
else
    echo "✗ Poppler: NOT FOUND"
fi

echo ""
echo "=================================="
echo "Installation complete!"
echo "=================================="
echo ""
echo "To run the application:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python3 app/mae.py"
echo ""
