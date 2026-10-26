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

from PIL import Image

from bot.embeds import image_cache

# Dossier Xûr (conservé pour les icônes de vendor, spécifiques à Xûr).
ICON_DIR = image_cache.feature_dir("xur")

# ⚙️ Largeur cible commune des en-têtes de vendor (px). La hauteur suit le
#    ratio natif de chaque image (aucun rognage). Incluse dans le nom de cache :
#    changer cette valeur régénère automatiquement les en-têtes au prochain rendu.
VENDOR_ICON_WIDTH = 246


# Purge du cache d'icônes d'une feature (avant régénération à sa cadence).
purge_icon_cache = image_cache.purge_cache


def purge_xur_cache() -> None:
    """Purge le cache d'icônes Xûr (raccourci historique). Appelée le vendredi
    à l'arrivée de Xûr, juste avant régénération."""
    purge_icon_cache("xur")


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

    cache_file = image_cache.feature_dir(feature) / _cache_name(item_hash, bool(watermark_path))

    async def produce() -> bytes | None:
        # icône et watermark téléchargés en parallèle.
        if watermark_path:
            icon_data, watermark_data = await asyncio.gather(
                image_cache.download(icon_path, "Icon"),
                image_cache.download(watermark_path, "Icon"),
            )
        else:
            icon_data, watermark_data = await image_cache.download(icon_path, "Icon"), None
        if icon_data is None:
            return None
        return await asyncio.to_thread(_compose, icon_data, watermark_data)

    return await image_cache.cached(cache_file, produce, "Icon")


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

    fname = _vendor_cache_name(vendor_key, VENDOR_ICON_WIDTH)

    async def produce() -> bytes | None:
        data = await image_cache.download(icon_path, "Xûr")
        if data is None:
            return None
        return await asyncio.to_thread(_resize_to_width, data, VENDOR_ICON_WIDTH)

    data = await image_cache.cached(ICON_DIR / fname, produce, "Xûr")
    return (data, fname) if data is not None else None
