# -*- coding: utf-8 -*-
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from bot.config import OUTPUT_DIR

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s"
_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
_LOG_FILE = OUTPUT_DIR / "bot.log"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("bot")
    if logger.handlers:  # évite les handlers en double si réimporté
        return logger

    # Le logger laisse tout passer ; ce sont les handlers qui filtrent.
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    # --- Console (UTF-8 pour emojis Discord / accents Bungie) ---
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")
    console = logging.StreamHandler(stream)
    console.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    console.setFormatter(formatter)
    logger.addHandler(console)

    # --- Fichier bot.log (tout, avec rotation par taille) ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 Mo
        backupCount=5,             # bot.log, bot.log.1 … bot.log.5
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


log = _build_logger()