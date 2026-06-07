# -*- coding: utf-8 -*-
import logging
import sys

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s"
_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("bot")
    if logger.handlers:  # évite les handlers en double si réimporté
        return logger

    logger.setLevel(logging.INFO)

    # Console en UTF-8 (emojis Discord / accents Bungie)
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


log = _build_logger()