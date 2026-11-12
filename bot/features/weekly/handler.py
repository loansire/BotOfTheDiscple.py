# -*- coding: utf-8 -*-
"""Calcul weekly/daily : secteurs oubliés, raids, donjons.

Deux régimes de message coexistent :
- Secteurs oubliés : MULTI-message (1 message par secteur, cf.
  bot/publishing/registry.py) — le texte cumulé d'un message unique dépassait la
  limite Discord de 4000 caractères une fois les icônes de modificateurs
  ajoutées. Le ping rôle est un message séparé, posté en dernier.
- Raids / Donjons  : MONO-message persistant (cf. bot/publishing/registry.py),
  ping injecté dans la vue. Jamais près du plafond CV2.

Calcul (presenter.py) → base → publication depuis la base. Le contenu porte
la ligne « Actualisation » : il change donc à chaque cadence (quotidienne
pour les secteurs, hebdo pour raids/donjons) et déclenche le repost, même si
les activités sont identiques.

Cache disque des bandeaux : purgé au premier calcul de chaque reset (le
dossier `raid_donjon` est partagé par raids et donjons).

`strict=True` (pipeline au reset) active le garde-fou « données pas prêtes »
(cf. bot/features/weekly/freshness.py) ; la signature validée est mémorisée
dès le calcul."""
from __future__ import annotations

from bot.core.reset import last_reset
from bot.compute import purge_icons_once_per_reset, store
from bot.content.keys import rotation_topic
from bot.content.model import Post
from bot.features.weekly import get_lost_sectors, get_raid_dungeon
from bot.features.weekly.freshness import check_fresh, not_ready, remember
from bot.features.weekly.rotation_presenter import build_rotation_view
from bot.features.weekly.presenter import (
    build_dungeon_view,
    build_lost_sectors_view,
    build_raid_view,
)
from bot.features.weekly.state import weekly_state
from bot.publishing import producers

LOST_SECTOR_TOPIC = "daily_lost_sector"
RAID_TOPIC = "weekly_raid"
DUNGEON_TOPIC = "weekly_dungeon"

# Clés de feature pour la purge du cache d'images (cf. render/banner.py).
_FEATURE_LOST_SECTOR = "secteur_oublie"
_FEATURE_RAID_DUNGEON = "raid_donjon"  # partagé raids + donjons


def _validate(topic: str, sig: list[str], strict: bool) -> None:
    """Garde-fou fraîcheur (strict) puis mémorisation de la signature."""
    if strict:
        check_fresh(weekly_state(), topic, sig)
        remember(weekly_state(), topic, sig)


# ── Secteurs oubliés (multi-message) ────────────────────────────────────


async def _produce_sectors(strict: bool) -> bool:
    sectors = await get_lost_sectors()
    if not sectors:
        if strict:
            not_ready(LOST_SECTOR_TOPIC, "aucun secteur oublié détecté")
        return False
    _validate(LOST_SECTOR_TOPIC, [str(v.activity_hash) for s in sectors for v in s.variants], strict)
    purge_icons_once_per_reset(_FEATURE_LOST_SECTOR)
    messages = await build_lost_sectors_view(sectors)
    await store(Post(LOST_SECTOR_TOPIC, "repost", {"default": messages}, period_start=last_reset()), "Secteurs")
    return True


producers.register(LOST_SECTOR_TOPIC, _produce_sectors)


# ── Raids / Donjons (mono-message) ──────────────────────────────────────


def _producer(topic: str, tag: str, activity_type: str, build_view):
    """Calcul d'un type d'activité ('Raid' / 'Donjon'). Seules les activités
    featured du type portent la signature de fraîcheur (un changement côté
    donjon ne doit pas bloquer le message raid)."""

    async def produce(strict: bool) -> bool:
        groups = await get_raid_dungeon()
        featured = [g for g in groups or [] if g.featured and g.activity_type == activity_type]
        if not featured:
            if strict:
                not_ready(topic, f"aucun {activity_type.lower()} featured détecté")
            return False
        _validate(topic, [g.base_name for g in featured], strict)
        purge_icons_once_per_reset(_FEATURE_RAID_DUNGEON)
        message = await build_view(groups)
        await store(Post(topic, "repost", {"default": [message]}, period_start=last_reset()), tag)
        # Rotation prédictive (bouton du message), calculée avec les mêmes données.
        kind = "dungeon" if activity_type == "Donjon" else "raid"
        rotation = build_rotation_view(kind, groups)
        await store(Post(rotation_topic(kind), "on_demand", {"default": [rotation]}, period_start=last_reset()),
                    f"{tag} (rotation prédictive)")
        return True

    return produce


producers.register(RAID_TOPIC, _producer(RAID_TOPIC, "Raids", "Raid", build_raid_view))
producers.register(DUNGEON_TOPIC, _producer(DUNGEON_TOPIC, "Donjons", "Donjon", build_dungeon_view))
