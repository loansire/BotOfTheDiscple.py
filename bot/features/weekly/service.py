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


def _load_extra() -> dict:
    if EXTRA_PATH.exists():
        try:
            with open(EXTRA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"[Weekly] lost_sector_extra.json illisible : {e}")
    return {}


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
    return filters.group_raid_dungeon(block.get("availableActivities", []), manifest)


async def get_lost_sectors() -> list[LostSector]:
    """Secteurs perdus du jour (1 par planète, Expert/Maîtrise)."""
    block = await _profile_block()
    if block is None:
        return []
    return filters.collect_lost_sectors(
        block.get("availableActivityInteractables", []),
        manifest,
        extra=_load_extra(),
    )