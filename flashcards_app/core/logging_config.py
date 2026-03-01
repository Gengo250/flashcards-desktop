from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    base_dir = Path.home() / ".flashcards_app"
    base_dir.mkdir(parents=True, exist_ok=True)
    log_path = base_dir / "app.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=2, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)