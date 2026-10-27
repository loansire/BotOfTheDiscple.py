# -*- coding: utf-8 -*-
"""Bandeaux d'activité : téléchargement de la pgcr Bungie, recadrage en bande
au ratio voulu, redimensionnement, mise en cache disque.

Le recadrage (Pillow) est synchrone : on l'exécute dans un thread pour ne pas
bloquer la boucle Discord.

Cache isolé PAR FEATURE sous `banners/<feature>/` (ex. `banners/secteur_oublie/`,
`banners/raid_donjon/`). Cette séparation permet de purger le cache d'une
feature à SA propre cadence sans toucher aux autres : un reset quotidien
(secteurs) ne doit jamais effacer les bandeaux hebdo (raids/donjons)."""
from __future__ import annotations

import asyncio
import os
from io import BytesIO

from PIL import Image

from bot.render import image_cache

# ⚙️ Ratio largeur:hauteur du bandeau — AJUSTE ICI (1920:590 ≈ 3.254).
#    C'est bien un ratio, pas une résolution : l'image garde sa largeur native
#    AVANT redimensionnement.
BANNER_RATIO = 1920 / 590

# ⚙️ Facteur de redimensionnement appliqué APRÈS le recadrage en bande.
#    1/3 → image 3× plus petite (largeur et hauteur divisées par 3).
#    1.0 → aucune réduction. Manipulable librement pour les tests.
BANNER_SCALE = 1 / 4

# Purge du cache de bandeaux d'une feature (avant régénération à sa cadence).
purge_banner_cache = image_cache.purge_cache


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
    pgcr_path: str,
    feature: str,
    ratio: float = BANNER_RATIO,
    scale: float = BANNER_SCALE,
) -> bytes | None:
    """Renvoie les octets WEBP du bandeau recadré et redimensionné (cache
    disque sous `banners/<feature>/`), ou None.

    `feature` isole le cache (ex. "secteur_oublie", "raid_donjon") pour
    permettre une purge ciblée par cadence.

    Le ratio ET le scale sont inclus dans le nom de cache : changer
    `BANNER_RATIO` ou `BANNER_SCALE` régénère automatiquement les bandeaux
    au prochain rendu."""
    if not pgcr_path:
        return None

    cache_file = image_cache.feature_dir(feature) / _cache_name(pgcr_path, ratio, scale)

    async def produce() -> bytes | None:
        data = await image_cache.download(pgcr_path, "Banner")
        if data is None:
            return None
        return await asyncio.to_thread(_crop, data, ratio, scale)

    return await image_cache.cached(cache_file, produce, "Banner")
