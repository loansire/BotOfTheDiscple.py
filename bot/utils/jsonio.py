# -*- coding: utf-8 -*-
"""Lecture / écriture JSON sur disque, partagées par tous les états et caches.

- `load_json` ne lève jamais : fichier absent ou corrompu → `default` (avec un
  warning dans le second cas), pour qu'un JSON tronqué n'empêche pas un cog de
  charger.
- `save_json` est ATOMIQUE : écriture dans un fichier temporaire voisin puis
  `os.replace`. Un crash en pleine écriture laisse l'ancien fichier intact au
  lieu d'un JSON à moitié écrit."""
from __future__ import annotations

import json
import os
from pathlib import Path

from bot.utils.logger import log


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        log.warning(f"[JSON] {path.name} illisible ({e}) — valeur par défaut utilisée.")
        return default


def save_json(path: Path, data, *, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


# Cache mémoire invalidé par la date de modification du fichier : pour les
# fichiers relus très souvent (autocomplétion, boucles à la minute) mais
# rarement modifiés. La valeur renvoyée est PARTAGÉE : l'appelant qui veut la
# modifier doit la copier.
_mtime_cache: dict[Path, tuple[int, object]] = {}


def load_json_cached(path: Path, default=None):
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return default
    hit = _mtime_cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    data = load_json(path, default)
    _mtime_cache[path] = (mtime, data)
    return data
