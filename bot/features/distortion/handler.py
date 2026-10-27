# -*- coding: utf-8 -*-
"""Handler de publication de la Distorsion.

Spécificité vs les autres features : mise à jour par ÉDITION EN PLACE (le
message avance d'un cran chaque heure), donc :
- AUCUN ping (l'édition ne notifie pas ; le topic n'expose d'ailleurs pas de
  rôle configurable) ;
- le message garde sa position dans le salon (pas de repost horaire).

La mécanique (idempotence par `content_hash`, rattrapage, réparation) est
partagée avec les Défis ascendants : cf. bot/publishing/edit_in_place.py."""
from __future__ import annotations

from datetime import datetime, timezone

from bot.publishing import edit_in_place
from bot.features.distortion.view import build_distortion_view, content_hash
from bot.features.distortion import TOPIC

_TAG = "Distortion"


async def publish(bot, state, *, force: bool = False) -> None:
    """Met à jour tous les salons abonnés à l'heure courante.

    `force=True` (utilisé par /refresh) réédite même si le hash est identique."""
    now = datetime.now(timezone.utc)
    await edit_in_place.publish(
        bot, state, TOPIC,
        lambda: build_distortion_view(now),
        content_hash(now),
        force=force, tag=_TAG,
    )


async def refresh(bot, state) -> None:
    """Réactualisation forcée (sans ping) pour /refresh."""
    state.invalidate()
    await publish(bot, state, force=True)


async def on_added(bot, state, guild_id, dest_info: dict) -> None:
    """Nouveau salon configuré → publication initiale immédiate."""
    now = datetime.now(timezone.utc)
    await edit_in_place.on_added(
        bot, state, guild_id, dest_info,
        lambda: build_distortion_view(now),
        content_hash(now),
        tag=_TAG,
    )


async def on_removed(bot, state, guild_id, dest_info: dict) -> None:
    """Salon retiré → suppression du message + purge de l'état."""
    await edit_in_place.on_removed(bot, state, guild_id, dest_info)
