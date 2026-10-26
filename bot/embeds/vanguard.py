# -*- coding: utf-8 -*-
"""Rendu Components V2 de l'Avant-garde (activités du Portail en focus).

UN MESSAGE PAR CATÉGORIE (Escouade, Prestige, Arène, Solo) : build_vanguard_views
renvoie une liste de (vue, fichiers). Chaque message :
- en-tête : `ui.Section` avec le titre de la catégorie (+ ligne d'actualisation
  sur le 1er message seulement) et l'icône Portal_Ico en accessoire ;
- un `ui.Separator` sous l'en-tête (comme raids/donjons) ;
- par activité : une `ui.Section` (nom, tags alerte/défi, item focus en lien
  light.gg) avec l'icône de l'item en accessoire, PUIS le bandeau pgcr recadré.
  Les activités s'enchaînent sans séparateur.

Les icônes d'items sont servies par URL Bungie (pas de pièce jointe) : un
message garde ainsi au plus 1 icône de catégorie + 1 bandeau par activité,
sous la limite Discord de 10 fichiers.

Cache d'images : bandeaux sous `banners/avant_garde/` (purge quotidienne
orchestrée par le handler)."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import next_reset
from bot.embeds.banner import BANNER_RATIO, get_banner
from bot.features.loottable.constants import ammo_type_tag, damage_type_tag, weapon_type_tag
from bot.features.vanguard.constants import (
    ARMOR_SUBTYPE_LABELS,
    LIGHT_GG_BASE,
    PORTAL_ICON_DIR,
)
from bot.features.vanguard.models import FocusItem, PortalActivity, PortalCategory
from bot.utils.logger import log

_ACCENT = discord.Color.dark_red()

# Clé de feature pour le cache d'images (cf. banner.py / purge_banner_cache).
FEATURE = "avant_garde"

_BUNGIE_ROOT = "https://www.bungie.net"

# Limite Discord : 10 fichiers par message, dont 1 pour l'icône de catégorie.
_MAX_BANNERS = 9


class VanguardView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


def _tags_line(act: PortalActivity) -> str:
    """Ligne « Alerte de l'Avant-garde · Défi », ou '' si aucun tag."""
    tags = []
    if act.is_alert:
        tags.append("Alerte de l'Avant-garde")
    if act.is_challenge:
        tags.append("Défi")
    return f"-# {' · '.join(tags)}" if tags else ""


def _type_tags(f: FocusItem) -> str:
    """Armure → libellé FR de la pièce ; arme → « type • élément • munitions »
    (emojis de la table de loot, libellé FR en repli)."""
    if f.sub_type in ARMOR_SUBTYPE_LABELS:
        return ARMOR_SUBTYPE_LABELS[f.sub_type]
    tags = [
        weapon_type_tag(f.sub_type, f.ammo_type),
        damage_type_tag(f.damage_type),
        ammo_type_tag(f.ammo_type),
    ]
    return " ".join(t for t in tags if t)


def _focus_line(act: PortalActivity) -> str:
    """« Focus : [**Haut fourneau**](light.gg) <type> <élément> <munitions> »."""
    f = act.focus
    if f is None:
        return "-# Aucun focus détecté."
    line = f"Focus : [**{f.name}**]({LIGHT_GG_BASE}{f.item_hash})"
    tags = _type_tags(f)
    return f"{line} · {tags}" if tags else line


def _activity_item(act: PortalActivity) -> ui.Item:
    """Section (texte + icône de l'item focus), ou simple texte sans icône."""
    lines = [f"### {act.base_name}", _tags_line(act), _focus_line(act)]
    text = ui.TextDisplay("\n".join(line for line in lines if line))
    if act.focus and act.focus.icon:
        return ui.Section(text, accessory=ui.Thumbnail(f"{_BUNGIE_ROOT}{act.focus.icon}"))
    return text


def _header(cat: PortalCategory, refresh_unix: int | None, files: list[discord.File]) -> ui.Item:
    """En-tête : titre (+ actualisation) avec l'icône de catégorie si présente."""
    text = f"# {cat.label}"
    if refresh_unix is not None:
        text += f"\nActualisation <t:{refresh_unix}:R>"
    title = ui.TextDisplay(text)

    icon = PORTAL_ICON_DIR / cat.icon_file
    try:
        data = icon.read_bytes()
    except OSError as e:
        log.warning(f"[Avant-garde] Icône {icon.name} illisible : {e}")
        return title
    fname = f"portal_{cat.key}.png"
    files.append(discord.File(BytesIO(data), filename=fname))
    return ui.Section(title, accessory=ui.Thumbnail(f"attachment://{fname}"))


async def _build_category(
    cat: PortalCategory, refresh_unix: int | None, ratio: float
) -> tuple[VanguardView, list[discord.File]]:
    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(_header(cat, refresh_unix, files))
    container.add_item(ui.Separator())

    if not cat.activities:
        container.add_item(ui.TextDisplay("-# Aucune activité en focus détectée."))

    banners = 0
    for act in cat.activities:
        container.add_item(_activity_item(act))
        if not act.pgcr_image or banners >= _MAX_BANNERS:
            continue
        banner = await get_banner(act.pgcr_image, FEATURE, ratio)
        if banner:
            fname = f"ag_{cat.key}_{banners}.webp"
            files.append(discord.File(BytesIO(banner), filename=fname))
            container.add_item(ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{fname}")))
            banners += 1

    return VanguardView(container), files


async def build_vanguard_views(
    categories: list[PortalCategory],
    ratio: float = BANNER_RATIO,
    next_refresh_unix: int | None = None,
) -> list[tuple[VanguardView, list[discord.File]]]:
    """Une (vue, fichiers) par catégorie. La ligne « Actualisation » (prochain
    reset quotidien par défaut) n'apparaît que sur le premier message."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_reset().timestamp())
    views = []
    for i, cat in enumerate(categories):
        views.append(await _build_category(cat, next_refresh_unix if i == 0 else None, ratio))
    return views
