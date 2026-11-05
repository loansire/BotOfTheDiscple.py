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

from bot.bungie.reset import last_reset
from bot.content import store as content_store
from bot.content.model import Component, Post, image
from bot.core.logger import log
from bot.render.item_icon import get_item_icon, purge_icon_cache


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


async def item_section(item, lines: list[str], filename: str, feature: str) -> Component | None:
    """Section d'un item : `lines` (vides ignorées) à gauche, icône composée
    (icône + watermark) en vignette. None si l'icône est indisponible (l'item
    est alors ignoré, comme avant la migration)."""
    data = await get_item_icon(item.item_hash, item.icon, item.watermark, feature=feature)
    if data is None:
        return None
    return image("section", data, filename, text="\n".join(line for line in lines if line))


_purged_for: dict[str, str] = {}


def purge_icons_once_per_reset(feature: str) -> None:
    """Vide le cache disque d'icônes d'une feature au premier calcul d'un
    nouveau reset seulement : les calculs suivants (réparation, nouveau
    salon) réutilisent les icônes déjà composées."""
    reset_id = last_reset().isoformat()
    if _purged_for.get(feature) != reset_id:
        purge_icon_cache(feature)
        _purged_for[feature] = reset_id
