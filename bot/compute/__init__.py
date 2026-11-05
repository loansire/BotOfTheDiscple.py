# -*- coding: utf-8 -*-
"""Côté CALCUL : construit les publications (bot/content/model.py) et les
range en base. Seul le bot live calcule ; tout bot publie depuis la base.

Chaque feature expose un `presenter.py` dont la fonction `build_post()`
renvoie un Post entièrement résolu (textes formatés, images générées).
`store()` l'écrit : une nouvelle version n'apparaît que si le contenu a
changé."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from bot.content import store as content_store
from bot.content.model import Post
from bot.core.logger import log


async def store(post: Post, tag: str) -> bool:
    """Écrit le Post ; True si une nouvelle version a été créée."""
    version, created = await content_store.save_post(post)
    if created:
        log.info(f"[{tag}] Contenu calculé : version {version}.")
    return created


@lru_cache(maxsize=64)
def read_resource(path: Path) -> bytes | None:
    """Octets d'une image locale (Ressources/), ou None si absente. Mis en
    cache : ces fichiers ne changent qu'avec un déploiement."""
    try:
        return path.read_bytes()
    except OSError:
        return None


def mime_of(path: Path) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "application/octet-stream")
