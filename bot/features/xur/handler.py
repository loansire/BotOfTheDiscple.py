# -*- coding: utf-8 -*-
"""Calcul Xûr : inventaire et statut, rangés en base.

La publication (statut + catégories, arrivée/départ, réparation) vit dans
bot/publishing/xur.py, qui appelle ces étapes via bot/publishing/producers.py.
Cache disque d'icônes : purgé au premier calcul de chaque reset
(banners/xur/), une fois le fetch confirmé : on ne supprime donc jamais une
icône qu'on vient de composer."""
from __future__ import annotations

from bot.compute import purge_icons_once_per_reset, store
from bot.content.keys import XUR_STATUS_TOPIC, XUR_TOPIC
from bot.features.xur import get_xur
from bot.features.xur.presenter import FEATURE, build_post, build_status_post
from bot.publishing import producers


async def produce_vendors() -> bool:
    """Calcule l'inventaire et le range en base. False si indisponible/vide."""
    vendors = await get_xur()
    if not vendors or all(not v.items for v in vendors):
        return False
    purge_icons_once_per_reset(FEATURE)
    await store(await build_post(vendors), "Xûr catégories")
    return True


async def produce_status() -> None:
    """Recalcule le message statut (dates d'arrivée / de départ)."""
    await store(build_status_post(), "Xûr statut")


producers.register(XUR_TOPIC, produce_vendors)
producers.register(XUR_STATUS_TOPIC, produce_status)
