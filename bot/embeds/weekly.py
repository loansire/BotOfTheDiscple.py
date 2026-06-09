# -*- coding: utf-8 -*-
"""Rendu Components V2 des activités weekly/daily.

- Raids & Donjons : message texte (pas de rotation featured pour l'instant →
  en-tête explicatif + liste compacte).
- Secteurs perdus : une carte par secteur, texte PUIS bandeau pgcr recadré.

Les builders renvoient une LayoutView (et la liste des fichiers à joindre,
pour les secteurs). La publication (post/édition) est gérée ailleurs."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import last_reset
from bot.embeds.banner import BANNER_RATIO, get_banner
from bot.features.weekly.models import LostSector, WeeklyActivity

_ACCENT = discord.Color.dark_red()

# Emojis de titre — ajuste librement (emojis custom serveur acceptés).
_RD_EMOJI = "<:Raid:1338595321319788595>"
_LS_EMOJI = "<:Secteur:1270042203577778246>"


class WeeklyView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


# ── Raids & Donjons ────────────────────────────────────────────────────


def build_raid_dungeon_view(groups: list[WeeklyActivity]) -> WeeklyView:
    raids = [g for g in groups if g.activity_type == "Raid"]
    dungeons = [g for g in groups if g.activity_type == "Donjon"]

    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(
        f"# {_RD_EMOJI} Raids & Donjons\n"
        "-# Pas de rotation *featured* cette semaine — voici la liste complète."
    ))
    if raids:
        container.add_item(ui.Separator())
        lines = "\n".join(f"- {g.base_name}" for g in raids)
        container.add_item(ui.TextDisplay(f"**Raids ({len(raids)})**\n{lines}"))
    if dungeons:
        container.add_item(ui.Separator())
        lines = "\n".join(f"- {g.base_name}" for g in dungeons)
        container.add_item(ui.TextDisplay(f"**Donjons ({len(dungeons)})**\n{lines}"))

    return WeeklyView(container)


# ── Secteurs perdus ────────────────────────────────────────────────────


async def build_lost_sectors_view(
    sectors: list[LostSector], ratio: float = BANNER_RATIO
) -> tuple[WeeklyView, list[discord.File]]:
    """Renvoie (vue, fichiers). Chaque secteur : texte puis bandeau recadré."""
    reset_unix = int(last_reset().timestamp())
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(
        f"# {_LS_EMOJI} Secteurs Oubliés du jour\n"
        f"Mis à jour le <t:{reset_unix}:f>"
    ))

    files: list[discord.File] = []
    for i, sector in enumerate(sectors):
        container.add_item(ui.Separator())
        diffs = " · ".join(v.label for v in sector.variants)
        dest = f" · {sector.destination}" if sector.destination else ""
        container.add_item(ui.TextDisplay(f"### {sector.base_name}{dest}\n{diffs}"))

        if sector.pgcr_image:
            banner = await get_banner(sector.pgcr_image, ratio)
            if banner:
                fname = f"ls_{i}.webp"
                files.append(discord.File(BytesIO(banner), filename=fname))
                container.add_item(
                    ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{fname}"))
                )

    return WeeklyView(container), files