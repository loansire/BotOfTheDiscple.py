# -*- coding: utf-8 -*-
"""Publication weekly/daily : secteurs oubliés, raids, donjons.

Deux régimes de message coexistent :
- Secteurs oubliés : MULTI-message (1 message par secteur, cf.
  bot/publishing/repost.py) — le texte cumulé d'un message unique dépassait la
  limite Discord de 4000 caractères une fois les icônes de modificateurs
  ajoutées. Le ping rôle est un message séparé, posté en dernier.
- Raids / Donjons  : MONO-message persistant (cf. bot/publishing/single.py),
  ping injecté dans la vue. Jamais près du plafond CV2.

Le hash de contenu inclut l'identifiant du reset courant : un repost a lieu à
chaque cadence (quotidienne pour les secteurs, hebdo pour raids/donjons) même
si les noms d'activités sont identiques, ce qui garde à jour la ligne
« Prochaine actualisation ». Dans une même période le hash est stable.

Cache d'images : les secteurs purgent leur cache à chaque publication. Raids
et donjons PARTAGENT le dossier `raid_donjon` : publish_raid_dungeon le purge
une seule fois AVANT de publier les deux types (une purge entre les deux
effacerait un bandeau fraîchement généré).

`strict=True` (pipeline au reset) active le garde-fou « données pas prêtes »
(cf. bot/features/weekly/freshness.py)."""
from __future__ import annotations

from bot.bungie.reset import last_reset
from bot.features.weekly import get_lost_sectors, get_raid_dungeon
from bot.features.weekly.freshness import check_fresh, not_ready, remember
from bot.features.weekly.state import weekly_slot, weekly_state
from bot.features.weekly.view import (
    build_dungeon_view,
    build_lost_sectors_view,
    build_raid_view,
)
from bot.publishing.primitives import content_hash
from bot.publishing.repost import Payload, RepostTopic
from bot.publishing.single import SingleTopic
from bot.render.banner import purge_banner_cache

LOST_SECTOR_TOPIC = "daily_lost_sector"
RAID_TOPIC = "weekly_raid"
DUNGEON_TOPIC = "weekly_dungeon"

# Clés de feature pour la purge du cache d'images (cf. render/banner.py).
_FEATURE_LOST_SECTOR = "secteur_oublie"
_FEATURE_RAID_DUNGEON = "raid_donjon"  # partagé raids + donjons


# ── Secteurs oubliés (multi-message) ────────────────────────────────────


async def _sectors_payload(strict: bool) -> Payload | None:
    sectors = await get_lost_sectors()
    if not sectors:
        if strict:
            not_ready(LOST_SECTOR_TOPIC, "aucun secteur oublié détecté")
        return None
    sig = [str(v.activity_hash) for s in sectors for v in s.variants]
    if strict:
        check_fresh(weekly_state(), LOST_SECTOR_TOPIC, sig)
    return Payload(sectors, content_hash([last_reset().isoformat(), *sig]), sig)


lost_sectors = RepostTopic(
    topic=LOST_SECTOR_TOPIC,
    tag="Secteurs",
    state=lambda: weekly_slot(LOST_SECTOR_TOPIC),
    payload=_sectors_payload,
    build_views=build_lost_sectors_view,
    purge_cache=lambda: purge_banner_cache(_FEATURE_LOST_SECTOR),
    on_published=lambda p: remember(weekly_state(), LOST_SECTOR_TOPIC, p.sig),
)


# ── Raids / Donjons (mono-message) ──────────────────────────────────────


def _activity_payload(topic: str, activity_type: str):
    """Fabrique le payload d'un type d'activité ('Raid' / 'Donjon').

    Les données renvoyées sont la liste COMPLÈTE (raids + donjons) : le builder
    filtre par type. Le hash ne porte QUE sur les activités featured du type
    (un changement côté donjon ne doit pas forcer le repost du message raid)."""

    async def payload(strict: bool) -> Payload | None:
        groups = await get_raid_dungeon()
        featured = [g for g in groups or [] if g.featured and g.activity_type == activity_type]
        if not featured:
            if strict:
                not_ready(topic, f"aucun {activity_type.lower()} featured détecté")
            return None
        sig = [g.base_name for g in featured]
        if strict:
            check_fresh(weekly_state(), topic, sig)
        return Payload(groups, content_hash([last_reset().isoformat(), topic, *sig]), sig)

    return payload


def _single(topic: str, tag: str, activity_type: str, build_view) -> SingleTopic:
    return SingleTopic(
        topic=topic,
        tag=tag,
        state=weekly_state,
        payload=_activity_payload(topic, activity_type),
        build_view=build_view,
        purge_cache=lambda: purge_banner_cache(_FEATURE_RAID_DUNGEON),
        on_published=lambda p: remember(weekly_state(), topic, p.sig),
    )


raids = _single(RAID_TOPIC, "Raids", "Raid", build_raid_view)
dungeons = _single(DUNGEON_TOPIC, "Donjons", "Donjon", build_dungeon_view)


async def publish_raid_dungeon(bot, *, ping: bool = True, strict: bool = False) -> None:
    """Reset hebdo (mardi) : purge le cache de bandeaux raids/donjons UNE seule
    fois PUIS publie raids puis donjons."""
    purge_banner_cache(_FEATURE_RAID_DUNGEON)
    await raids.publish(bot, ping=ping, strict=strict)
    await dungeons.publish(bot, ping=ping, strict=strict)
