# -*- coding: utf-8 -*-
"""Rendu Components V2 d'Ada-1 (1 message).

Structure de publication (gérée par le handler) :
- 1 message : titre « Ada-1 » + ligne d'actualisation, puis une `ui.Section` par
  item. Re-découpé en plusieurs messages seulement si le plafond CV2 est dépassé
  (suffixe « (1/2) », comme Xûr/Eververse).

Chaque Section porte à gauche un `TextDisplay` (nom + ligne de coût Glimmer) et à
droite l'icône composée de l'item en accessoire `ui.Thumbnail`. Un `ui.Separator`
sépare les items.

Ada-1 étant un vendor PERMANENT, PAS de message statut ni d'image d'en-tête
(largeIcon) : juste le message de contenu.

Coût : toujours affiché (DUST/Glimmer), avec GLIMMER_EMOJI + quantité, sauf si
la quantité est inconnue.

Builder :
- build_ada_view → liste de (vue, fichiers), normalement 1 entrée.

La publication (post/suppression) est gérée dans le handler."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import TUESDAY, next_weekday_reset
from bot.embeds.xur_image import get_item_icon
from bot.features.ada.constants import ADA_EMOJI, ADA_LABEL, GLIMMER_EMOJI
from bot.features.ada.models import AdaItem

_FEATURE = "ada"  # sous-dossier de cache d'icônes (banners/ada/)
_ACCENT = discord.Color.dark_gold()

# Plafond de sécurité CV2 (40 composants top-level/message). Un item « plein »
# coûte ~3 composants (Separator + Section + Thumbnail). On garde de la marge
# sous 40 (container + titre + séparateur d'entête inclus).
_MAX_ITEMS_PER_MESSAGE = 9


class AdaView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


def _chunk(seq: list, size: int):
    """Découpe une liste en tranches de `size`."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _cost_line(item: AdaItem) -> str:
    """Ligne de coût Glimmer : '<:Glimer:…> x25000', ou '' si inconnu."""
    if item.cost_quantity is None:
        return ""
    return f"{GLIMMER_EMOJI} x{item.cost_quantity}"


def _name_line(item: AdaItem) -> str:
    return f"**{item.name}**"


async def _item_section(item: AdaItem, files: list[discord.File]) -> ui.Section | None:
    """Construit la Section d'un item (texte à gauche, vignette à droite).

    Ajoute le fichier image à `files`. Renvoie None si l'icône composée est
    indisponible (item ignoré)."""
    icon_bytes = await get_item_icon(
        item.item_hash, item.icon, item.watermark, feature=_FEATURE
    )
    if icon_bytes is None:
        return None

    fname = f"ada_{item.item_hash}.webp"
    files.append(discord.File(BytesIO(icon_bytes), filename=fname))

    lines = [_name_line(item)]
    cost = _cost_line(item)
    if cost:
        lines.append(cost)

    return ui.Section(
        ui.TextDisplay("\n".join(lines)),
        accessory=ui.Thumbnail(f"attachment://{fname}"),
    )


def _header_text(suffix: str, refresh_unix: int | None) -> str:
    """Titre du message + (sur le 1er message seulement) ligne d'actualisation."""
    text = f"# {ADA_EMOJI} {ADA_LABEL}{suffix}"
    if refresh_unix is not None:
        text += (
            f"\nActualisation: <t:{refresh_unix}:F> "
            f"(<t:{refresh_unix}:R>)"
        )
    return text


async def _build_message(
    items: list[AdaItem], part: int, total: int, refresh_unix: int | None
) -> tuple:
    """Construit (vue, fichiers) pour un paquet d'items.

    `part`/`total` numérotent les messages si Ada déborde le plafond (suffixe
    « (1/2) »). En pratique Ada tient toujours sur un seul message."""
    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT)
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    container.add_item(ui.TextDisplay(_header_text(suffix, refresh_unix)))
    # Séparation entête (titre + actualisation) → contenu.
    container.add_item(ui.Separator())

    first = True
    for item in items:
        section = await _item_section(item, files)
        if section is None:
            continue
        if not first:
            container.add_item(ui.Separator())
        container.add_item(section)
        first = False

    # Aucun item résoluble → repli (le séparateur d'entête est déjà présent).
    if first:
        container.add_item(ui.TextDisplay("-# Aucun item pour cette rotation."))

    return AdaView(container), files


async def build_ada_view(
    items: list[AdaItem],
    next_refresh_unix: int | None = None,
) -> list:
    """Renvoie une LISTE de (vue, fichiers), normalement 1 entrée.

    La ligne « Actualisation » (prochain reset du mardi par défaut, Ada changeant
    à l'hebdo) n'apparaît que sur le tout premier message. Une liste qui dépasse
    le plafond CV2 est re-découpée (suffixe « (n/total) »)."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_weekday_reset(TUESDAY).timestamp())

    chunks = list(_chunk(items, _MAX_ITEMS_PER_MESSAGE)) or [[]]
    messages: list = []
    for part, chunk in enumerate(chunks):
        refresh = next_refresh_unix if part == 0 else None
        messages.append(await _build_message(chunk, part, len(chunks), refresh))
    return messages