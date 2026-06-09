# -*- coding: utf-8 -*-
"""Tri et regroupement des activités (logique pure, sans I/O réseau).

Reçoit les listes brutes du profil + un résolveur de hash (le ManifestStore,
ou tout objet exposant `resolve(hash, definition_name) -> dict`)."""
from __future__ import annotations

from .models import ActivityVariant, LostSector, WeeklyActivity

# Hashes de type d'activité (confirmés valides post-Portal)
RAID = 2043403989
DUNGEON = 608898761
LOST_SECTOR = 103143560

WEEKLY_TYPES = {RAID: "Raid", DUNGEON: "Donjon"}


def split_name(name: str) -> tuple[str, str]:
    """'Le Caveau de verre: Maîtrise' → ('Le Caveau de verre', 'Maîtrise').

    Sans suffixe ': ', le label vaut 'Standard' par défaut."""
    if ": " in name:
        base, label = name.split(": ", 1)
        return base.strip(), label.strip()
    return name.strip(), "Standard"


def _norm_light(value) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _def_modifier_hashes(adef: dict) -> list[int]:
    """Extrait les activityModifierHash de la définition d'activité."""
    return [
        m.get("activityModifierHash")
        for m in adef.get("modifiers", [])
        if m.get("activityModifierHash")
    ]


# ── Raids & Donjons ────────────────────────────────────────────────────


def group_raid_dungeon(activities: list[dict], manifest) -> list[WeeklyActivity]:
    """Filtre les raids/donjons et regroupe par nom de base.

    Les variantes (Standard/Maîtrise) sont conservées avec leurs infos
    (lumière, palier de difficulté, modifiers) issues du profil."""
    groups: dict[str, WeeklyActivity] = {}

    for raw in activities:
        ah = raw.get("activityHash")
        adef = manifest.resolve(ah, "DestinyActivityDefinition")
        type_hash = adef.get("activityTypeHash")
        if type_hash not in WEEKLY_TYPES:
            continue

        name = adef.get("displayProperties", {}).get("name", "")
        base, label = split_name(name)

        group = groups.get(base)
        if group is None:
            group = WeeklyActivity(
                base_name=base,
                activity_type=WEEKLY_TYPES[type_hash],
                type_hash=type_hash,
                pgcr_image=adef.get("pgcrImage") or None,
            )
            groups[base] = group

        group.variants.append(ActivityVariant(
            activity_hash=ah,
            label=label,
            recommended_light=_norm_light(raw.get("recommendedLight")),
            difficulty_tier=raw.get("difficultyTier"),
            modifier_hashes=list(raw.get("modifierHashes", [])),
        ))

    return list(groups.values())


# ── Secteurs perdus ────────────────────────────────────────────────────


def collect_lost_sectors(
    interactables: list[dict], manifest, extra: dict | None = None
) -> list[LostSector]:
    """Résout les secteurs perdus via entries[activityInteractableElementIndex].

    Chaque référence (hash, elementIndex) pointe vers UNE entrée précise de la
    définition d'interactable — on n'itère donc PAS toutes les entries (ce qui
    causait le faux dédoublement). `extra` greffe des infos maison par
    activity_hash (str) dans la variante correspondante."""
    extra = extra or {}
    groups: dict[str, LostSector] = {}
    seen: set[int] = set()

    for ref in interactables:
        ih = ref.get("activityInteractableHash")
        idx = ref.get("activityInteractableElementIndex")
        idef = manifest.resolve(ih, "DestinyActivityInteractableDefinition")
        entries = idef.get("entries", [])

        if not isinstance(idx, int) or idx < 0 or idx >= len(entries):
            continue

        ah = entries[idx].get("activityHash")
        if isinstance(ah, list):
            ah = ah[0] if ah else None
        if ah is None:
            continue

        adef = manifest.resolve(ah, "DestinyActivityDefinition")
        if adef.get("activityTypeHash") != LOST_SECTOR:
            continue
        if ah in seen:
            continue
        seen.add(ah)

        name = adef.get("displayProperties", {}).get("name", "")
        base, label = split_name(name)

        group = groups.get(base)
        if group is None:
            dest_def = manifest.resolve(
                adef.get("destinationHash"), "DestinyDestinationDefinition"
            )
            group = LostSector(
                base_name=base,
                destination=dest_def.get("displayProperties", {}).get("name") or None,
                pgcr_image=adef.get("pgcrImage") or None,
            )
            groups[base] = group

        variant = ActivityVariant(
            activity_hash=ah,
            label=label,
            recommended_light=_norm_light(adef.get("activityLightLevel")),
            modifier_hashes=_def_modifier_hashes(adef),
        )
        if str(ah) in extra:
            variant.extra = dict(extra[str(ah)])
        group.variants.append(variant)

    return list(groups.values())