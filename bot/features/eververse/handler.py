# -*- coding: utf-8 -*-
"""Calcul Eververse (items en rotation quotidienne de Tess Everis).

Publication multi-message (cf. bot/publishing/registry.py) : un message par
section (re-découpé si une section dépasse le plafond CV2), puis le ping rôle
seul. Pas de fenêtre présent/absent ni de message statut, contrairement à Xûr.

Calcul : get_eververse() → presenter.build_post() → base. Publication :
lecture de la base (content_source). Cache d'icônes disque : purgé au premier
calcul de chaque reset (banners/eververse/)."""
from __future__ import annotations

from bot.compute import purge_icons_once_per_reset, store
from bot.features.eververse import TOPIC, get_eververse
from bot.features.eververse.presenter import FEATURE, build_post
from bot.publishing import producers

TAG = "Eververse"


async def produce(strict: bool = False) -> bool:
    """Calcule l'Eververse et la range en base. False seulement si l'API est
    indisponible (get_eververse renvoie []) : une section vide est conservée
    (le message affiche un repli)."""
    sections = await get_eververse()
    if not sections:
        return False
    purge_icons_once_per_reset(FEATURE)
    await store(await build_post(sections), TAG)
    return True


producers.register(TOPIC, produce)
