# -*- coding: utf-8 -*-
"""Constantes de la feature Table de butin (co-localisées).

Feature 100 % MANUELLE côté données : la liste des items de chaque activité est
maintenue à la main en base (tables compute_loot_table*). Seules les
MÉTADONNÉES d'un item (nom FR, icône, watermark, façonnabilité, type d'arme,
élément, type de munitions) sont résolues automatiquement via la définition
Bungie — exactement comme Xûr.

Les tables d'énumérés ci-dessous (sous-type d'arme / type de dégâts / munitions)
sont des valeurs NUMÉRIQUES du manifest : elles sont stables et indépendantes de
la langue, contrairement à `itemTypeDisplayName` (renvoyé en anglais par l'API
live). C'est donc sur elles qu'on mappe emojis et libellés FR.
"""
from bot.core.config import RESOURCES_DIR
from bot.render.emotes import e

# Bannières d'activité (images locales, optionnelles).
ACTIVITY_BANNER_DIR = RESOURCES_DIR / "ActivityBanner"

# Clé de cache d'icônes (sous-dossier `banners/<feature>/`).
ICON_FEATURE = "loottable"

# Base des fiches d'item .
LIGHT_GG_BASE = "https://www.light.gg/db/fr/items/"

# Emoji custom du schéma extractible (Souvenance)
SOUVENANCE_EMOJI = e("misc.craftable")

# Plafond par message. La contrainte DURE n'est pas les 40 composants CV2 mais
# les 10 pièces jointes par message : 1 bannière + 1 icône par item → 9 items
# max. Au-delà, la vue pagine (boutons ◀ ▶).
MAX_ITEMS_PER_PAGE = 9

# Rareté exotique (DestinyInventoryItemDefinition.inventory.tierType).
TIER_EXOTIC = 6

# Note affichée sous la ligne de tags des items exotiques.
EXOTIC_NOTE = (
    "-# *Obtenu en terminant l'activité.*\n"
    "-# *Les catalyseurs se débloquent*\n"
    "-# *en difficulté Maîtrise ou supérieure.*"
)


# ── Type d'activité (champ "type" de loot_tables.json) ──────────────────
ACTIVITY_TYPE_EMOJIS: dict[str, str] = {
    "prestige": e("loot.prestige"),
    "destination": e("loot.destination"),
}


# Ordre de tri de l'autocomplétion.
ACTIVITY_TYPE_ORDER: dict[str, int] = {
    "prestige": 0,
    "destination": 1,
}

_UNKNOWN_TYPE_ORDER = len(ACTIVITY_TYPE_ORDER)

def activity_type_tag(activity_type: str | None) -> str:
    """Emoji du type d'activité, ou '' si absent/inconnu."""
    if not activity_type:
        return ""
    return ACTIVITY_TYPE_EMOJIS.get(activity_type, "")


def activity_type_order(activity_type: str | None) -> int:
    """Rang de tri du type ; les valeurs inconnues passent en dernier."""
    if not activity_type:
        return _UNKNOWN_TYPE_ORDER
    return ACTIVITY_TYPE_ORDER.get(activity_type, _UNKNOWN_TYPE_ORDER)


# Libellés lisibles des types, utilisés par les séparateurs d'autocomplétion
# (les emojis custom ne sont PAS rendus dans un Choice.name : texte brut only).
ACTIVITY_TYPE_LABELS: dict[str, str] = {
    "prestige": "Prestige",
    "destination": "Destination",
}

# Libellé de repli pour un type absent ou non déclaré ci-dessus.
UNKNOWN_TYPE_LABEL = "Autres"


def activity_type_label(activity_type: str | None) -> str:
    """Libellé affichable du type ; repli sur le type brut capitalisé, puis
    sur UNKNOWN_TYPE_LABEL. Un type inconnu reste ainsi lisible dans la liste."""
    if not activity_type:
        return UNKNOWN_TYPE_LABEL
    return ACTIVITY_TYPE_LABELS.get(activity_type) or activity_type.capitalize()

# ── Sous-type d'arme (DestinyInventoryItemDefinition.itemSubType) ───────
# Libellés FR utilisés en repli quand l'emoji correspondant n'est pas renseigné.
WEAPON_TYPE_LABELS: dict[int, str] = {
    6: "Fusil auto",
    7: "Fusil à pompe",
    8: "Mitrailleuse",
    9: "Revolver",
    10: "Lance-roquettes",
    11: "Fusil à fusion",
    12: "Fusil de précision",
    13: "Fusil à impulsion",
    14: "Fusil d'éclaireur",
    17: "Pistolet",
    18: "Épée",
    22: "Fusil à fusion linéaire",
    23: "Lance-grenades",
    24: "Pistolet-mitrailleur",
    25: "Fusil à rayon",
    31: "Arc",
    33: "Glaive",
}

# emoji custom par sous-type d'arme.
WEAPON_TYPE_EMOJIS: dict[int, str] = {
    6: e("weapon.auto_rifle"),   # Fusil auto
    7: e("weapon.shotgun"),   # Fusil à pompe
    8: e("weapon.machine_gun"),   # Mitrailleuse
    9: e("weapon.hand_cannon"),   # Revolver
    10: e("weapon.rocket_launcher"),  # Lance-roquettes
    11: e("weapon.fusion_rifle"),  # Fusil à fusion
    12: e("weapon.sniper_rifle"),  # Fusil de précision
    13: e("weapon.pulse_rifle"),  # Fusil à impulsion
    14: e("weapon.scout_rifle"),  # Fusil d'éclaireur
    17: e("weapon.sidearm"),  # Arme de poing
    18: e("weapon.sword"),  # Épée
    22: e("weapon.linear_fusion"),  # Fusil à fusion linéaire
    23: e("weapon.heavy_gl"),  # Lance-grenades (lourd)
    24: e("weapon.smg"),  # Pistolet-mitrailleur
    25: e("weapon.trace_rifle"),  # Fusil à rayon
    31: e("weapon.bow"),  # Arc
    33: e("weapon.glaive"),  # Glaive
}

# ── Surcharges (sous-type, munitions) ───────────────────────────────────
# Certains sous-types recouvrent DEUX archétypes que le manifest ne sépare
# pas : seul `ammoType` tranche. Cette table est consultée AVANT
# WEAPON_TYPE_EMOJIS / WEAPON_TYPE_LABELS.
#  munitions lourdes (3) → lourd, munitions spéciales (2) → léger.
WEAPON_TYPE_AMMO_EMOJIS: dict[tuple[int, int], str] = {
    (23, 3): e("weapon.heavy_gl"),
    (23, 2): e("weapon.special_gl"),
}

WEAPON_TYPE_AMMO_LABELS: dict[tuple[int, int], str] = {
    (23, 3): "Lance-grenades lourd",
    (23, 2): "Lance-grenades léger",
}


# ── Élément (DestinyInventoryItemDefinition.defaultDamageType) ──────────
DAMAGE_TYPE_LABELS: dict[int, str] = {
    1: "Cinétique",
    2: "Arc",
    3: "Solaire",
    4: "Vide",
    6: "Stase",
    7: "Filament",
}

# Emojis élémentaires
DAMAGE_TYPE_EMOJIS: dict[int, str] = {
    1: e("element.kinetic"),   # Cinétique
    2: e("element.arc"),   # Arc
    3: e("element.solar"),   # Solaire
    4: e("element.void"),   # Vide
    6: e("element.stasis"),   # Stase
    7: e("element.strand"),   # Filament
}


# ── Munitions (equippingBlock.ammoType) ────────────────────────────────
AMMO_TYPE_LABELS: dict[int, str] = {
    1: "Primaire",
    2: "Spéciale",
    3: "Lourde",
}

# emoji custom par type de munitions.
AMMO_TYPE_EMOJIS: dict[int, str] = {
    1: e("ammo.primary"),  # Primaire
    2: e("ammo.special"),  # Spéciale
    3: e("ammo.heavy"),  # Lourde
}


def weapon_type_tag(sub_type: int | None, ammo_type: int | None = None) -> str:
    """Emoji du sous-type d'arme, ou libellé FR en repli, ou '' si inconnu.

    `ammo_type` permet de départager les sous-types ambigus (cf.
    WEAPON_TYPE_AMMO_EMOJIS) ; il reste optionnel, l'appel à un seul argument
    retombe sur la table générique."""
    if sub_type is None:
        return ""
    if ammo_type is not None:
        combo = (sub_type, ammo_type)
        override = (
            WEAPON_TYPE_AMMO_EMOJIS.get(combo)
            or WEAPON_TYPE_AMMO_LABELS.get(combo)
        )
        if override:
            return override
    return WEAPON_TYPE_EMOJIS.get(sub_type) or WEAPON_TYPE_LABELS.get(sub_type, "")


def damage_type_tag(damage_type: int | None) -> str:
    """Emoji d'élément, ou libellé FR en repli, ou '' si inconnu."""
    if damage_type is None:
        return ""
    return DAMAGE_TYPE_EMOJIS.get(damage_type) or DAMAGE_TYPE_LABELS.get(damage_type, "")


def ammo_type_tag(ammo_type: int | None) -> str:
    """Emoji de munitions, ou libellé FR en repli, ou '' si inconnu."""
    if ammo_type is None:
        return ""
    return AMMO_TYPE_EMOJIS.get(ammo_type) or AMMO_TYPE_LABELS.get(ammo_type, "")
