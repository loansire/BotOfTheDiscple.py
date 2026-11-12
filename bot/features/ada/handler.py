# -*- coding: utf-8 -*-
"""Calcul Ada-1 (vendor PERMANENT, inventaire renouvelé au reset du mardi).

Publication (multi-message, cf. bot/publishing/registry.py) : le(s)
message(s) de contenu (normalement 1), suivi(s) du ping rôle seul.

Calcul : get_ada() → presenter.build_post() → base. Publication : lecture
de la base (content_source). Cache d'icônes disque : purgé au premier calcul
de chaque reset (banners/ada/)."""
from __future__ import annotations

from bot.compute import purge_icons_once_per_reset, store
from bot.features.ada import TOPIC, get_ada
from bot.features.ada.presenter import FEATURE, build_post
from bot.publishing import producers

TAG = "Ada-1"


async def produce(strict: bool = False) -> bool:
    """Calcule Ada-1 et le range en base. False si rien à publier : get_ada
    renvoie [] à la fois si l'API est indisponible et si le filtre ne laisse
    rien, et on ne poste pas un message vide. Une BungieMaintenanceError
    remonte (hold mode)."""
    items = await get_ada()
    if not items:
        return False
    purge_icons_once_per_reset(FEATURE)
    await store(await build_post(items), TAG)
    return True


producers.register(TOPIC, produce)
