# -*- coding: utf-8 -*-
"""Rendu Components V2 de l'Eververse.

Structure de publication (gérée par le handler) :
- Message 1 : « Tess - Poussière brillante »
- Message 2 : « Tess - Poussière brillante (Autre) »

Chaque message = un Container (titre + un séparateur d'en-tête + une `ui.Section`
par item). Chaque Section porte à gauche un `TextDisplay` (nom + éventuel
libellé de classe + éventuelle ligne de coût) et à droite l'icône composée de
l'item en accessoire `ui.Thumbnail`. Les items s'enchaînent SANS séparateur
entre eux ; seul un `ui.Separator` sépare le bloc d'en-tête (titre +
actualisation) du contenu.

Libellé de classe : pour les ornements d'armure (vendor multi-classe), une ligne
« Ornement Titan / Arcaniste / Chasseur » est insérée ENTRE le nom et le coût.

Coût : affiché en Poussière brillante (`currency == "dust"`, DUST_EMOJI +
quantité).

Builder :
- build_eververse_views → liste de (vue, fichiers), une entrée par message. Une
  section qui déborde le plafond CV2 est re-découpée avec un suffixe « (1/2) ».

La publication (post/suppression) est gérée dans le handler."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import next_reset
from bot.embeds.xur_image import get_item_icon
from bot.features.eververse.constants import DUST_EMOJI, TESS_EMOJI
from bot.features.eververse.models import EververseSection

_FEATURE = "eververse"  # sous-dossier de cache d'icônes (banners/eververse/)

# Couleur d'accent (Poussière brillante).
_ACCENT_DUST = discord.Color(0x57C9E6)    # cyan Poussière brillante

# Plafond de sécurité CV2 (40 composants top-level/message). Un item coûte ~2
# composants (Section + Thumbnail ; le TextDisplay est un enfant de la Section),
# les séparateurs inter-items ayant été retirés. On garde de la marge sous 40
# (container + titre + séparateur d'en-tête inclus). Au-delà, la section est
# re-découpée en plusieurs messages avec suffixe.
_MAX_ITEMS_PER_MESSAGE = 10


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


def _cost_line(item) -> str:
    """Ligne de coût d'un item : '<:Dust:…> x1250', ou '' si inconnu."""
    if item.cost_quantity is None:
        return ""
    return f"{DUST_EMOJI} x{item.cost_quantity}"


def _name_line(item) -> str:
    return f"**{item.name}**"


async def _item_section(item, files: list[discord.File]) -> ui.Section | None:
    """Construit la Section d'un item (texte à gauche, vignette à droite).

    Ordre des lignes : nom, (libellé de classe si présent), (coût si connu).
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
    # Libellé de classe (ornements d'armure multi-classe), au-dessus du coût.
    if getattr(item, "class_label", None):
        lines.append(item.class_label)
    cost = _cost_line(item)
    if cost:
        lines.append(cost)

    return ui.Section(
        ui.TextDisplay("\n".join(lines)),
        accessory=ui.Thumbnail(f"attachment://{fname}"),
    )


def _header_text(section: EververseSection, suffix: str, refresh_unix: int | None) -> str:
    """Titre du message (emoji Tess + libellé) + ligne d'actualisation."""
    text = f"# {TESS_EMOJI} {section.title}{suffix}"
    if refresh_unix is not None:
        text += (
            f"\nActualisation: <t:{refresh_unix}:F>"
            f"(<t:{refresh_unix}:R>)"
        )
    return text


async def _build_section_message(
    section: EververseSection, part: int, total: int, refresh_unix: int | None
) -> tuple:
    """Construit (vue, fichiers) pour un paquet d'items d'une section.

    `part`/`total` numérotent les messages si une section déborde le plafond
    (suffixe « (1/2) »). Une section sans item résoluble affiche un repli.

    Les items s'enchaînent sans séparateur entre eux ; seul le séparateur
    d'en-tête (titre + actualisation → contenu) est conservé."""
    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT_DUST)
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    container.add_item(ui.TextDisplay(_header_text(section, suffix, refresh_unix)))
    # Séparation entête (titre + « Actualisation ») → contenu.
    container.add_item(ui.Separator())

    any_item = False
    for item in section.items:
        sec = await _item_section(item, files)
        if sec is None:
            continue
        container.add_item(sec)
        any_item = True

    # Aucun item résoluble → repli (le séparateur d'entête est déjà présent).
    if not any_item:
        container.add_item(ui.TextDisplay("-# Aucun item pour cette rotation."))

    return EververseView(container), files


async def build_eververse_views(
    sections: list[EververseSection],
    next_refresh_unix: int | None = None,
) -> list:
    """Renvoie une LISTE de (vue, fichiers), une entrée par message.

    Normalement 2 messages (un par section, dans l'ordre). Une section qui
    dépasse le plafond CV2 est re-découpée (suffixe « (n/total) »).

    La ligne « Actualisation » (prochain reset quotidien par défaut) apparaît sur
    CHAQUE message (y compris les parties re-découpées d'une même section)."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_reset().timestamp())

    messages: list = []
    for section in sections:
        chunks = list(_chunk(section.items, _MAX_ITEMS_PER_MESSAGE)) or [[]]
        for part, chunk in enumerate(chunks):
            sub = EververseSection(
                id=section.id,
                title=section.title,
                currency=section.currency,
                items=chunk,
            )
            messages.append(
                await _build_section_message(sub, part, len(chunks), next_refresh_unix)
            )
    return messages