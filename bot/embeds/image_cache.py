# -*- coding: utf-8 -*-
"""Socle commun des caches d'images (bandeaux d'activité, icônes d'items).

- Un sous-dossier par feature sous `banners/<feature>/`, purgeable à la
  cadence propre de la feature (purge_cache).
- Téléchargement depuis bungie.net via la session HTTP partagée (download).
- Lecture du cache ou production + écriture (cached), avec traitement Pillow
  exécuté dans un thread par l'appelant.

Toute erreur (réseau, image corrompue, disque) est logguée et renvoie None :
une image manquante ne doit jamais faire échouer le rendu d'un message."""
from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from bot.bungie.client import BUNGIE_BASE
from bot.config import MANIFEST_DIR
from bot.utils.http import NETWORK_ERRORS, get_session
from bot.utils.logger import log

# Racine commune des caches d'images (un sous-dossier par feature).
IMAGE_CACHE_DIR = MANIFEST_DIR / "banners"


def feature_dir(feature: str) -> Path:
    """Sous-dossier de cache d'une feature (`banners/<feature>/`)."""
    return IMAGE_CACHE_DIR / feature


def purge_cache(feature: str) -> None:
    """Vide intégralement le cache d'images d'une feature.

    Appelée juste AVANT régénération (au reset de la cadence de la feature).
    Sans danger si le dossier n'existe pas encore."""
    directory = feature_dir(feature)
    if not directory.exists():
        return
    removed = 0
    for entry in directory.iterdir():
        if entry.is_file():
            try:
                entry.unlink()
                removed += 1
            except OSError as e:
                log.warning(f"[Image] Suppression cache '{feature}' échouée ({entry.name}) : {e}")
    log.info(f"[Image] Cache '{feature}' purgé ({removed} fichier(s)).")


async def download(path: str, tag: str = "Image") -> bytes | None:
    """Télécharge une image hébergée sur bungie.net (chemin relatif)."""
    url = f"{BUNGIE_BASE}{path}"
    try:
        async with get_session().get(url) as resp:
            if resp.status != 200:
                log.warning(f"[{tag}] image → HTTP {resp.status} ({path})")
                return None
            return await resp.read()
    except NETWORK_ERRORS as e:
        log.warning(f"[{tag}] Téléchargement image échoué ({path}) : {e!r}")
        return None


async def cached(
    cache_file: Path, produce: Callable[[], Awaitable[bytes | None]], tag: str = "Image"
) -> bytes | None:
    """Octets du fichier en cache, sinon `produce()` puis écriture du cache."""
    if cache_file.exists():
        try:
            return cache_file.read_bytes()
        except OSError as e:
            log.warning(f"[{tag}] Lecture cache échouée ({cache_file.name}) : {e}")

    try:
        data = await produce()
    except Exception as e:  # image corrompue (PIL.UnidentifiedImageError…), etc.
        log.warning(f"[{tag}] Génération de {cache_file.name} échouée : {e!r}")
        return None
    if data is None:
        return None

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(data)
    except OSError as e:
        log.warning(f"[{tag}] Écriture cache échouée ({cache_file.name}) : {e}")
    return data
