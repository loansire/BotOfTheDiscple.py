# -*- coding: utf-8 -*-
"""Tables d'emotes custom des raids & donjons.

Extraites de embeds/weekly.py pour être partagées entre la publication
hebdomadaire (embeds/weekly.py) et la rotation prédictive
(embeds/weekly_rotation.py) sans import circulaire.

Le matching se fait sur la forme NORMALISÉE (cf. features.weekly.rotation.
norm_name) pour absorber les écarts avec le manifest Bungie : article initial
« Le/La », ligature œ, accents.
"""
from __future__ import annotations

from bot.features.weekly.rotation import norm_name

# Emojis génériques de repli (également utilisés comme emoji de titre).
RD_EMOJI = "<:Raid:1338595321319788595>"
DJ_EMOJI = "<:Donjon:1338595321319788595>"

RAID_EMOJIS_RAW = {
    "Dernier Voeu": "<:LW:1273058036209946634>",
    "Jardin du Salut": "<:JDS:1273058012751335486>",
    "Crypte de la Pierre": "<:DSC:1273057991670890496>",
    "Caveau de verre": "<:VOG:1273058120192495658>",
    "Serment du Disciple": "<:VOW:1273058146453295155>",
    "Chute du Roi": "<:Oryx:1273058059849302056>",
    "Origine des Cauchemars": "<:RON:1273058080086560870>",
    "Chute de Cropta": "<:Cropta:1273057968660676790>",
    "Orée du Salut": "<:SE:1273058098818322492>",
    "Désert Perpétuel": "<:DP:1399391431302451300>",
    "Désert perpétuel (Épique)": "<:DP:1399391431302451300>",
}

DUNGEON_EMOJIS_RAW = {
    "Fosse de l'Hérésie": "<:Fosse:1275104301827620865>",
    "Prophétie": "<:Prophetie:1275104326854901852>",
    "Trône Brisé": "<:Trone:1275104381242572873>",
    "Etreinte de l'Avarice": "<:Etreinte:1275104223016517742>",
    "Dualité": "<:Dualite:1275104177143676948>",
    "Flèche de la Vigie": "<:Fleche:1275104276347359385>",
    "Fantômes des Profondeurs": "<:Fantome:1275104249700941844>",
    "Ruine de la Guerrière": "<:Ruine:1275104356387000450>",
    "Hôte Vesper": "<:Vesper:1295144736964870214>",
    "Dogme fragmenté": "<:Dogme:1341339537221353492>",
    "Équilibre": "<:Equilibre:1513709145348509726>",
}

# Dicts résolus une fois, par forme normalisée.
RAID_EMOJIS = {norm_name(k): v for k, v in RAID_EMOJIS_RAW.items()}
DUNGEON_EMOJIS = {norm_name(k): v for k, v in DUNGEON_EMOJIS_RAW.items()}


def activity_emoji_for(base_name: str, activity_type: str) -> str:
    """Emoji custom d'une activité, avec repli générique par type.

    `activity_type` : 'Raid' ou 'Donjon' (valeurs de WeeklyActivity)."""
    key = norm_name(base_name)
    if activity_type == "Donjon":
        return DUNGEON_EMOJIS.get(key, DJ_EMOJI)
    return RAID_EMOJIS.get(key, RD_EMOJI)