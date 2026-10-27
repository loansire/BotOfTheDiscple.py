# -*- coding: utf-8 -*-
"""Publication Ada-1 (vendor PERMANENT, inventaire renouvelé au reset du mardi).

Moteur multi-message partagé : cf. bot/publishing/repost.py. Ada-1 n'a ni
fenêtre présent/absent, ni message statut, ni largeIcon : juste le(s)
message(s) de contenu (normalement 1), suivi(s) du ping rôle seul.

Cache d'icônes : purgé à chaque publication (banners/ada/, cadence hebdo) ;
restore / on_added réutilisent le cache existant. Les dossiers étant séparés,
la purge ne touche jamais les caches des autres features."""
from __future__ import annotations

from bot.bungie.reset import last_reset
from bot.features.ada import TOPIC, get_ada
from bot.features.ada.state import ada_state
from bot.features.ada.view import build_ada_view
from bot.publishing.primitives import content_hash
from bot.publishing.repost import Payload, RepostTopic
from bot.render.item_icon import purge_icon_cache


async def _payload(strict: bool) -> Payload | None:
    """Items Ada-1, ou None si rien à publier.

    get_ada renvoie [] à la fois si l'API est indisponible et si le filtre ne
    laisse rien : dans les deux cas on ne poste pas un message vide. Une
    BungieMaintenanceError remonte (hold mode). Le hash inclut l'iso du reset
    → repost hebdo garanti au mardi."""
    items = await get_ada()
    if not items:
        return None
    reset_id = last_reset().isoformat()
    return Payload(items, content_hash([reset_id, *[str(it.item_hash) for it in items]]))


publication = RepostTopic(
    topic=TOPIC,
    tag="Ada-1",
    state=ada_state,
    payload=_payload,
    build_views=build_ada_view,
    purge_cache=lambda: purge_icon_cache("ada"),
    empty_warning="Aucun item récupéré — publication annulée.",
)
