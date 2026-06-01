"""
Logger — rangli, faylga ham yozuvchi logging setup
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path


class _ColorFormatter(logging.Formatter):
    """Terminal uchun ANSI rangli formatter."""

    COLORS = {
        logging.DEBUG:    "\033[0;36m",   # cyan
        logging.INFO:     "\033[0;32m",   # green
        logging.WARNING:  "\033[0;33m",   # yellow
        logging.ERROR:    "\033[0;31m",   # red
        logging.CRITICAL: "\033[1;31m",   # bold red
    }
    RESET = "\033[0m"
    FMT = "%(asctime)s  %(levelname)-8s  %(name)s  —  %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        formatter = logging.Formatter(
            f"{color}{self.FMT}{self.RESET}",
            datefmt="%H:%M:%S",
        )
        return formatter.format(record)


def setup_logger(name: str = "vodiysoftbot", level: int = logging.INFO) -> logging.Logger:
    """
    Asosiy logger yaratadi:
    - konsolda rangli chiqish
    - logs/ papkasida kunlik fayl
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Konsol handler ──────────────────────────────────────────
    console_h = logging.StreamHandler(sys.stdout)
    console_h.setLevel(level)
    console_h.setFormatter(_ColorFormatter())
    logger.addHandler(console_h)

    # ── Fayl handler ─────────────────────────────────────────────
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"userbot_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_h = logging.FileHandler(log_file, encoding="utf-8")
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s  —  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_h)

    return logger
