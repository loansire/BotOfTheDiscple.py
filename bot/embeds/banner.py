# -*- coding: utf-8 -*-
"""Bandeaux d'activité : téléchargement de la pgcr Bungie, recadrage en bande
au ratio voulu, redimensionnement, mise en cache disque.

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
#    C'est bien un ratio, pas une résolution : l'image garde sa largeur native
#    AVANT redimensionnement.
BANNER_RATIO = 1920 / 590

# ⚙️ Facteur de redimensionnement appliqué APRÈS le recadrage en bande.
#    1/3 → image 3× plus petite (largeur et hauteur divisées par 3).
#    1.0 → aucune réduction. Manipulable librement pour les tests.
BANNER_SCALE = 1 / 4

BANNER_DIR = MANIFEST_DIR / "banners"


def _crop(data: bytes, ratio: float, scale: float) -> bytes:
    """Recadre une bande centrale au ratio donné, puis réduit par `scale`.
    Renvoie du WEBP."""
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
    cropped = img.crop(box)

    if scale != 1.0:                        # redimensionnement final
        cw, ch = cropped.size
        new_size = (max(1, round(cw * scale)), max(1, round(ch * scale)))
        cropped = cropped.resize(new_size, Image.LANCZOS)

    out = BytesIO()
    cropped.save(out, format="WEBP", quality=90)
    return out.getvalue()


def _cache_name(pgcr_path: str, ratio: float, scale: float) -> str:
    stem = os.path.splitext(os.path.basename(pgcr_path))[0]
    safe = "".join(c for c in stem if c.isalnum() or c in "-_") or "banner"
    return f"{safe}_{int(ratio * 1000)}_{int(scale * 1000)}.webp"


async def get_banner(
    pgcr_path: str, ratio: float = BANNER_RATIO, scale: float = BANNER_SCALE
) -> bytes | None:
    """Renvoie les octets WEBP du bandeau recadré et redimensionné (cache
    disque), ou None.

    Le ratio ET le scale sont inclus dans le nom de cache : changer
    `BANNER_RATIO` ou `BANNER_SCALE` régénère automatiquement les bandeaux
    au prochain rendu."""
    if not pgcr_path:
        return None

    BANNER_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = BANNER_DIR / _cache_name(pgcr_path, ratio, scale)
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

    cropped = await asyncio.to_thread(_crop, data, ratio, scale)
    try:
        cache_file.write_bytes(cropped)
    except OSError as e:
        log.warning(f"[Weekly] Écriture cache bandeau échouée : {e}")
    return cropped