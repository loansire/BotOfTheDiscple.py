# -*- coding: utf-8 -*-
"""Handler de publication des Défis ascendants.

Comme la Distorsion : mise à jour par ÉDITION EN PLACE (le message avance d'un
cran à chaque reset hebdo), donc :
- AUCUN ping (l'édition ne notifie pas ; le topic n'expose pas de rôle) ;
- le message garde sa position dans le salon (pas de repost hebdo).

La mécanique (idempotence par `content_hash` de semaine, rattrapage,
réparation) est partagée avec la Distorsion : cf. bot/discord/edit_in_place.py.

Source de vérité : la formule déterministe. POUR BRANCHER LE CONTRAT LIVE de
Petra (composant 402) : récupérer l'itemHash du contrat vendu et le passer en
`hash_contrat=` à build_ascendant_view() ET content_hash() ci-dessous. Le reste
(édition/rattrapage/réparation) ne change pas — resolve() gère l'override et
loggue toute divergence avec la formule."""
from __future__ import annotations

from datetime import datetime, timezone

from bot.discord import edit_in_place
from bot.embeds.ascendant import build_ascendant_view, content_hash
from bot.features.ascendant import TOPIC
from bot.features.ascendant.service import fetch_contrat_hash, reset_cache

_TAG = "Ascendant"


async def publish(bot, state, *, force: bool = False) -> None:
    """Met à jour tous les salons abonnés à la semaine courante.

    `force=True` réédite même si le hash est identique."""
    now = datetime.now(timezone.utc)
    contrat = await fetch_contrat_hash(now)  # None → repli formule (mémoïsé/semaine)
    await edit_in_place.publish(
        bot, state, TOPIC,
        lambda: build_ascendant_view(now, contrat),
        content_hash(now, contrat),
        force=force, tag=_TAG,
    )


async def refresh(bot, state) -> None:
    """Réactualisation forcée (sans ping). Re-pull le contrat live au passage."""
    reset_cache()
    state.invalidate()
    await publish(bot, state, force=True)


async def on_added(bot, state, guild_id, dest_info: dict) -> None:
    """Nouveau salon configuré → publication initiale immédiate."""
    now = datetime.now(timezone.utc)
    contrat = await fetch_contrat_hash(now)
    await edit_in_place.on_added(
        bot, state, guild_id, dest_info,
        lambda: build_ascendant_view(now, contrat),
        content_hash(now, contrat),
        tag=_TAG,
    )


async def on_removed(bot, state, guild_id, dest_info: dict) -> None:
    """Salon retiré → suppression du message + purge de l'état."""
    await edit_in_place.on_removed(bot, state, guild_id, dest_info)
