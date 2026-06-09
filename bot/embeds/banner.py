# -*- coding: utf-8 -*-
"""Bandeaux d'activité : téléchargement de la pgcr Bungie, recadrage en bande
au ratio voulu, mise en cache disque.

Le recadrage (Pillow) est synchrone : on l'exécute dans un thread pour ne pas
bloquer la boucle Discord."""
from __future__ import annotations

import asyncio
import os
from io import BytesIO

import aiohttp
from PIL import Image

from bot.bungie.client import BUNGIE_BASE
from bot.config import MANIFEST_DIR
from bot.utils.logger import log

# ⚙️ Ratio largeur:hauteur du bandeau — AJUSTE ICI (1920:590 ≈ 3.254).
#    C'est bien un ratio, pas une résolution : l'image garde sa largeur native.
BANNER_RATIO = 1920 / 590

BANNER_DIR = MANIFEST_DIR / "banners"


def _crop(data: bytes, ratio: float) -> bytes:
    """Recadre une bande centrale au ratio donné. Renvoie du WEBP."""
    img = Image.open(BytesIO(data)).convert("RGB")
    w, h = img.size
    target_h = round(w / ratio)
    if target_h <= h:                       # cas normal : on rogne haut/bas
        top = (h - target_h) // 2
        box = (0, top, w, top + target_h)
    else:                                   # image trop peu haute : on rogne les côtés
        target_w = round(h * ratio)
        left = (w - target_w) // 2
        box = (left, 0, left + target_w, h)
    out = BytesIO()
    img.crop(box).save(out, format="WEBP", quality=90)
    return out.getvalue()


def _cache_name(pgcr_path: str, ratio: float) -> str:
    stem = os.path.splitext(os.path.basename(pgcr_path))[0]
    safe = "".join(c for c in stem if c.isalnum() or c in "-_") or "banner"
    return f"{safe}_{int(ratio * 1000)}.webp"


async def get_banner(pgcr_path: str, ratio: float = BANNER_RATIO) -> bytes | None:
    """Renvoie les octets WEBP du bandeau recadré (cache disque), ou None.

    Le ratio est inclus dans le nom de cache : changer `BANNER_RATIO`
    régénère automatiquement les bandeaux au prochain rendu."""
    if not pgcr_path:
        return None

    BANNER_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = BANNER_DIR / _cache_name(pgcr_path, ratio)
    if cache_file.exists():
        return cache_file.read_bytes()

    url = f"{BUNGIE_BASE}{pgcr_path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.warning(f"[Weekly] pgcr → HTTP {resp.status} ({pgcr_path})")
                    return None
                data = await resp.read()
    except aiohttp.ClientError as e:
        log.warning(f"[Weekly] Téléchargement pgcr échoué : {e}")
        return None

    cropped = await asyncio.to_thread(_crop, data, ratio)
    try:
        cache_file.write_bytes(cropped)
    except OSError as e:
        log.warning(f"[Weekly] Écriture cache bandeau échouée : {e}")
    return cropped