# -*- coding: utf-8 -*-
"""Publication Eververse (items en rotation quotidienne de Tess Everis).

Moteur multi-message partagé : cf. bot/publishing/repost.py. Un message par
section (re-découpé si une section dépasse le plafond CV2), puis le ping rôle
seul. Pas de fenêtre présent/absent ni de message statut, contrairement à Xûr.

Calcul : get_eververse() → presenter.build_post() → base. Publication :
lecture de la base (content_source). Cache d'icônes disque : purgé au premier
calcul de chaque reset (banners/eververse/)."""
from __future__ import annotations

from bot.compute import purge_icons_once_per_reset, store
from bot.features.eververse import TOPIC, get_eververse
from bot.features.eververse.presenter import FEATURE, build_post
from bot.features.eververse.state import eververse_state
from bot.publishing.content_source import stored_payload, stored_views
from bot.publishing.repost import RepostTopic

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


publication = RepostTopic(
    topic=TOPIC,
    tag=TAG,
    state=eververse_state,
    payload=stored_payload(TOPIC, produce),
    build_views=stored_views,
    empty_warning="Aucun item récupéré — publication annulée.",
)
