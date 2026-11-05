# -*- coding: utf-8 -*-
"""Publication Ada-1 (vendor PERMANENT, inventaire renouvelé au reset du mardi).

Moteur multi-message partagé : cf. bot/publishing/repost.py. Ada-1 n'a ni
fenêtre présent/absent, ni message statut, ni largeIcon : juste le(s)
message(s) de contenu (normalement 1), suivi(s) du ping rôle seul.

Calcul : get_ada() → presenter.build_post() → base. Publication : lecture
de la base (content_source). Cache d'icônes disque : purgé au premier calcul
de chaque reset (banners/ada/)."""
from __future__ import annotations

from bot.compute import purge_icons_once_per_reset, store
from bot.features.ada import TOPIC, get_ada
from bot.features.ada.presenter import FEATURE, build_post
from bot.features.ada.state import ada_state
from bot.publishing.content_source import stored_payload, stored_views
from bot.publishing.repost import RepostTopic

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


publication = RepostTopic(
    topic=TOPIC,
    tag=TAG,
    state=ada_state,
    payload=stored_payload(TOPIC, produce),
    build_views=stored_views,
    empty_warning="Aucun item récupéré — publication annulée.",
)
