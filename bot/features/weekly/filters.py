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


# ── Surcharges (surges) des secteurs oubliés ────────────────────────────
# Un secteur oublié affiche 1 surcharge d'ARME (spécifique au secteur, présente
# telle quelle dans sa définition statique) + 2 surcharges ÉLÉMENTAIRES de la
# semaine (globales, communes à toutes les activités du jour).
#
# La déf statique du secteur liste TOUTES les surges élémentaires possibles :
# on ne peut donc pas en déduire les 2 actives. Celles-ci se lisent sur
# l'activité globale GLOBAL_SURGE_ACTIVITY d'availableActivities (composant 204),
# via ses modifierHashes.
#
# NB : ces ensembles servent à CLASSIFIER les modificateurs (data). Le mapping
# hash → emoji vit à part dans embeds/weekly.py (_LS_MODIFIER_EMOJIS) ;
# duplication assumée, factoriser coupleraient feature → embeds (mauvais sens de
# dépendance). Les commentaires rappellent l'abréviation d'emoji correspondante
# pour la traçabilité entre les deux tables.

# Activité « porteuse » des surges élémentaires globales du jour.
GLOBAL_SURGE_ACTIVITY = 4129614942

# Surcharges d'ARME (une seule active par secteur, issue de sa déf statique).
WEAPON_SURGE_HASHES: set[int] = {
    95459596,    # s_LR
    1282934989,  # s_FDP
    2178457119,  # s_FAR
    2626834038,  # s_FAF
    2743796883,  # s_G
    3132780533,  # s_FAP
    3320777106,  # s_FAFL
    3758645512,  # s_LG
    795009574,   # s_M
    1326581064,  # s_E
}

# Surcharges ÉLÉMENTAIRES (2 actives par semaine, globales).
ELEMENTAL_SURGE_HASHES: set[int] = {
    426976067,   # s_S
    2691200658,  # s_C
    3196075844,  # s_A
    2983647439,  # s_St
    3809788899,  # s_St
    3810297122,  # s_F
}


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


def weekly_elemental_surges(available_activities: list[dict]) -> list[int]:
    """Les surcharges élémentaires de la semaine (normalement 2).

    Lues sur l'activité globale GLOBAL_SURGE_ACTIVITY d'availableActivities
    (surges communes à toutes les activités du jour), filtrées à l'ensemble connu
    ELEMENTAL_SURGE_HASHES. Le filtrage par ensemble (plutôt que positionnel) est
    insensible à un éventuel réordonnancement Bungie. Renvoie [] si l'activité
    globale est absente (repli silencieux)."""
    for a in available_activities:
        if a.get("activityHash") == GLOBAL_SURGE_ACTIVITY:
            return [
                h for h in a.get("modifierHashes", [])
                if h in ELEMENTAL_SURGE_HASHES
            ]
    return []


# ── Raids & Donjons ────────────────────────────────────────────────────


def group_raid_dungeon(
    activities: list[dict], manifest, permanent_hashes: set[int] | None = None
) -> list[WeeklyActivity]:
    """Filtre les raids/donjons et regroupe par nom de base.

    Les variantes (Standard/Maîtrise) sont conservées avec leurs infos
    (lumière, palier de difficulté, modifiers, nb de challenges actifs) issues
    du profil. `active_challenges` sert de signal "featured" (cf.
    WeeklyActivity.featured). `permanent_hashes` (set d'activity_hash) marque les
    groupes "permanents" (contenu le plus récent, défini hors code)."""
    permanent_hashes = permanent_hashes or set()
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
            active_challenges=len(raw.get("challenges", [])),
        ))

        if ah in permanent_hashes:
            group.permanent = True

    return list(groups.values())


# ── Secteurs perdus ────────────────────────────────────────────────────


def collect_lost_sectors(
    interactables: list[dict],
    manifest,
    *,
    extra: dict | None = None,
    elemental_surges: list[int] | None = None,
) -> list[LostSector]:
    """Résout les secteurs perdus via entries[activityInteractableElementIndex].

    Chaque référence (hash, elementIndex) pointe vers UNE entrée précise de la
    définition d'interactable — on n'itère donc PAS toutes les entries (ce qui
    causait le faux dédoublement). `extra` greffe des infos maison par
    activity_hash (str) dans la variante correspondante.

    Modificateurs affichés par variante = la surcharge d'ARME du secteur (filtrée
    depuis sa déf statique via WEAPON_SURGE_HASHES, normalement 1 seule) SUIVIE
    des 2 surcharges ÉLÉMENTAIRES de la semaine (`elemental_surges`, lues en amont
    sur l'activité globale). Ordre : arme d'abord, puis élémentaires.

    On n'utilise PLUS toutes les surges élémentaires de la déf statique (elle les
    liste toutes → affichait toutes les surges de tous les éléments)."""
    extra = extra or {}
    elemental_surges = list(elemental_surges or [])
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

        # Surcharge d'arme : filtrée depuis la déf statique (spécifique secteur).
        weapon_surges = [
            h for h in _def_modifier_hashes(adef) if h in WEAPON_SURGE_HASHES
        ]

        variant = ActivityVariant(
            activity_hash=ah,
            label=label,
            recommended_light=_norm_light(adef.get("activityLightLevel")),
            modifier_hashes=weapon_surges + elemental_surges,
        )
        if str(ah) in extra:
            variant.extra = dict(extra[str(ah)])
        group.variants.append(variant)

    return list(groups.values())