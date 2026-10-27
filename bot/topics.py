# -*- coding: utf-8 -*-
"""Registre UNIQUE des topics configurables (source de vérité, sans import).

Chaque topic déclare ici son identité d'affichage (libellés et emoji pour
/botconfig), s'il accepte un rôle à pinger, et le libellé qu'il prend dans
/refresh (None = non rafraîchissable : topics événementiels news/maintenance).

La publication associée à chaque topic persistant est déclarée dans
bot/publishing/registry.py. Ajouter une feature = une entrée ici + une ligne
là-bas : /botconfig, /refresh et le routeur de changement de salon suivent."""
from __future__ import annotations

from dataclasses import dataclass


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
        Topic("maintenance_destiny", "Maintenance", "Maintenance", "<:D2:1270042220627497020>"),
        Topic("maintenance_marathon", "Maintenance", "Maintenance", "<:Marathon:1513347065881559273>"),
        Topic("news_twid", "This Week in Destiny", "TWID", "📰"),
        Topic("news_patch_note", "Patch Note", "Patch note", "📝"),
        Topic("daily_lost_sector", "Secteurs Oubliés du jour", "Secteur oublié",
              "<:Secteur:1270042203577778246>", refresh="Secteurs Oubliés"),
        Topic("weekly_raid", "Raids de la semaine", "Raids",
              "<:Raid:1338595321319788595>", refresh="Raids"),
        Topic("weekly_dungeon", "Donjons de la semaine", "Donjons",
              "<:Donjon:1338595206706233458>", refresh="Donjons"),
        Topic("daily_vanguard", "Avant-garde - Focus du jour", "Avant-garde", "🛡️",
              refresh="Avant-garde"),
        Topic("xur", "Xûr - Agent des Neuf", "Xûr", "<:Xur:1527021351368659205>", refresh="Xûr"),
        Topic("eververse", "Eververse - Tess Everis", "Eververse",
              "<:Tess:1527021352245268675>", refresh="Eververse"),
        Topic("ada", "Ada-1 - Revêtements", "Ada-1", "<:Ada:1527021353591374024>", refresh="Ada-1"),
        Topic("distortion", "Distorsion", "Distorsion", "<:Distortion:1533753753772097596>",
              no_role=True, refresh="Distorsion"),
        Topic("ascendant", "Défi ascendant de la semaine", "Défi ascendant",
              "<:Challenge_Ascendant:1534163534970093618>", no_role=True, refresh="Défi ascendant"),
    )
}
