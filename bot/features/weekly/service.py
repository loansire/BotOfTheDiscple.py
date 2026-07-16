# -*- coding: utf-8 -*-
"""Orchestration : manifest.sync → fetch profil → tri → modèles.

API publique de la feature weekly. Ne touche ni à Discord ni au rendu :
renvoie des listes de modèles prêtes à être présentées (lot ultérieur)."""
from __future__ import annotations

import json

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.config import RESOURCES_DIR
from bot.utils.logger import log

from . import filters
from .models import LostSector, WeeklyActivity

# Greffe maison (vide par défaut) : { "<activity_hash>": { ... } }
EXTRA_PATH = RESOURCES_DIR / "Weekly" / "lost_sector_extra.json"

# Activités "permanentes" (contenu le plus récent, toujours actif) : liste de
# hashes (str) affichés dans une sous-section dédiée. Maintenu hors code.
PERMANENT_PATH = RESOURCES_DIR / "Weekly" / "permanent_activities.json"


def _load_extra() -> dict:
    if EXTRA_PATH.exists():
        try:
            with open(EXTRA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"[Weekly] lost_sector_extra.json illisible : {e}")
    return {}


def _load_permanent() -> set[int]:
    """Hashes d'activités permanentes (set d'int). Vide si fichier absent/illisible."""
    if PERMANENT_PATH.exists():
        try:
            with open(PERMANENT_PATH, "r", encoding="utf-8") as f:
                return {int(h) for h in json.load(f)}
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
            log.warning(f"[Weekly] permanent_activities.json illisible : {e}")
    return set()


async def _profile_block() -> dict | None:
    """S'assure que le manifest est à jour puis renvoie activities.data."""
    await manifest.sync()
    data = await bungie.get_character_activities()
    if not data:
        log.error("[Weekly] Profil personnage indisponible.")
        return None
    return data.get("activities", {}).get("data", {})


async def get_raid_dungeon() -> list[WeeklyActivity]:
    """Raids + donjons disponibles, regroupés par nom de base."""
    block = await _profile_block()
    if block is None:
        return []
    return filters.group_raid_dungeon(
        block.get("availableActivities", []),
        manifest,
        permanent_hashes=_load_permanent(),
    )


async def get_lost_sectors() -> list[LostSector]:
    """Secteurs perdus du jour (1 par planète, Expert/Maîtrise).

    Les 2 surcharges élémentaires de la semaine (globales) sont lues sur
    availableActivities (activité globale des surges) puis injectées dans chaque
    variante, en plus de la surcharge d'arme propre au secteur (cf.
    filters.collect_lost_sectors)."""
    block = await _profile_block()
    if block is None:
        return []
    elemental_surges = filters.weekly_elemental_surges(
        block.get("availableActivities", [])
    )
    return filters.collect_lost_sectors(
        block.get("availableActivityInteractables", []),
        manifest,
        extra=_load_extra(),
        elemental_surges=elemental_surges,
    )