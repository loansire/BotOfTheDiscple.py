# -*- coding: utf-8 -*-
"""Icônes d'items : téléchargement de l'icon Bungie, superposition de
l'iconWatermark (si présent), mise en cache disque.

La superposition (Pillow) est synchrone → exécutée dans un thread pour ne pas
bloquer la boucle Discord. icon et watermark sont normalement 96×96 ; on
redimensionne le watermark à la taille de l'icon par sécurité avant collage.

Cache isolé PAR FEATURE sous `banners/<feature>/` (aligné avec les autres caches
d'images du bot). La composition d'icône est partagée entre features (Xûr,
Eververse…) : `get_item_icon` prend un paramètre `feature` (défaut "xur") qui
choisit le sous-dossier de cache. `purge_icon_cache(feature)` purge un cache
donné (purge_xur_cache = raccourci historique sur "xur").

Icônes de vendor (largeIcon) : spécifiques à Xûr (en-tête de catégorie), gardées
telles quelles sous `banners/xur/`."""
from __future__ import annotations

import asyncio
from io import BytesIO

import aiohttp
from PIL import Image

from bot.bungie.client import BUNGIE_BASE
from bot.config import MANIFEST_DIR
from bot.utils.logger import log

# Racine commune des caches d'icônes (un sous-dossier par feature).
ICON_BASE_DIR = MANIFEST_DIR / "banners"

# Dossier Xûr (conservé pour les icônes de vendor, spécifiques à Xûr).
ICON_DIR = ICON_BASE_DIR / "xur"

# ⚙️ Largeur cible commune des en-têtes de vendor (px). La hauteur suit le
#    ratio natif de chaque image (aucun rognage). Incluse dans le nom de cache :
#    changer cette valeur régénère automatiquement les en-têtes au prochain rendu.
VENDOR_ICON_WIDTH = 246


def _icon_dir(feature: str):
    """Sous-dossier de cache d'icônes d'une feature (`banners/<feature>/`)."""
    return ICON_BASE_DIR / feature


def purge_icon_cache(feature: str) -> None:
    """Vide intégralement le cache d'icônes d'une feature.

    Appelée juste AVANT régénération (au reset de la cadence de la feature) :
    on supprime tous les `.webp` du sous-dossier, recréé au prochain
    `get_item_icon`. Sans danger si le dossier n'existe pas encore."""
    directory = _icon_dir(feature)
    if not directory.exists():
        return
    removed = 0
    for entry in directory.iterdir():
        if entry.is_file():
            try:
                entry.unlink()
                removed += 1
            except OSError as e:
                log.warning(f"[Icon] Suppression cache '{feature}' échouée ({entry.name}) : {e}")
    log.info(f"[Icon] Cache '{feature}' purgé ({removed} fichier(s)).")


def purge_xur_cache() -> None:
    """Purge le cache d'icônes Xûr (raccourci historique). Appelée le vendredi
    à l'arrivée de Xûr, juste avant régénération."""
    purge_icon_cache("xur")


async def _download(path: str) -> bytes | None:
    """Télécharge une image hébergée sur bungie.net (chemin relatif)."""
    url = f"{BUNGIE_BASE}{path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.warning(f"[Icon] image → HTTP {resp.status} ({path})")
                    return None
                return await resp.read()
    except aiohttp.ClientError as e:
        log.warning(f"[Icon] Téléchargement image échoué : {e}")
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
    item_hash: int,
    icon_path: str | None,
    watermark_path: str | None,
    feature: str = "xur",
) -> bytes | None:
    """Renvoie les octets WEBP de l'icône composée (cache disque), ou None.

    `feature` choisit le sous-dossier de cache (`banners/<feature>/`) : "xur",
    "eververse"… Le comportement par défaut ("xur") est inchangé pour les
    appelants historiques.

    L'item_hash + présence du watermark forment la clé de cache : si Bungie
    change le watermark d'un item, le hash reste le même mais le contenu est
    quasi stable — le cache se régénère naturellement à chaque purge de cadence
    (arrivée de Xûr, reset quotidien Eververse…)."""
    if not icon_path:
        return None

    directory = _icon_dir(feature)
    directory.mkdir(parents=True, exist_ok=True)
    cache_file = directory / _cache_name(item_hash, bool(watermark_path))
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
        log.warning(f"[Icon] Écriture cache icône échouée : {e}")
    return composed


# ── Icône d'en-tête de vendor (largeIcon) — spécifique Xûr ──────────────


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