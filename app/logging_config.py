"""
MAE-IDP Structured Logging Configuration
Provides JSON logging for production and pretty logging for development
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key in ["request_id", "file", "duration_ms", "user_agent"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data, ensure_ascii=False)


class PrettyFormatter(logging.Formatter):
    """Colored pretty formatter for development"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Shorten logger name
        name = record.name
        if name.startswith("mae_idp."):
            name = name[8:]
        elif name == "__main__":
            name = "main"

        formatted = f"{color}[{timestamp}] {record.levelname:7}{self.RESET} {name}: {record.getMessage()}"

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def setup_logging(
    level: str = "INFO",
    json_format: bool = None,
    log_file: str = None
) -> logging.Logger:
    """
    Configure logging for MAE-IDP

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format (auto-detected from env if None)
        log_file: Optional file path for logging

    Returns:
        Root logger
    """
    # Auto-detect JSON format from environment
    if json_format is None:
        json_format = os.environ.get("MAE_LOG_JSON", "").lower() in ("1", "true", "yes")

    # Get level from environment if not specified
    level = os.environ.get("MAE_LOG_LEVEL", level).upper()

    # Create root logger
    root_logger = logging.getLogger("mae_idp")
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)

    if json_format:
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(PrettyFormatter())

    root_logger.addHandler(console)

    # File handler (always JSON for parsing)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a module"""
    return logging.getLogger(f"mae_idp.{name}")
