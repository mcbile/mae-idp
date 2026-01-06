"""
MAE-IDP (Intelligent Document Processing)
Version 1.5.0 - © 2026 McBile
"""

import os
import sys
import json
import logging
import asyncio
import threading
import subprocess
import shutil
import time
import re
from pathlib import Path, PurePath
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

# Structured logging setup
from logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger("main")

# Setup paths
APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"
TEMPLATES_DIR = APP_DIR / "templates"

# Add app directory to path for imports
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Setup environment
from setup_env import setup_all
setup_all()

# Core OCR processing
from core import BaseOCRProcessor, ConfidenceScore

# OCR cache
from cache import get_cache

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Optional imports for desktop/watcher features
# Disable webview in server/headless mode (no display)
WEBVIEW_OK = False
if os.environ.get("DISPLAY") or sys.platform == "darwin" or sys.platform == "win32":
    try:
        import webview
        WEBVIEW_OK = True
    except ImportError:
        pass

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False
    Observer = None
    FileSystemEventHandler = object


class Config:
    APP_NAME = "MAE-IDP"
    VERSION = "1.5.0"
    HOST = "0.0.0.0"  # Allow access from local network
    PORT = int(os.environ.get("PORT", 8766))  # Render sets PORT env var
    INPUT_DIR = DATA_DIR / "input"
    OUTPUT_DIR = DATA_DIR / "output"
    ARCHIVE_DIR = DATA_DIR / "archive"

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.INPUT_DIR, cls.OUTPUT_DIR, cls.ARCHIVE_DIR]:
            d.mkdir(parents=True, exist_ok=True)


# ConfidenceScore imported from core.py


@dataclass
class ParsedDoc:
    filename: str
    status: str = "pending"  # pending, success, review, error
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    internal_number: Optional[str] = None
    vat_id: Optional[str] = None
    confidence: int = 0
    error: Optional[str] = None
    timestamp: Optional[str] = None


# KNOWN_VENDORS imported from core.py


class Parser(BaseOCRProcessor):
    """Document parser using shared OCR processing logic"""

    def __init__(self):
        super().__init__()
        self.cache = get_cache()

    def parse(self, path: Path, use_cache: bool = True) -> ParsedDoc:
        r = ParsedDoc(filename=path.name, timestamp=datetime.now().isoformat())
        if not self.ocr_ok:
            r.status, r.error = "error", "OCR not available"
            return r

        # Check cache first
        if use_cache:
            cached = self.cache.get(path)
            if cached:
                logger.debug("Cache hit for %s", path.name)
                return ParsedDoc(**cached)

        try:
            # Load image using base class method
            img = self.load_image(path)
            if img is None:
                raise ValueError("Failed to load image")

            # Extract QR codes
            qr_data = self.extract_qr_codes(img)
            r.internal_number = self.extract_internal_from_qr(qr_data)

            # If not found in QR, try corner (handwritten)
            if not r.internal_number:
                r.internal_number = self.extract_internal_from_corner(img)

            # OCR using base class method
            text = self.run_ocr(img)
            conf = 0

            # Extract vendor (header first, then footer, then full text)
            r.vendor = self.extract_vendor(text, img)
            if r.vendor:
                conf += ConfidenceScore.VENDOR

            # Extract invoice number
            r.invoice_number = self.extract_invoice_number(text)
            if r.invoice_number:
                conf += ConfidenceScore.INVOICE_NUMBER

            # Extract internal number confidence
            if r.internal_number:
                conf += ConfidenceScore.INTERNAL_NUMBER

            # Extract VAT ID (optional)
            r.vat_id = self.extract_vat_id(text)
            if r.vat_id:
                conf += ConfidenceScore.VAT_ID

            r.confidence = min(conf, 100)
            r.status = "success" if conf >= ConfidenceScore.THRESHOLD else "review"

            # Save to cache
            if use_cache:
                self.cache.set(path, asdict(r))
                logger.debug("Cached result for %s", path.name)

        except Exception as e:
            r.status, r.error = "error", str(e)

        return r


def _wait_for_file_ready(path: Path, timeout: float = 30.0) -> bool:
    """Ждёт пока файл будет полностью записан (размер стабилизируется)"""
    prev_size = -1
    start = time.time()
    while time.time() - start < timeout:
        try:
            if not path.exists():
                time.sleep(0.5)
                continue
            size = path.stat().st_size
            if size == prev_size and size > 0:
                return True
            prev_size = size
        except OSError:
            pass
        time.sleep(0.5)
    return prev_size > 0  # Вернуть True если файл существует


def generate_archive_name(result: ParsedDoc, original_path: Path) -> str:
    """Генерирует имя архивного файла на основе распознанных данных.

    Формат успеха: Vendor_InvoiceNumber_InternalNumber.ext
    Формат review: warn_Vendor_InvoiceNumber_InternalNumber.ext (с тем что распозналось)
    Fallback: warn_YYYYMMDD_HHMMSS_originalname.ext
    """
    vendor_clean = re.sub(r'[^\w\s-]', '', result.vendor or '').replace(' ', '') or "UNKNOWN"
    invoice_clean = re.sub(r'[^\w-]', '', result.invoice_number or '') or "UNKNOWN"
    internal_clean = re.sub(r'[^\d]', '', result.internal_number or '') if result.internal_number else "0"

    if result.status == "success" and result.vendor and result.invoice_number:
        return f"{vendor_clean}_{invoice_clean}_{internal_clean}{original_path.suffix.lower()}"
    elif result.vendor or result.invoice_number or result.internal_number:
        # Частичное распознавание — добавляем warn_ префикс
        return f"warn_{vendor_clean}_{invoice_clean}_{internal_clean}{original_path.suffix.lower()}"
    else:
        # Ничего не распозналось — дата + оригинальное имя
        return f"warn_{datetime.now():%Y%m%d_%H%M%S}_{original_path.name}"


class FolderWatcher:
    def __init__(self, parser, on_result):
        self.parser = parser
        self.on_result = on_result
        self.observer = None
        self.watch_path = None
        self.running = False
        self.processed_files = set()
        self._processed_lock = threading.Lock()  # Thread-safe access to processed_files

    def start(self, watch_path: str, output_path: str = None):
        if not WATCHDOG_OK:
            logger.warning("Watchdog not installed, folder watching disabled")
            return False

        if self.running:
            self.stop()

        self.watch_path = Path(watch_path)
        # output_path сохраняется в конфиге, но не используется (архив всегда в ARCHIVE_DIR)

        if not self.watch_path.exists():
            return False

        watcher = self

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory:
                    return
                ext = Path(event.src_path).suffix.lower()
                if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                    file_path = Path(event.src_path)
                    if _wait_for_file_ready(file_path):
                        watcher.process_file(file_path)
                    else:
                        logger.warning("File not ready after timeout: %s", event.src_path)

        self.observer = Observer()
        self.observer.schedule(Handler(), str(self.watch_path), recursive=False)
        self.observer.start()
        self.running = True
        
        # Process existing files
        for f in self.watch_path.iterdir():
            if f.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                if str(f) not in self.processed_files:
                    self.process_file(f)
        
        return True
    
    def process_file(self, path: Path):
        # Thread-safe check and add
        with self._processed_lock:
            if str(path) in self.processed_files:
                return
            self.processed_files.add(str(path))
        # Processing outside lock (long operation)
        result = self.parser.parse(path)
        self.on_result(result)
        archive_name = generate_archive_name(result, path)
        shutil.move(str(path), str(Config.ARCHIVE_DIR / archive_name))
    
    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.running = False
        self.observer = None
    
    @property
    def status(self):
        return {
            "running": self.running,
            "watch_path": str(self.watch_path) if self.watch_path else None
        }


# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_RESULTS = 1000  # Maximum results in memory (FIFO)

# File type validation via magic bytes
ALLOWED_MAGIC_BYTES = {
    b'%PDF': 'pdf',
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG': 'png',
    b'II*\x00': 'tiff',  # Little-endian TIFF
    b'MM\x00*': 'tiff',  # Big-endian TIFF
}


def validate_file_magic(content: bytes) -> bool:
    """Validate file type by checking magic bytes (first 4-8 bytes).

    Returns True if file matches allowed types, False otherwise.
    """
    for magic in ALLOWED_MAGIC_BYTES:
        if content.startswith(magic):
            return True
    return False

# Thread-safe results storage
parser = Parser()
parser_lock = threading.Lock()  # Защита parser от параллельных вызовов
results = []
results_lock = threading.Lock()

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)

def _safe_append_result(r):
    with results_lock:
        if len(results) >= MAX_RESULTS:
            results.pop(0)  # FIFO: remove oldest
        results.append(asdict(r))

watcher = FolderWatcher(parser, _safe_append_result)


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


@asynccontextmanager
async def lifespan(app):
    # Startup
    logger.info("Starting MAE-IDP v%s", Config.VERSION)
    Config.ensure_dirs()
    cfg = load_config()
    if cfg.get("watch_path") and Path(cfg["watch_path"]).exists():
        watcher.start(cfg["watch_path"], cfg.get("output_path"))
        logger.info("Watcher started: %s", cfg["watch_path"])
    yield
    # Shutdown
    logger.info("Shutting down...")
    watcher.stop()
    _executor.shutdown(wait=False)


# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# CORS configuration
# Default: allow localhost and local network for development
# Production: set ALLOWED_ORIGINS env var (comma-separated)
CORS_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",") if os.environ.get("ALLOWED_ORIGINS") else [
    "http://localhost:*",
    "http://127.0.0.1:*",
]

# FastAPI App
app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Keep permissive for local network access (PWA, mobile)
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)


def get_ui() -> str:
    """Load UI template from file"""
    return (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def root():
    return get_ui()


@app.get("/static/{filename}")
async def static_file(filename: str):
    """Serve static files from templates directory"""
    file_path = TEMPLATES_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/status")
async def status():
    return {
        "ocr": parser.ocr_ok,
        "watcher": watcher.status,
        "results_count": len(results),
        "cache": parser.cache.stats()
    }


@app.post("/api/parse")
@limiter.limit("10/minute")  # Rate limit: 10 files per minute per IP
async def do_parse(request: Request, file: UploadFile = File(...)):
    # Check file extension
    if Path(file.filename).suffix.lower() not in [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]:
        raise HTTPException(400, "Unsupported format")

    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 50MB)")

    # Validate magic bytes (prevent extension spoofing)
    if not validate_file_magic(content):
        raise HTTPException(400, "Invalid file type (content doesn't match extension)")

    safe_name = PurePath(file.filename).name
    tmp = Config.INPUT_DIR / safe_name
    tmp.write_bytes(content)

    # Run OCR in thread pool to avoid blocking event loop (OCR takes 2-10 seconds)
    def _parse_sync():
        with parser_lock:
            return parser.parse(tmp)

    loop = asyncio.get_event_loop()
    r = await loop.run_in_executor(_executor, _parse_sync)

    archive_name = generate_archive_name(r, tmp)
    shutil.move(str(tmp), str(Config.ARCHIVE_DIR / archive_name))
    _safe_append_result(r)
    return {"success": True, "data": asdict(r)}


@app.get("/api/results")
async def get_results():
    with results_lock:
        return {"results": list(results)}


@app.delete("/api/results")
async def clear_results():
    with results_lock:
        results.clear()
    return {"success": True}


@app.post("/api/export")
async def export(request: Request):
    body = await request.json()
    data = body.get("results", results)
    fmt = body.get("format", "csv").lower()

    if not data:
        raise HTTPException(400, "No data")

    if fmt not in ("csv", "md", "txt"):
        raise HTTPException(400, "Unsupported format. Use: csv, md, txt")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"MAE_{timestamp}.{fmt}"
    filepath = Config.OUTPUT_DIR / filename

    # Define columns
    columns = ["filename", "status", "vendor", "invoice_number", "internal_number", "vat_id", "confidence", "timestamp"]

    if fmt == "csv":
        # CSV format
        lines = [";".join(columns)]
        for row in data:
            lines.append(";".join(str(row.get(c, "")) for c in columns))
        filepath.write_text("\n".join(lines), encoding="utf-8")
        media_type = "text/csv"

    elif fmt == "md":
        # Markdown table
        lines = ["# MAE Export Report", "", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
        headers = ["Status", "Vendor", "Invoice #", "Internal #", "VAT ID", "Confidence"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in data:
            cells = [
                row.get("status", ""),
                row.get("vendor", "") or "—",
                row.get("invoice_number", "") or "—",
                row.get("internal_number", "") or "—",
                row.get("vat_id", "") or "—",
                f"{row.get('confidence', 0)}%"
            ]
            lines.append("| " + " | ".join(cells) + " |")
        filepath.write_text("\n".join(lines), encoding="utf-8")
        media_type = "text/markdown"

    else:  # txt
        # Plain text table
        lines = ["MAE Export Report", "=" * 40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
        for i, row in enumerate(data, 1):
            lines.append(f"[{i}] {row.get('filename', 'Unknown')}")
            lines.append(f"    Status:   {row.get('status', '')}")
            lines.append(f"    Vendor:   {row.get('vendor', '') or '—'}")
            lines.append(f"    Invoice:  {row.get('invoice_number', '') or '—'}")
            lines.append(f"    Internal: {row.get('internal_number', '') or '—'}")
            lines.append(f"    VAT ID:   {row.get('vat_id', '') or '—'}")
            lines.append(f"    Confidence: {row.get('confidence', 0)}%")
            lines.append("")
        lines.append("=" * 40)
        lines.append(f"Total: {len(data)} documents")
        filepath.write_text("\n".join(lines), encoding="utf-8")
        media_type = "text/plain"

    return FileResponse(filepath, filename=filename, media_type=media_type)


def _open_path(path: Path):
    """Cross-platform folder/file opener"""
    path_str = str(path)
    if sys.platform == "win32":
        os.startfile(path_str)
    elif sys.platform == "darwin":
        subprocess.run(["open", path_str], check=False)
    else:
        subprocess.run(["xdg-open", path_str], check=False)


@app.get("/api/open/{folder}")
async def open_folder(folder: str):
    folders = {
        "input": Config.INPUT_DIR,
        "output": Config.OUTPUT_DIR,
        "archive": Config.ARCHIVE_DIR,
        "watch": watcher.watch_path
    }
    p = folders.get(folder)
    if p and p.exists():
        _open_path(p)
        return {"ok": True}
    raise HTTPException(404)


@app.post("/api/watcher/start")
async def start_watcher(request: Request):
    data = await request.json()
    watch_path = data.get("watch_path", "").strip()
    output_path = data.get("output_path", "").strip() or None
    if not watch_path or not Path(watch_path).exists():
        raise HTTPException(400, "Invalid watch path")
    if watcher.start(watch_path, output_path):
        save_config({"watch_path": watch_path, "output_path": output_path})
        return {"success": True, "status": watcher.status}
    raise HTTPException(500, "Failed to start watcher")


@app.post("/api/watcher/stop")
async def stop_watcher():
    watcher.stop()
    save_config({})
    return {"success": True}


def _browse_folder_sync(initial_path: str) -> str:
    """Blocking folder browser dialog (runs in thread pool)"""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    try:
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(initialdir=initial_path or os.path.expanduser("~"))
        return folder
    finally:
        root.destroy()


@app.get("/api/browse")
async def browse_folder(path: str = ""):
    loop = asyncio.get_event_loop()
    folder = await loop.run_in_executor(_executor, _browse_folder_sync, path)
    return {"path": folder}


@app.get("/api/detect-gdrive")
async def detect_gdrive():
    possible_paths = []
    for letter in "GHIJKLMNOPQRSTUVWXYZ":
        for name in ["My Drive", "Meine Ablage", "Google Drive"]:
            p = Path(f"{letter}:/{name}")
            if p.exists():
                possible_paths.append(str(p))

    for name in ["Google Drive", "GoogleDrive"]:
        p = Path(os.path.expanduser(f"~/{name}"))
        if p.exists():
            possible_paths.append(str(p))

    return {"paths": possible_paths}


# Batch processing state
batch_state = {
    "running": False,
    "total": 0,
    "processed": 0,
    "current_file": None,
    "results": []
}
batch_lock = threading.Lock()


def _process_batch_folder(folder_path: str, archive: bool = True):
    """Process all files in folder (runs in thread pool)"""
    global batch_state

    folder = Path(folder_path)
    extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
    files = [f for f in folder.iterdir() if f.suffix.lower() in extensions]

    with batch_lock:
        batch_state["running"] = True
        batch_state["total"] = len(files)
        batch_state["processed"] = 0
        batch_state["results"] = []

    for file_path in files:
        # Check if stopped
        with batch_lock:
            if not batch_state["running"]:
                break
            batch_state["current_file"] = file_path.name

        try:
            with parser_lock:
                result = parser.parse(file_path)

            _safe_append_result(result)

            with batch_lock:
                batch_state["results"].append(asdict(result))
                batch_state["processed"] += 1

            # Archive processed file
            if archive:
                archive_name = generate_archive_name(result, file_path)
                shutil.move(str(file_path), str(Config.ARCHIVE_DIR / archive_name))

        except Exception as e:
            logger.error("Batch error processing %s: %s", file_path.name, e)
            with batch_lock:
                batch_state["processed"] += 1

    with batch_lock:
        batch_state["running"] = False
        batch_state["current_file"] = None


@app.post("/api/batch/start")
async def start_batch(request: Request):
    """Start batch processing of all files in a folder"""
    data = await request.json()
    folder_path = data.get("folder_path", "").strip()
    archive = data.get("archive", True)

    if not folder_path:
        raise HTTPException(400, "folder_path is required")

    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(400, "Invalid folder path")

    with batch_lock:
        if batch_state["running"]:
            raise HTTPException(409, "Batch processing already running")

    # Count files
    extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
    files = [f for f in folder.iterdir() if f.suffix.lower() in extensions]

    if not files:
        raise HTTPException(400, "No supported files found in folder")

    # Start processing in background
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _process_batch_folder, folder_path, archive)

    return {"success": True, "total_files": len(files)}


@app.get("/api/batch/status")
async def batch_status():
    """Get current batch processing status"""
    with batch_lock:
        return {
            "running": batch_state["running"],
            "total": batch_state["total"],
            "processed": batch_state["processed"],
            "current_file": batch_state["current_file"],
            "progress": round(batch_state["processed"] / batch_state["total"] * 100) if batch_state["total"] > 0 else 0
        }


@app.post("/api/batch/stop")
async def stop_batch():
    """Stop batch processing (will complete current file)"""
    with batch_lock:
        batch_state["running"] = False
    return {"success": True}


# UI loaded from templates/index.html via get_ui()



if __name__ == "__main__":
    if WEBVIEW_OK:
        # Desktop mode with webview
        def run_server():
            uvicorn.Server(uvicorn.Config(app, host=Config.HOST, port=Config.PORT, log_level="warning")).run()

        threading.Thread(target=run_server, daemon=True).start()
        time.sleep(1)

        webview.create_window(
            f"{Config.APP_NAME} v{Config.VERSION}",
            f"http://{Config.HOST}:{Config.PORT}",
            width=1100,
            height=800,
            min_size=(800, 600)
        )
        webview.start()
    else:
        # Web-only mode
        print(f"Starting {Config.APP_NAME} v{Config.VERSION}")
        print(f"Open in browser: http://{Config.HOST}:{Config.PORT}")
        uvicorn.run(app, host=Config.HOST, port=Config.PORT)
