# -*- coding: utf-8 -*-
"""Icônes d'items Xûr : téléchargement de l'icon Bungie, superposition de
l'iconWatermark (si présent), mise en cache disque.

La superposition (Pillow) est synchrone → exécutée dans un thread pour ne pas
bloquer la boucle Discord. icon et watermark sont normalement 96×96 ; on
redimensionne le watermark à la taille de l'icon par sécurité avant collage.

Cache sous `banners/xur/` (aligné avec les autres caches d'images du bot,
regroupés sous `banners/<feature>/`). Purgé chaque vendredi à l'arrivée de
Xûr, juste avant régénération."""
from __future__ import annotations

import asyncio
import os
from io import BytesIO

import aiohttp
from PIL import Image

from bot.bungie.client import BUNGIE_BASE
from bot.config import MANIFEST_DIR
from bot.utils.logger import log

ICON_DIR = MANIFEST_DIR / "banners" / "xur"


def purge_xur_cache() -> None:
    """Vide intégralement le cache d'icônes Xûr.

    Appelée juste AVANT régénération (vendredi, arrivée de Xûr) : on supprime
    tous les `.webp` du dossier, recréé au prochain `get_item_icon`. Sans
    danger si le dossier n'existe pas encore."""
    if not ICON_DIR.exists():
        return
    removed = 0
    for entry in ICON_DIR.iterdir():
        if entry.is_file():
            try:
                entry.unlink()
                removed += 1
            except OSError as e:
                log.warning(f"[Xûr] Suppression cache échouée ({entry.name}) : {e}")
    log.info(f"[Xûr] Cache d'icônes purgé ({removed} fichier(s)).")


async def _download(path: str) -> bytes | None:
    """Télécharge une image hébergée sur bungie.net (chemin relatif)."""
    url = f"{BUNGIE_BASE}{path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.warning(f"[Xûr] image → HTTP {resp.status} ({path})")
                    return None
                return await resp.read()
    except aiohttp.ClientError as e:
        log.warning(f"[Xûr] Téléchargement image échoué : {e}")
        return None


def _compose(icon_data: bytes, watermark_data: bytes | None) -> bytes:
    """Superpose le watermark sur l'icon (si fourni). Renvoie du WEBP."""
    base = Image.open(BytesIO(icon_data)).convert("RGBA")

    if watermark_data is not None:
        wm = Image.open(BytesIO(watermark_data)).convert("RGBA")
        if wm.size != base.size:
            wm = wm.resize(base.size, Image.LANCZOS)
        # alpha_composite respecte la transparence du watermark.
        base = Image.alpha_composite(base, wm)

    out = BytesIO()
    base.save(out, format="WEBP", quality=90)
    return out.getvalue()


def _cache_name(item_hash: int, has_watermark: bool) -> str:
    suffix = "wm" if has_watermark else "plain"
    return f"{item_hash}_{suffix}.webp"


async def get_item_icon(
    item_hash: int, icon_path: str | None, watermark_path: str | None
) -> bytes | None:
    """Renvoie les octets WEBP de l'icône composée (cache disque), ou None.

    L'item_hash + présence du watermark forment la clé de cache : si Bungie
    change le watermark d'un item, le hash reste le même mais le contenu est
    quasi stable — le cache se régénère naturellement chaque semaine via la
    purge à l'arrivée de Xûr (purge_xur_cache)."""
    if not icon_path:
        return None

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = ICON_DIR / _cache_name(item_hash, bool(watermark_path))
    if cache_file.exists():
        return cache_file.read_bytes()

    icon_data = await _download(icon_path)
    if icon_data is None:
        return None

    watermark_data = await _download(watermark_path) if watermark_path else None

    composed = await asyncio.to_thread(_compose, icon_data, watermark_data)
    try:
        cache_file.write_bytes(composed)
    except OSError as e:
        log.warning(f"[Xûr] Écriture cache icône échouée : {e}")
    return composed