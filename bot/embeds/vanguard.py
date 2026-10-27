# -*- coding: utf-8 -*-
"""Rendu Components V2 de l'Avant-garde (activités du Portail en focus).

UN MESSAGE PAR CATÉGORIE (Escouade, Prestige, Arène, Solo) : build_vanguard_views
renvoie une liste de (vue, fichiers). Chaque message :
- en-tête : `ui.Section` avec le titre de la catégorie (+ ligne d'actualisation) et l'icône Portal_Ico en accessoire, rendue
  CARRÉE (les icônes sources ne le sont pas, la vignette Discord rognerait) ;
- un `ui.Separator` sous l'en-tête (comme raids/donjons) ;
- par activité : un `TextDisplay` (nom, tags alerte, item focus, arme de défi)
  PUIS le bandeau pgcr avec les icônes (focus, arme de défi) INCRUSTÉES à droite. Pas de vignette à
  côté du texte : le bandeau suit directement, sans décalage.

Item focus : « Focus : nom » puis le détail sur sa propre ligne (largeur des
containers homogène) :
- arme → nom en lien light.gg, ligne d'emojis type / élément / munitions ;
- armure → nom sans lien, puis le set et ses bonus 2 / 4 pièces en liens
  D2Glossary.
Activité avec défi hebdo : « Arme de défi : arme » sous le focus, même rendu.

Cache d'images : bandeaux sous `banners/avant_garde/` (purge quotidienne
orchestrée par le handler)."""
from __future__ import annotations

import asyncio
from io import BytesIO

import discord
from discord import ui
from PIL import Image, ImageChops, ImageDraw

from bot.bungie.reset import next_reset
from bot.embeds.banner import BANNER_RATIO, get_banner
from bot.embeds.xur_image import get_item_icon
from bot.features.loottable.constants import ammo_type_tag, damage_type_tag, weapon_type_tag
from bot.features.vanguard.constants import (
    ALERT_LABELS,
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

# Bordure de l'icône (px) : claire par défaut, dorée pour l'alerte grand maître
# (« pièce maîtresse », comme en jeu).
_BORDER = 2
_BORDER_COLOR = (220, 220, 220, 255)
_BORDER_GOLD = (230, 190, 70, 255)
_BORDER_CHALLENGE = (41, 182, 178, 255)  # turquoise de l'icône de défi en jeu

# Liseré en biais derrière l'icône (alerte grand maître), de gauche à droite :
# blanc, orange, orange, bleu marine Avant-garde, en dégradé vers la
# transparence. Largeur de bande relative à la hauteur du bandeau.
_STRIPE_COLORS = ((255, 255, 255), (235, 120, 30), (235, 120, 30), (24, 38, 82))
_STRIPE_WIDTH = 0.16


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


def _stripes(size: tuple[int, int], left: int) -> Image.Image:
    """Calque RGBA : bandes en biais (blanc, orange, orange) qui sortent de
    derrière l'icône (bord gauche `left`) vers le bas-gauche, en dégradé vers
    la transparence."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    band = max(2, round(h * _STRIPE_WIDTH))
    for i, color in enumerate(reversed(_STRIPE_COLORS)):
        x = left - i * band * 2 - band
        draw.polygon([(x, h), (x + band, h), (x + band + h, 0), (x + h, 0)], fill=(*color, 255))
    # Dégradé horizontal : transparent loin à gauche, opaque sous l'icône.
    fade = Image.new("L", size, 0)
    ramp = max(1, round(h * 2.5))
    for xx in range(w):
        v = 255 if xx >= left else max(0, 255 - (left - xx) * 255 // ramp)
        fade.paste(v, (xx, 0, xx + 1, h))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), fade))
    return layer


def _bordered(icon: bytes, size: int, color: tuple[int, int, int, int]) -> Image.Image:
    """Icône redimensionnée avec une fine bordure de la couleur donnée."""
    ico = Image.open(BytesIO(icon)).convert("RGBA").resize((size, size), Image.LANCZOS)
    framed = Image.new("RGBA", (size + 2 * _BORDER, size + 2 * _BORDER), color)
    framed.paste(ico, (_BORDER, _BORDER), ico)
    return framed


def _compose(
    banner: bytes, icons: list[tuple[bytes, tuple[int, int, int, int]]], grandmaster: bool = False
) -> bytes:
    """Incruste les icônes (carrées, bordées) à droite du bandeau, de droite à
    gauche (focus puis arme de défi), centrées verticalement. `icons` =
    (icône, couleur de bordure). Grand maître : liseré en biais derrière."""
    base = Image.open(BytesIO(banner)).convert("RGBA")
    size = round(base.height * _ICON_HEIGHT)
    margin = round(base.height * _ICON_MARGIN)
    framed = [_bordered(icon, size, color) for icon, color in icons]
    xs, x = [], base.width - margin
    for ico in framed:
        x -= ico.width
        xs.append(x)
        x -= margin // 2
    if grandmaster:
        base = Image.alpha_composite(base, _stripes(base.size, xs[-1]))
    for ico, x in zip(framed, xs):
        base.paste(ico, (x, (base.height - ico.height) // 2), ico)
    base = base.convert("RGB")
    out = BytesIO()
    base.save(out, format="WEBP", quality=90)
    return out.getvalue()


async def _activity_banner(act: PortalActivity, ratio: float) -> bytes | None:
    """Bandeau pgcr recadré, avec les icônes de l'item focus et de l'arme de
    défi incrustées si dispo."""
    if not act.pgcr_image:
        return None
    banner = await get_banner(act.pgcr_image, FEATURE, ratio)
    if banner is None:
        return None
    icons = []
    focus_color = _BORDER_GOLD if act.is_grandmaster else _BORDER_COLOR
    for item, color in ((act.focus, focus_color), (act.challenge, _BORDER_CHALLENGE)):
        if item is None or not item.icon:
            continue
        icon = await get_item_icon(item.item_hash, item.icon, item.watermark, feature=FEATURE)
        if icon:
            icons.append((icon, color))
    if not icons:
        return banner
    return await asyncio.to_thread(_compose, banner, icons, act.is_grandmaster)


# ── Texte ───────────────────────────────────────────────────────────────


def _tags_line(act: PortalActivity, cat_key: str) -> str:
    """Ligne « Alerte de l'Avant-garde (…) », ou '' si aucun tag. L'alerte
    simple est qualifiée par la catégorie (Escouade, Arène)."""
    tags = []
    if act.is_grandmaster:
        tags.append("Alerte de l'Avant-garde (Grand-maître)")
    elif act.is_alert:
        label = ALERT_LABELS.get(cat_key)
        tags.append(f"Alerte de l'Avant-garde ({label})" if label else "Alerte de l'Avant-garde")
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


def _item_lines(label: str, f: FocusItem) -> list[str]:
    """« <label> : item » puis le détail ligne à ligne (set d'armure ou tags d'arme)."""
    if f.sub_type in ARMOR_SUBTYPE_LABELS:
        return [f"{label} : **{f.name}**", *_armor_lines(f)]
    lines = [f"{label} : [**{f.name}**]({LIGHT_GG_BASE}{f.item_hash})"]
    tags = _weapon_tags(f)
    if tags:
        lines.append(tags)
    return lines


def _focus_lines(act: PortalActivity) -> list[str]:
    """Item focus, puis arme de défi de la semaine si l'activité en a une."""
    lines = _item_lines("Focus", act.focus) if act.focus else ["-# Aucun focus détecté."]
    if act.challenge:
        lines += _item_lines("Arme de défi", act.challenge)
    return lines


def _activity_text(act: PortalActivity, cat_key: str) -> ui.TextDisplay:
    title = f"### {act.base_name}"
    if len(act.difficulties) > 1:
        title += f" ({' / '.join(act.difficulties)})"
    lines = [title, _tags_line(act, cat_key), *_focus_lines(act)]
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
        container.add_item(_activity_text(act, cat.key))
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
    reset quotidien par défaut) figure sur chaque message."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_reset().timestamp())
    views = []
    for cat in categories:
        views.append(await _build_category(cat, next_refresh_unix, ratio))
    return views
