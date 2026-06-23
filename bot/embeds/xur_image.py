# -*- coding: utf-8 -*-
"""Icônes d'items Xûr : téléchargement de l'icon Bungie, superposition de
l'iconWatermark (si présent), mise en cache disque.

La superposition (Pillow) est synchrone → exécutée dans un thread pour ne pas
bloquer la boucle Discord. icon et watermark sont normalement 96×96 ; on
redimensionne le watermark à la taille de l'icon par sécurité avant collage.

Cache sous `banners/xur/` (aligné avec les autres caches d'images du bot,
regroupés sous `banners/<feature>/`). Purgé chaque vendredi à l'arrivée de
Xûr, juste avant régénération.

Icônes de vendor (largeIcon) : on part du principe que c'est toujours la même
image par catégorie, mais leurs dimensions natives diffèrent. On les
redimensionne donc à une LARGEUR FIXE commune (hauteur proportionnelle, aucun
rognage ni déformation) pour homogénéiser les en-têtes. Sortie en WEBP, mise
en cache dans le même dossier sous un nom préfixé `vendor_`."""
from __future__ import annotations

import asyncio
from io import BytesIO

import aiohttp
from PIL import Image

from bot.bungie.client import BUNGIE_BASE
from bot.config import MANIFEST_DIR
from bot.utils.logger import log

ICON_DIR = MANIFEST_DIR / "banners" / "xur"

# ⚙️ Largeur cible commune des en-têtes de vendor (px). La hauteur suit le
#    ratio natif de chaque image (aucun rognage). Incluse dans le nom de cache :
#    changer cette valeur régénère automatiquement les en-têtes au prochain rendu.
VENDOR_ICON_WIDTH = 246


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


# ── Icône d'en-tête de vendor (largeIcon) ───────────────────────────────


def _resize_to_width(data: bytes, target_width: int) -> bytes:
    """Redimensionne une image à `target_width` (hauteur proportionnelle).

    Aucun rognage ni déformation : la hauteur est calculée pour préserver le
    ratio natif. Agrandit aussi les images plus petites que la cible (pour
    homogénéiser). Renvoie du WEBP."""
    img = Image.open(BytesIO(data)).convert("RGBA")
    w, h = img.size
    if w != target_width and w > 0:
        target_height = max(1, round(h * target_width / w))
        img = img.resize((target_width, target_height), Image.LANCZOS)

    out = BytesIO()
    img.save(out, format="WEBP", quality=90)
    return out.getvalue()


def _vendor_cache_name(vendor_key: str, width: int) -> str:
    """Nom de cache d'une en-tête de vendor (largeur incluse → régénération
    auto si VENDOR_ICON_WIDTH change). Sortie toujours en WEBP."""
    return f"vendor_{vendor_key}_{width}.webp"


async def get_vendor_icon(
    vendor_key: str, icon_path: str | None
) -> tuple[bytes, str] | None:
    """Renvoie (octets WEBP, nom_de_fichier) de l'en-tête d'un vendor, ou None.

    Téléchargement puis redimensionnement à une LARGEUR FIXE commune
    (VENDOR_ICON_WIDTH), hauteur proportionnelle — aucun rognage. Mise en cache
    disque sous `banners/xur/vendor_<key>_<width>.webp`, purgée comme le reste
    à l'arrivée de Xûr (purge_xur_cache).

    Le nom de fichier est renvoyé pour la référence `attachment://` côté rendu."""
    if not icon_path:
        return None

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    fname = _vendor_cache_name(vendor_key, VENDOR_ICON_WIDTH)
    cache_file = ICON_DIR / fname
    if cache_file.exists():
        return cache_file.read_bytes(), fname

    data = await _download(icon_path)
    if data is None:
        return None

    resized = await asyncio.to_thread(_resize_to_width, data, VENDOR_ICON_WIDTH)
    try:
        cache_file.write_bytes(resized)
    except OSError as e:
        log.warning(f"[Xûr] Écriture cache icône vendor échouée : {e}")
    return resized, fname