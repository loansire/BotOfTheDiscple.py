# -*- coding: utf-8 -*-
"""Rendu Components V2 de Xûr (4 messages).

Structure de publication (gérée par le cog) :
- Message 1 : STATUT — « Xûr est là » / « Xûr n'est pas là » (+ date de
  départ/retour). Persistant : édité in-place, jamais supprimé.
- Messages 2-4 : une CATÉGORIE par message (Armes / Armures / Matériaux),
  supprimés puis republiés.

Rendu d'une catégorie : un Container (titre + une `ui.Section` par item).
Chaque Section porte, à gauche, un `TextDisplay` (nom + ligne de coût
`<:PiecesEtranges:…> x{quantity}`) et, à droite, l'image combinée de l'item en
accessoire `ui.Thumbnail`. Un `ui.Separator` sépare chaque item.

Builders :
- build_xur_status_view  → vue du message statut (présent ou absent).
- build_xur_category_views → liste de (vue, fichiers), une par vendor non vide.

La publication (post/édition/suppression) est gérée dans le cog."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.embeds.xur_image import get_item_icon
from bot.features.xur.models import XurVendor

_ACCENT = discord.Color.gold()

_TITLE = "<:Xur:1516172178905759844>"  # emoji custom Xûr
# Emoji de la monnaie de coût (Pièces étranges).
_PIECES_EMOJI = "<:PiecesEtranges:1516155586755166338>"

# Plafond CV2 : 40 composants top-level par message. Un item « plein » coûte
# 3 composants (Separator + Section + Thumbnail ; le TextDisplay est un enfant
# de la Section). Avec le titre + container on reste très en dessous, mais on
# garde une limite de sécurité par message catégorie.
_MAX_ITEMS_PER_MESSAGE = 9


class XurView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


def _chunk(seq: list, size: int):
    """Découpe une liste en tranches de `size`."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ── Message statut (présent / absent) ──────────────────────────────────


def build_xur_status_view(
    present: bool,
    *,
    departure_unix: int | None = None,
    return_unix: int | None = None,
) -> XurView:
    """Vue du message statut persistant.

    - present=True  → « Xûr est là » + (si departure_unix) date de départ.
    - present=False → « Xûr n'est pas là » + (si return_unix) date de retour.
    """
    container = ui.Container(accent_color=_ACCENT)
    if present:
        text = f"# {_TITLE} XÛR EST LÀ"
        if departure_unix:
            text += (
                f"\nDisponible jusqu'au <t:{departure_unix}:F> "
                f"(<t:{departure_unix}:R>)"
            )
    else:
        text = f"# {_TITLE} XÛR N'EST PAS LÀ"
        if return_unix:
            text += (
                f"\n-# Il reviendra le <t:{return_unix}:F> "
                f"(<t:{return_unix}:R>)"
            )
    container.add_item(ui.TextDisplay(text))
    return XurView(container)


# ── Messages catégories (Armes / Armures / Matériaux) ──────────────────


def _cost_line(item) -> str:
    """Ligne de coût d'un item : '<:PiecesEtranges:…> x29', ou '' si inconnu."""
    if item.cost_quantity is None:
        return ""
    return f"{_PIECES_EMOJI} x{item.cost_quantity}"


def _name_line(item) -> str:
    """Nom de l'item, suffixé '- x{n}' si l'item apparaît en plusieurs cases."""
    name = f"**{item.name}**"
    if getattr(item, "quantity", 1) > 1:
        name += f" - x{item.quantity}"
    return name


async def _item_section(
    item, vendor_key: str, files: list[discord.File]
) -> ui.Section | None:
    """Construit la Section d'un item (texte à gauche, vignette à droite).

    Ajoute le fichier image à `files`. Renvoie None si l'icône composée est
    indisponible (item ignoré)."""
    icon_bytes = await get_item_icon(item.item_hash, item.icon, item.watermark)
    if icon_bytes is None:
        return None

    fname = f"xur_{vendor_key}_{item.item_hash}.webp"
    files.append(discord.File(BytesIO(icon_bytes), filename=fname))

    lines = [_name_line(item)]
    cost = _cost_line(item)
    if cost:
        lines.append(cost)

    return ui.Section(
        ui.TextDisplay("\n".join(lines)),
        accessory=ui.Thumbnail(f"attachment://{fname}"),
    )


async def _build_vendor_message(vendor: XurVendor, part: int, total: int) -> tuple:
    """Construit (vue, fichiers) pour un paquet d'items d'un vendor.

    `part`/`total` numérotent les messages si un vendor déborde le plafond
    (suffixe « (1/2) »). En pratique Xûr tient toujours sur un seul message
    par catégorie."""
    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT)
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    container.add_item(ui.TextDisplay(f"## {vendor.emoji} {vendor.label}{suffix}"))

    first = True
    for item in vendor.items:
        section = await _item_section(item, vendor.key, files)
        if section is None:
            continue
        if not first:
            container.add_item(ui.Separator())
        container.add_item(section)
        first = False

    # Aucun item résoluble dans ce paquet → pas de message.
    if first:
        return None
    return XurView(container), files


async def build_xur_category_views(vendors: list) -> list:
    """Renvoie une LISTE de (vue, fichiers), une entrée par message catégorie.

    Un vendor = un message (re-découpé seulement s'il dépasse le plafond de
    sécurité). Les vendors sans item sont ignorés."""
    messages: list = []
    for vendor in vendors:
        if not vendor.items:
            continue
        chunks = list(_chunk(vendor.items, _MAX_ITEMS_PER_MESSAGE))
        for part, chunk in enumerate(chunks):
            sub = XurVendor(
                key=vendor.key,
                label=vendor.label,
                emoji=vendor.emoji,
                items=chunk,
            )
            built = await _build_vendor_message(sub, part, len(chunks))
            if built:
                messages.append(built)
    return messages