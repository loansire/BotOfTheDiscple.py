# -*- coding: utf-8 -*-
"""Publication Eververse (items en rotation quotidienne de Tess Everis).

Moteur multi-message partagé : cf. bot/publishing/repost.py. Un message par
section (re-découpé si une section dépasse le plafond CV2), puis le ping rôle
seul. Pas de fenêtre présent/absent ni de message statut, contrairement à Xûr.

Cache d'icônes : purgé à chaque publication (banners/eververse/, cadence
quotidienne) ; restore / on_added réutilisent le cache existant."""
from __future__ import annotations

from bot.bungie.reset import last_reset
from bot.features.eververse import TOPIC, get_eververse
from bot.features.eververse.state import eververse_state
from bot.features.eververse.view import build_eververse_views
from bot.publishing.primitives import content_hash
from bot.publishing.repost import Payload, RepostTopic
from bot.render.item_icon import purge_icon_cache


async def _payload(strict: bool) -> Payload | None:
    """Sections Eververse, ou None si l'API est indisponible.

    Une section sans item est conservée (le rendu affiche un repli) : seul un
    échec API total (get_eververse renvoie []) annule la publication. Le hash
    inclut l'iso du reset → repost quotidien garanti."""
    sections = await get_eververse()
    if not sections:
        return None
    parts = [last_reset().isoformat()]
    parts += [str(item.item_hash) for section in sections for item in section.items]
    return Payload(sections, content_hash(parts))


publication = RepostTopic(
    topic=TOPIC,
    tag="Eververse",
    state=eververse_state,
    payload=_payload,
    build_views=build_eververse_views,
    purge_cache=lambda: purge_icon_cache("eververse"),
    empty_warning="Aucun item récupéré — publication annulée.",
)
