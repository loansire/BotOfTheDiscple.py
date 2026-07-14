# -*- coding: utf-8 -*-
"""Rendu Components V2 de l'Eververse (3 messages).

Structure de publication (gérée par le handler, Lot 3) :
- Message 1 : « Offre de Poussière brillante (principales) »
- Message 2 : « Offre de Poussière brillante (autres) »
- Message 3 : « Offres d'Argentum »

Chaque message = un Container (titre + une `ui.Section` par item). Chaque Section
porte à gauche un `TextDisplay` (nom + éventuelle ligne de coût) et à droite
l'icône composée de l'item en accessoire `ui.Thumbnail`. Un `ui.Separator`
sépare les items. Contrairement à la page web, il n'y a PAS de sous-titre par
sous-catégorie : les items s'enchaînent, dans l'ordre défini par SECTIONS.

Coût : affiché UNIQUEMENT pour les sections en Poussière brillante
(`currency == "dust"`, avec DUST_EMOJI + quantité). Les sections en Argentum
(`currency == "silver"`) n'affichent AUCUN coût.

Builder :
- build_eververse_views → liste de (vue, fichiers), une entrée par message
  (normalement 3 ; une section qui déborde le plafond CV2 est re-découpée avec
  un suffixe « (1/2) », comme Xûr).

La publication (post/suppression) est gérée dans le handler."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import next_reset
from bot.embeds.xur_image import get_item_icon
from bot.features.eververse.constants import DUST_EMOJI
from bot.features.eververse.models import EververseSection

_FEATURE = "eververse"  # sous-dossier de cache d'icônes (banners/eververse/)

# Couleurs d'accent par monnaie (cohérentes avec la page web).
_ACCENT_DUST = discord.Color(0x57C9E6)    # cyan Poussière brillante
_ACCENT_SILVER = discord.Color(0xC0C6D0)  # argent

# Plafond de sécurité CV2 (40 composants top-level/message). Un item « plein »
# coûte ~4 composants (Separator + Section + TextDisplay + Thumbnail). On garde
# de la marge sous 40 (container + titre inclus). Au-delà, la section est
# re-découpée en plusieurs messages avec suffixe.
_MAX_ITEMS_PER_MESSAGE = 9


class EververseView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


def _chunk(seq: list, size: int):
    """Découpe une liste en tranches de `size`."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _accent(currency: str) -> discord.Color:
    return _ACCENT_SILVER if currency == "silver" else _ACCENT_DUST


def _cost_line(item) -> str:
    """Ligne de coût d'un item.

    - Poussière brillante (dust) : '<:Dust:…> x1250'.
    - Argentum (silver) : chaîne vide (coût jamais affiché, cf. spéc).
    """
    if item.currency != "dust" or item.cost_quantity is None:
        return ""
    return f"{DUST_EMOJI} x{item.cost_quantity}"


def _name_line(item) -> str:
    return f"**{item.name}**"


async def _item_section(item, files: list[discord.File]) -> ui.Section | None:
    """Construit la Section d'un item (texte à gauche, vignette à droite).

    Ajoute le fichier image à `files`. Renvoie None si l'icône composée est
    indisponible (item ignoré)."""
    icon_bytes = await get_item_icon(
        item.item_hash, item.icon, item.watermark, feature=_FEATURE
    )
    if icon_bytes is None:
        return None

    fname = f"ev_{len(files)}.webp"
    files.append(discord.File(BytesIO(icon_bytes), filename=fname))

    lines = [_name_line(item)]
    cost = _cost_line(item)
    if cost:
        lines.append(cost)

    return ui.Section(
        ui.TextDisplay("\n".join(lines)),
        accessory=ui.Thumbnail(f"attachment://{fname}"),
    )


def _header_text(section: EververseSection, suffix: str, refresh_unix: int | None) -> str:
    """Titre du message + (sur le 1er message seulement) ligne d'actualisation."""
    text = f"# {section.title}{suffix}"
    if refresh_unix is not None:
        text += (
            f"\nProchaine actualisation le <t:{refresh_unix}:F> "
            f"(<t:{refresh_unix}:R>)"
        )
    return text


async def _build_section_message(
    section: EververseSection, part: int, total: int, refresh_unix: int | None
) -> tuple:
    """Construit (vue, fichiers) pour un paquet d'items d'une section.

    `part`/`total` numérotent les messages si une section déborde le plafond
    (suffixe « (1/2) »). Une section sans item résoluble affiche un repli."""
    files: list[discord.File] = []
    container = ui.Container(accent_color=_accent(section.currency))
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    container.add_item(ui.TextDisplay(_header_text(section, suffix, refresh_unix)))

    first = True
    for item in section.items:
        sec = await _item_section(item, files)
        if sec is None:
            continue
        if not first:
            container.add_item(ui.Separator())
        container.add_item(sec)
        first = False

    # Aucun item résoluble → repli (on garde le message pour rester à 3).
    if first:
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("-# Aucun item pour cette rotation."))

    return EververseView(container), files


async def build_eververse_views(
    sections: list[EververseSection],
    next_refresh_unix: int | None = None,
) -> list:
    """Renvoie une LISTE de (vue, fichiers), une entrée par message.

    Normalement 3 messages (un par section, dans l'ordre). Une section qui
    dépasse le plafond CV2 est re-découpée (suffixe « (n/total) »).

    La ligne « Prochaine actualisation » (prochain reset quotidien par défaut)
    n'apparaît que sur le tout premier message."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_reset().timestamp())

    messages: list = []
    first_message = True
    for section in sections:
        chunks = list(_chunk(section.items, _MAX_ITEMS_PER_MESSAGE)) or [[]]
        for part, chunk in enumerate(chunks):
            sub = EververseSection(
                id=section.id,
                title=section.title,
                currency=section.currency,
                items=chunk,
            )
            refresh = next_refresh_unix if first_message else None
            messages.append(await _build_section_message(sub, part, len(chunks), refresh))
            first_message = False
    return messages