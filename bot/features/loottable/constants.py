# -*- coding: utf-8 -*-
"""Constantes de la feature Table de butin (co-localisées).

Feature 100 % MANUELLE côté données : la liste des items de chaque activité est
maintenue à la main dans `Ressources/LootTable/loot_tables.json`. Seules les
MÉTADONNÉES d'un item (nom FR, icône, watermark, façonnabilité, type d'arme,
élément, type de munitions) sont résolues automatiquement via la définition
Bungie — exactement comme Xûr.

Les tables d'énumérés ci-dessous (sous-type d'arme / type de dégâts / munitions)
sont des valeurs NUMÉRIQUES du manifest : elles sont stables et indépendantes de
la langue, contrairement à `itemTypeDisplayName` (renvoyé en anglais par l'API
live). C'est donc sur elles qu'on mappe emojis et libellés FR.
"""
from bot.config import RESOURCES_DIR

# Fichier de données, maintenu à la main (hors code).
LOOT_TABLES_PATH = RESOURCES_DIR / "LootTable" / "loot_tables.json"

# Bannières d'activité (images locales, optionnelles).
ACTIVITY_BANNER_DIR = RESOURCES_DIR / "ActivityBanner"

# Clé de cache d'icônes (sous-dossier `banners/<feature>/`).
ICON_FEATURE = "loottable"

# Base des fiches d'item .
LIGHT_GG_BASE = "https://www.light.gg/db/fr/items/"

# Emoji custom du schéma extractible (Souvenance)
SOUVENANCE_EMOJI = "<:Souvenance:1528569980226895892>"

# Plafond par message. La contrainte DURE n'est pas les 40 composants CV2 mais
# les 10 pièces jointes par message : 1 bannière + 1 icône par item → 9 items
# max. Au-delà, la vue pagine (boutons ◀ ▶).
MAX_ITEMS_PER_PAGE = 9

# Rareté exotique (DestinyInventoryItemDefinition.inventory.tierType).
TIER_EXOTIC = 6

# Note affichée sous la ligne de tags des items exotiques.
EXOTIC_NOTE = (
    "-# *Obtenu en terminant l'activité. Les catalyseurs se débloquent*\n"
    "-# *en difficulté Maîtrise ou supérieure.*"
)

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
    6: "<:Fusilautomatique:1305317622266462238>",   # Fusil auto
    7: "<:Fusilapompe:1305317574585745408>",   # Fusil à pompe
    8: "<:Mitrailleuse:1305317781029388378>",   # Mitrailleuse
    9: "<:Revolver:1305317829653823608>",   # Revolver
    10: "<:Lanceroquettes:1305317762712735744>",  # Lance-roquettes
    11: "<:Fusion:1305317671889403925>",  # Fusil à fusion
    12: "<:Fusildeprecision:1305317655221375026>",  # Fusil de précision
    13: "<:Fusilaimpulsion:1305317558748057661>",  # Fusil à impulsion
    14: "<:Fusildeclaireur:1305317638158942248>",  # Fusil d'éclaireur
    17: "<:Pistolet:1305317796908892160>",  # Arme de poing
    18: "<:Epee:1305317544684556370>",  # Épée
    22: "<:Fusionlineaire:1305317687894999060>",  # Fusil à fusion linéaire
    23: "<:Lancegrenadeslourd:1305317747349000192>",  # Lance-grenades (lourd)
    24: "<:Pistoletmitrailleur:1305317813094711416>",  # Pistolet-mitrailleur
    25: "<:Fusilarayon:1305317604839264257>",  # Fusil à rayon
    31: "<:Arc:1305317528079437955>",  # Arc
    33: "<:Glaive:1305317709751259147>",  # Glaive
}

# ── Surcharges (sous-type, munitions) ───────────────────────────────────
# Certains sous-types recouvrent DEUX archétypes que le manifest ne sépare
# pas : seul `ammoType` tranche. Cette table est consultée AVANT
# WEAPON_TYPE_EMOJIS / WEAPON_TYPE_LABELS.
#  munitions lourdes (3) → lourd, munitions spéciales (2) → léger.
WEAPON_TYPE_AMMO_EMOJIS: dict[tuple[int, int], str] = {
    (23, 3): "<:Lancegrenadeslourd:1305317747349000192>",
    (23, 2): "<:Lancegrenadesleger:1305317726125948968>",
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
    1: "<:Ci:1353052017278320650>",   # Cinétique
    2: "<:Cr:1270715011781627904>",   # Arc
    3: "<:So:1270714993553178624>",   # Solaire
    4: "<:Ab:1270715025660711023>",   # Vide
    6: "<:St:1293381064869285938>",   # Stase
    7: "<:Fi:1293381094774931456>",   # Filament
}


# ── Munitions (equippingBlock.ammoType) ────────────────────────────────
AMMO_TYPE_LABELS: dict[int, str] = {
    1: "Primaire",
    2: "Spéciale",
    3: "Lourde",
}

# emoji custom par type de munitions.
AMMO_TYPE_EMOJIS: dict[int, str] = {
    1: "<:Principale:1352409012511051799>",  # Primaire
    2: "<:Speciale:1352409042538070016>",  # Spéciale
    3: "<:Lourde:1352409107273093191>",  # Lourde
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
