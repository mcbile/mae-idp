"""
Environment setup for MAE-IDP
Configures Tesseract and Poppler paths for all platforms
"""

import os
import sys
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent


def get_platform() -> str:
    """Определить текущую платформу"""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    else:
        return "linux"


def setup_tesseract() -> bool:
    """Setup Tesseract OCR path for all platforms"""
    platform = get_platform()

    # Пути для поиска Tesseract
    search_paths = []

    if platform == "windows":
        search_paths = [
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
            ROOT_DIR / "tesseract" / "tesseract.exe",
        ]
    elif platform == "macos":
        search_paths = [
            Path("/opt/homebrew/bin/tesseract"),  # Apple Silicon
            Path("/usr/local/bin/tesseract"),      # Intel Mac (Homebrew)
            Path("/usr/bin/tesseract"),
            ROOT_DIR / "tesseract" / "tesseract",
        ]
    else:  # Linux
        search_paths = [
            Path("/usr/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
            Path("/snap/bin/tesseract"),
            ROOT_DIR / "tesseract" / "tesseract",
        ]

    # Также проверить через which/where
    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        search_paths.insert(0, Path(tesseract_in_path))

    for p in search_paths:
        if p.exists():
            os.environ["TESSERACT_CMD"] = str(p)
            # Установить напрямую для pytesseract
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = str(p)
            except ImportError:
                pass
            return True

    return False


def setup_poppler() -> bool:
    """Setup Poppler path for PDF processing (all platforms)"""
    platform = get_platform()

    search_paths = []

    if platform == "windows":
        search_paths = [
            ROOT_DIR / "poppler" / "Library" / "bin",
            ROOT_DIR / "poppler" / "bin",
            Path("C:/Program Files/poppler/bin"),
        ]
    elif platform == "macos":
        search_paths = [
            Path("/opt/homebrew/bin"),      # Apple Silicon (Homebrew)
            Path("/usr/local/bin"),          # Intel Mac (Homebrew)
            ROOT_DIR / "poppler" / "bin",
        ]
    else:  # Linux
        search_paths = [
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            ROOT_DIR / "poppler" / "bin",
        ]

    # Проверить наличие pdftoppm (часть poppler)
    pdftoppm_in_path = shutil.which("pdftoppm")
    if pdftoppm_in_path:
        return True  # Poppler уже в PATH

    for p in search_paths:
        pdftoppm = p / ("pdftoppm.exe" if platform == "windows" else "pdftoppm")
        if pdftoppm.exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            return True

    return False


def setup_all() -> dict:
    """Setup all environment variables, returns status dict"""
    tesseract_ok = setup_tesseract()
    poppler_ok = setup_poppler()

    return {
        "platform": get_platform(),
        "tesseract": tesseract_ok,
        "poppler": poppler_ok
    }
