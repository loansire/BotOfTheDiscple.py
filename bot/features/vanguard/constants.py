# -*- coding: utf-8 -*-
"""Constantes de la feature Avant-garde (Portail : activités en focus du jour)."""
from datetime import datetime, timezone

from bot.config import RESOURCES_DIR

TOPIC = "daily_vanguard"

# Dossier des icônes de catégorie (thumbnail de chaque container).
PORTAL_ICON_DIR = RESOURCES_DIR / "Portal_Ico"

# Catégories publiées, dans l'ordre d'affichage : (clé, nœud racine du graphe
# Fireteam Finder, titre, fichier icône). Les nœuds racines sont ceux de
# DestinyGlobalConstantsDefinition.portalActivityGraphRootNodesWithIcons ;
# l'Épreuve et le Gambit (PvP) ne sont volontairement pas publiés.
CATEGORIES: tuple[tuple[str, int, str, str], ...] = (
    ("fireteam", 4038998327, "Opérations d'escouade", "portal_fireteam.png"),
    ("pinnacle", 2042336100, "Opérations de prestige", "portal_pinnacle.png"),
    ("arena", 2699534027, "Opérations en arène", "portal_arena.png"),
    ("solo", 1204273545, "Opérations en solo", "portal_solo.png"),
)

# Récompense commune à toutes les activités du Portail (« Gain bonus des
# Opérations ») : ignorée pour trouver l'item focus.
OPS_BONUS_REWARD = 3956025454

LIGHT_GG_BASE = "https://www.light.gg/db/fr/items/"

# Fiche d'un bonus de set d'armure (`id` = sandboxPerkHash, ouvre la popup).
D2GLOSSARY_SET_PERK = "https://d2glossary.fr/setarmor.html?id="

# Libellés FR des pièces d'armure (DestinyItemSubType) : l'API live renvoie
# itemTypeDisplayName en anglais. Les armes passent par les tags de la table
# de loot (emoji type / élément / munitions).
ARMOR_SUBTYPE_LABELS: dict[int, str] = {
    26: "Casque",
    27: "Gantelets",
    28: "Armure de torse",
    29: "Jambières",
    30: "Objet de classe",
}

# ── Armes de défi (rotation hebdomadaire) ──────────────────────────────
# Le manifest liste le POOL complet des récompenses d'un défi
# (challenges[].displayRewards, armes puis récompenses génériques) sans
# indiquer l'arme de la semaine : elle avance d'un cran par semaine dans
# l'ordre des ARMES du pool. Ancrage = arme observée en jeu la semaine de
# référence, par objectif de défi. Un défi absent d'ici n'affiche pas d'arme.
CHALLENGE_REFERENCE_WEEK = datetime(2026, 10, 20, 17, 0, tzinfo=timezone.utc)
CHALLENGE_ANCHORS: dict[int, int] = {
    907263283: 1479562935,   # Partie rapide (Escouade) → Aube de l'aurore
    3511848321: 189854537,   # Berceau du mal (Grand-maître) → Coup violent
}
