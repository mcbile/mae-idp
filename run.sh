#!/bin/bash
# MAE-IDP - Run Script for macOS/Linux
# © 2026 McBile AI-Engine

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Активация виртуального окружения
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found!"
    echo "Please run ./install.sh first"
    exit 1
fi

# Запуск приложения
echo "Starting MAE-IDP..."
python3 app/mae.py
