# -*- coding: utf-8 -*-
"""Tables d'emotes custom des raids & donjons.

Extraites de features/weekly/view.py pour être partagées entre la publication
hebdomadaire (features/weekly/view.py) et la rotation prédictive
(features/weekly/rotation_presenter.py) sans import circulaire.

Le matching se fait sur la forme NORMALISÉE (cf. features.weekly.rotation.
norm_name) pour absorber les écarts avec le manifest Bungie : article initial
« Le/La », ligature œ, accents.
"""
from __future__ import annotations

from bot.features.weekly.rotation import norm_name
from bot.render.emotes import e

# Emojis génériques de repli (également utilisés comme emoji de titre).
RD_EMOJI = e("topic.raid")
DJ_EMOJI = e("topic.dungeon")

RAID_EMOJIS_RAW = {
    "Dernier Voeu": e("raid.lw"),
    "Jardin du Salut": e("raid.gos"),
    "Crypte de la Pierre": e("raid.dsc"),
    "Caveau de verre": e("raid.vog"),
    "Serment du Disciple": e("raid.vow"),
    "Chute du Roi": e("raid.kf"),
    "Origine des Cauchemars": e("raid.ron"),
    "Chute de Cropta": e("raid.crota"),
    "Fin de Crota": e("raid.crota"),
    "Orée du Salut": e("raid.se"),
    "Désert Perpétuel": e("raid.desert"),
    "Désert perpétuel (Épique)": e("raid.desert"),
}

DUNGEON_EMOJIS_RAW = {
    "Fosse de l'Hérésie": e("dungeon.pit"),
    "Prophétie": e("dungeon.prophecy"),
    "Trône Brisé": e("dungeon.shattered_throne"),
    "Etreinte de l'Avarice": e("dungeon.grasp"),
    "Dualité": e("dungeon.duality"),
    "Flèche de la Vigie": e("dungeon.spire"),
    "Fantômes des Profondeurs": e("dungeon.ghosts"),
    "Ruine de la Guerrière": e("dungeon.warlords_ruin"),
    "Hôte Vesper": e("dungeon.vesper"),
    "Dogme fragmenté": e("dungeon.sundered_doctrine"),
    "Doctrine ébranlée": e("dungeon.sundered_doctrine"),
    "Équilibre": e("dungeon.equilibrium"),
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