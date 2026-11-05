# -*- coding: utf-8 -*-
"""Registre UNIQUE des topics configurables (source de vérité, sans import).

Chaque topic déclare ici son identité d'affichage (libellés et emoji pour
/botconfig), s'il accepte un rôle à pinger, et le libellé qu'il prend dans
/refresh (None = non rafraîchissable : topics événementiels news/maintenance ;
les maintenances ont leurs choix /refresh propres, cf. cogs/pipeline.py).

La publication associée à chaque topic persistant est déclarée dans
bot/publishing/registry.py. Ajouter une feature = une entrée ici + une ligne
là-bas : /botconfig, /refresh et le routeur de changement de salon suivent."""
from __future__ import annotations

from dataclasses import dataclass
from bot.render.emotes import e


@dataclass(frozen=True)
class Topic:
    key: str
    label: str              # libellé complet (page détail /botconfig)
    short: str              # nom compact (aperçus de navigation)
    emoji: str = ""
    no_role: bool = False   # True → aucun rôle configurable (édition en place)
    refresh: str | None = None  # libellé du choix /refresh, None = absent


TOPICS: dict[str, Topic] = {
    t.key: t
    for t in (
        Topic("maintenance_destiny", "Maintenance", "Maintenance", e("game.destiny")),
        Topic("maintenance_marathon", "Maintenance", "Maintenance", e("game.marathon")),
        Topic("news_twid", "This Week in Destiny", "TWID", "📰"),
        Topic("news_patch_note", "Patch Note", "Patch note", "📝"),
        Topic("daily_lost_sector", "Secteurs Oubliés du jour", "Secteur oublié",
              e("topic.lost_sector"), refresh="Secteurs Oubliés"),
        Topic("weekly_raid", "Raids de la semaine", "Raids",
              e("topic.raid"), refresh="Raids"),
        Topic("weekly_dungeon", "Donjons de la semaine", "Donjons",
              e("topic.dungeon"), refresh="Donjons"),
        Topic("daily_vanguard", "Avant-garde - Focus du jour", "Avant-garde", e("topic.avant_garde"),
              refresh="Avant-garde"),
        Topic("xur", "Xûr - Agent des Neuf", "Xûr", e("topic.xur"), refresh="Xûr"),
        Topic("eververse", "Eververse - Tess Everis", "Eververse",
              e("topic.eververse"), refresh="Eververse"),
        Topic("ada", "Ada-1 - Revêtements", "Ada-1", e("topic.ada"), refresh="Ada-1"),
        Topic("distortion", "Distorsion", "Distorsion", e("topic.distortion"),
              no_role=True, refresh="Distorsion"),
        Topic("ascendant", "Défi ascendant de la semaine", "Défi ascendant",
              e("topic.ascendant"), no_role=True, refresh="Défi ascendant"),
    )
}
