# -*- coding: utf-8 -*-
"""Orchestration : manifest.sync → fetch profil → tri → modèles.

API publique de la feature weekly. Ne touche ni à Discord ni au rendu :
renvoie des listes de modèles prêtes à être présentées (lot ultérieur)."""
from __future__ import annotations

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.bungie.reset import last_reset
from bot.config import RESOURCES_DIR
from bot.utils.jsonio import load_json
from bot.utils.logger import log

from . import filters
from .models import LostSector, WeeklyActivity

# Greffe maison (vide par défaut) : { "<activity_hash>": { ... } }
EXTRA_PATH = RESOURCES_DIR / "Weekly" / "lost_sector_extra.json"

# Activités "permanentes" (contenu le plus récent, toujours actif) : liste de
# hashes (str) affichés dans une sous-section dédiée. Maintenu hors code.
PERMANENT_PATH = RESOURCES_DIR / "Weekly" / "permanent_activities.json"


# Reset pour lequel une resynchro forcée du manifest a déjà été tentée (une
# seule par reset : inutile de retélécharger 20 Mo à chaque poll si Bungie
# expose réellement des hashes absents de son propre manifest).
_forced_resync_reset: str | None = None


def _load_extra() -> dict:
    data = load_json(EXTRA_PATH, {})
    return data if isinstance(data, dict) else {}


def _load_permanent() -> set[int]:
    """Hashes d'activités permanentes (set d'int). Vide si fichier absent/illisible."""
    try:
        return {int(h) for h in load_json(PERMANENT_PATH, []) or []}
    except (ValueError, TypeError) as e:
        log.warning(f"[Weekly] permanent_activities.json illisible : {e}")
        return set()


async def _ensure_resolvable(available: list[dict]) -> None:
    """Garde-fou manifest : si des activités du profil sont introuvables dans
    les définitions locales, on force UNE resynchro complète du manifest
    (par reset). S'il en reste ensuite, on le logue explicitement au lieu de
    les ignorer en silence."""
    global _forced_resync_reset
    unresolved = filters.unresolved_hashes(available, manifest)
    if not unresolved:
        return

    reset_id = last_reset().isoformat()
    if _forced_resync_reset != reset_id:
        _forced_resync_reset = reset_id
        log.warning(
            f"[Weekly] {len(unresolved)} activité(s) introuvable(s) dans le manifest "
            "local — resynchro forcée."
        )
        manifest.mark_stale()
        await manifest.sync()
        await manifest.preload("DestinyActivityDefinition")
        unresolved = filters.unresolved_hashes(available, manifest)

    if unresolved:
        log.warning(
            f"[Weekly] {len(unresolved)} activité(s) toujours non résolue(s) "
            f"(ignorées) : {unresolved[:10]}"
        )


async def _profile_block() -> dict | None:
    """S'assure que le manifest est à jour puis renvoie activities.data."""
    await manifest.sync()
    await manifest.preload("DestinyActivityDefinition")
    data = await bungie.get_character_activities()
    if not data:
        log.error("[Weekly] Profil personnage indisponible.")
        return None
    block = data.get("activities", {}).get("data", {})
    await _ensure_resolvable(block.get("availableActivities", []))
    return block


async def get_raid_dungeon() -> list[WeeklyActivity]:
    """Raids + donjons disponibles, regroupés par nom de base."""
    block = await _profile_block()
    if block is None:
        return []
    groups = filters.group_raid_dungeon(
        block.get("availableActivities", []),
        manifest,
        permanent_hashes=_load_permanent(),
    )
    # Diagnostic : ce qui est détecté comme featured (signal = challenges
    # actifs). Indispensable pour comprendre une activité « manquante ».
    for g in groups:
        if g.featured or g.permanent:
            log.debug(
                f"[Weekly] {g.activity_type} featured={g.featured} "
                f"permanent={g.permanent} : {g.base_name} "
                f"(challenges={[v.active_challenges for v in g.variants]})"
            )
    return groups


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