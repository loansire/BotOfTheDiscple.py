# -*- coding: utf-8 -*-
"""Rendu Components V2 des activités weekly/daily.

- Raids & Donjons : message texte (pas de rotation featured pour l'instant →
  en-tête explicatif + liste compacte).
- Secteurs perdus : une carte par secteur, texte (boucliers/champions par
  difficulté) PUIS bandeau pgcr recadré.

Les builders renvoient une LayoutView (et la liste des fichiers à joindre,
pour les secteurs). La publication (post/édition) est gérée ailleurs."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import last_reset
from bot.embeds.banner import BANNER_RATIO, get_banner
from bot.features.weekly.models import ActivityVariant, LostSector, WeeklyActivity

_ACCENT = discord.Color.dark_red()

# Emojis de titre — ajuste librement (emojis custom serveur acceptés).
_RD_EMOJI = "<:Raid:1338595321319788595>"
_LS_EMOJI = "<:Secteur:1270042203577778246>"

# Emotes des boucliers / champions, par clé telle qu'écrite dans
# lost_sector_extra.json (greffée dans variant.extra).
_EXTRA_EMOJIS = {
    # Boucliers
    "Solaires": "<:Solaire:1270714993553178624>",
    "Abyssaux": "<:Abyssale:1270715025660711023>",
    "Cryo-électriques": "<:Cryo:1270715011781627904>",
    "Stasiques": "<:Stase:1293381064869285938>",
    "Filobscures": "<:Filobscur:1293381094774931456>",
    # Champions
    "Brise-bouclier": "<:Bloqueur:1270042102033678388>",
    "Perturbation": "<:Surcharge:1270042140944236619>",
    "Chancellement": "<:Implacable:1270042120857849877>",
}

# Emojis d'en-tête de groupe (boucliers / champions) dans une ligne.
_SHIELD_PREFIX = "🛡️"
_CHAMP_PREFIX = "⚔️"


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


def _emote_group(values: dict, sep: str = " ") -> str:
    """'{Abyssaux: 11, ...}' → '<:emote:…>11 <:emote:…>2'.
    Ignore les clés sans emote connue."""
    parts = []
    for key, n in values.items():
        emote = _EXTRA_EMOJIS.get(key)
        if emote:
            parts.append(f"{emote}{n}")
    return sep.join(parts)


def _format_variant_line(variant: ActivityVariant) -> str | None:
    """Ligne d'une difficulté : '**Maîtrise** — 🛡️ … · ⚔️ …', ou None si
    aucune donnée greffée."""
    extra = variant.extra or {}
    shields = _emote_group(extra.get("shields", {}))
    champs = _emote_group(extra.get("champions", {}))

    segments = []
    if shields:
        segments.append(f"{shields}")
    if champs:
        segments.append(f"{champs}")
    if not segments:
        return None

    return f"**{variant.label}** - " + "  |  ".join(segments)


async def build_lost_sectors_view(
    sectors: list[LostSector], ratio: float = BANNER_RATIO
) -> tuple[WeeklyView, list[discord.File]]:
    """Renvoie (vue, fichiers). Chaque secteur : titre, lignes par difficulté
    (boucliers/champions en emotes), puis bandeau recadré."""
    reset_unix = int(last_reset().timestamp())
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(
        f"# {_LS_EMOJI} Secteurs Oubliés du jour\n"
        f"Mis à jour le <t:{reset_unix}:f>"
    ))

    files: list[discord.File] = []
    for i, sector in enumerate(sectors):
        container.add_item(ui.Separator())

        dest = f" · {sector.destination}" if sector.destination else ""
        lines = [f"### {sector.base_name}{dest}"]

        for variant in sector.variants:
            line = _format_variant_line(variant)
            if line:
                lines.append(line)

        # Repli : si aucune donnée greffée, on liste au moins les difficultés.
        if len(lines) == 1:
            diffs = " · ".join(v.label for v in sector.variants)
            if diffs:
                lines.append(diffs)

        container.add_item(ui.TextDisplay("\n".join(lines)))

        if sector.pgcr_image:
            banner = await get_banner(sector.pgcr_image, ratio)
            if banner:
                fname = f"ls_{i}.webp"
                files.append(discord.File(BytesIO(banner), filename=fname))
                container.add_item(
                    ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{fname}"))
                )

    return WeeklyView(container), files