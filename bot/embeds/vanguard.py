# -*- coding: utf-8 -*-
"""Rendu Components V2 de l'Avant-garde (activités du Portail en focus).

UN MESSAGE PAR CATÉGORIE (Escouade, Prestige, Arène, Solo) : build_vanguard_views
renvoie une liste de (vue, fichiers). Chaque message :
- en-tête : `ui.Section` avec le titre de la catégorie (+ ligne d'actualisation
  sur le 1er message seulement) et l'icône Portal_Ico en accessoire, rendue
  CARRÉE (les icônes sources ne le sont pas, la vignette Discord rognerait) ;
- un `ui.Separator` sous l'en-tête (comme raids/donjons) ;
- par activité : un `TextDisplay` (nom, tags alerte/défi, item focus) PUIS le
  bandeau pgcr avec l'icône de l'item INCRUSTÉE à droite. Pas de vignette à
  côté du texte : le bandeau suit directement, sans décalage.

Item focus : « Focus : nom » puis le détail sur sa propre ligne (largeur des
containers homogène) :
- arme → nom en lien light.gg, ligne d'emojis type / élément / munitions ;
- armure → nom sans lien, puis le set et ses bonus 2 / 4 pièces en liens
  D2Glossary.
Activité défi (sans focus) : « Défi : arme » avec le même rendu.

Cache d'images : bandeaux sous `banners/avant_garde/` (purge quotidienne
orchestrée par le handler)."""
from __future__ import annotations

import asyncio
from io import BytesIO

import discord
from discord import ui
from PIL import Image

from bot.bungie.reset import next_reset
from bot.embeds.banner import BANNER_RATIO, get_banner
from bot.embeds.xur_image import get_item_icon
from bot.features.loottable.constants import ammo_type_tag, damage_type_tag, weapon_type_tag
from bot.features.vanguard.constants import (
    ARMOR_SUBTYPE_LABELS,
    D2GLOSSARY_SET_PERK,
    LIGHT_GG_BASE,
    PORTAL_ICON_DIR,
)
from bot.features.vanguard.models import FocusItem, PortalActivity, PortalCategory
from bot.utils.logger import log

_ACCENT = discord.Color.dark_red()

# Clé de feature pour le cache d'images (cf. banner.py / purge_banner_cache).
FEATURE = "avant_garde"

# Limite Discord : 10 fichiers par message, dont 1 pour l'icône de catégorie.
_MAX_BANNERS = 9

# Icône incrustée : hauteur relative au bandeau, marge relative à sa hauteur.
_ICON_HEIGHT = 0.72
_ICON_MARGIN = 0.14


class VanguardView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


# ── Images ──────────────────────────────────────────────────────────────


def _square_png(data: bytes) -> bytes:
    """Centre l'image sur un fond transparent carré (côté = plus grande dimension)."""
    img = Image.open(BytesIO(data)).convert("RGBA")
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def _compose(banner: bytes, icon: bytes) -> bytes:
    """Incruste l'icône (carrée) à droite du bandeau, centrée verticalement."""
    base = Image.open(BytesIO(banner)).convert("RGB")
    size = round(base.height * _ICON_HEIGHT)
    margin = round(base.height * _ICON_MARGIN)
    ico = Image.open(BytesIO(icon)).convert("RGBA").resize((size, size), Image.LANCZOS)
    base.paste(ico, (base.width - size - margin, (base.height - size) // 2), ico)
    out = BytesIO()
    base.save(out, format="WEBP", quality=90)
    return out.getvalue()


async def _activity_banner(act: PortalActivity, ratio: float) -> bytes | None:
    """Bandeau pgcr recadré, avec l'icône de l'item focus incrustée si dispo."""
    if not act.pgcr_image:
        return None
    banner = await get_banner(act.pgcr_image, FEATURE, ratio)
    if banner is None or act.focus is None or not act.focus.icon:
        return banner
    icon = await get_item_icon(
        act.focus.item_hash, act.focus.icon, act.focus.watermark, feature=FEATURE
    )
    if icon is None:
        return banner
    return await asyncio.to_thread(_compose, banner, icon)


# ── Texte ───────────────────────────────────────────────────────────────


def _tags_line(act: PortalActivity) -> str:
    """Ligne « Alerte de l'Avant-garde · Défi », ou '' si aucun tag."""
    tags = []
    if act.is_alert:
        tags.append("Alerte de l'Avant-garde")
    if act.is_challenge:
        tags.append("Défi de la semaine")
    return f"-# {' · '.join(tags)}" if tags else ""


def _armor_lines(f: FocusItem) -> list[str]:
    """Pièce + set d'armure, chaque bonus sur sa ligne en lien D2Glossary."""
    piece = ARMOR_SUBTYPE_LABELS.get(f.sub_type, "Armure")
    lines = [f"{piece} · Set **{f.set_name}**" if f.set_name else piece]
    lines += [
        f"-# {count} pièces : [{name}]({D2GLOSSARY_SET_PERK}{perk_hash})"
        for count, name, perk_hash in f.set_perks
    ]
    return lines


def _weapon_tags(f: FocusItem) -> str:
    """« type élément munitions » (emojis de la table de loot, libellé FR en repli)."""
    tags = [
        weapon_type_tag(f.sub_type, f.ammo_type),
        damage_type_tag(f.damage_type),
        ammo_type_tag(f.ammo_type),
    ]
    return " ".join(t for t in tags if t)


def _focus_lines(act: PortalActivity) -> list[str]:
    """« Focus : item » (ou « Défi : arme ») puis le détail ligne à ligne."""
    label = "Focus" if act.is_focused else "Défi"
    f = act.focus
    if f is None:
        return [f"-# Aucun {label.lower()} détecté."]
    if f.sub_type in ARMOR_SUBTYPE_LABELS:
        return [f"{label} : **{f.name}**", *_armor_lines(f)]
    lines = [f"{label} : [**{f.name}**]({LIGHT_GG_BASE}{f.item_hash})"]
    tags = _weapon_tags(f)
    if tags:
        lines.append(tags)
    return lines


def _activity_text(act: PortalActivity) -> ui.TextDisplay:
    lines = [f"### {act.base_name}", _tags_line(act), *_focus_lines(act)]
    return ui.TextDisplay("\n".join(line for line in lines if line))


# ── Containers ──────────────────────────────────────────────────────────


async def _header(cat: PortalCategory, refresh_unix: int | None, files: list[discord.File]) -> ui.Item:
    """En-tête : titre (+ actualisation) avec l'icône de catégorie si présente."""
    text = f"# {cat.label}"
    if refresh_unix is not None:
        text += f"\nActualisation <t:{refresh_unix}:R>"
    title = ui.TextDisplay(text)

    icon = PORTAL_ICON_DIR / cat.icon_file
    try:
        data = await asyncio.to_thread(_square_png, icon.read_bytes())
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
    container.add_item(await _header(cat, refresh_unix, files))
    container.add_item(ui.Separator())

    if not cat.activities:
        container.add_item(ui.TextDisplay("-# Aucune activité en focus détectée."))

    banners = 0
    for act in cat.activities:
        container.add_item(_activity_text(act))
        if banners >= _MAX_BANNERS:
            continue
        banner = await _activity_banner(act, ratio)
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
