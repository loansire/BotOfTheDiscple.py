# -*- coding: utf-8 -*-
"""Rendu Components V2 de Xûr (multi-message).

Contrainte Discord : 10 fichiers (images) max par message. Comme Xûr peut
afficher plus de 10 items au total, on poste PLUSIEURS messages :
- 1 message par vendor (Armes / Ressources / Armures) ;
- si un vendor dépasse 10 images, il est re-découpé en paquets de 10.

build_xur_views renvoie une LISTE de (vue, fichiers), une entrée par message.
Le PREMIER message porte l'en-tête global « Xûr est là » ; le ping rôle (géré
par le cog) n'est ajouté qu'à ce premier message.

build_xur_departed_view : message « Xûr est parti », édité in-place le mardi
(pas de repost -> pas de notification).
"""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.embeds.xur_image import get_item_icon
from bot.features.xur.models import XurVendor

_ACCENT = discord.Color.gold()

# Limite dure Discord : 10 fichiers attachés par message.
_FILES_PER_MESSAGE = 10
# MediaGallery : 10 items max par composant.
_GALLERY_MAX = 10

_TITLE = "<:Xur:1270042203577778246>"  # emoji custom Xûr (ajuste l'ID au besoin)


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


async def _vendor_galleries(
    vendor: XurVendor, files: list, start_index: int
) -> list:
    """Construit les MediaGalleryItem d'un vendor + ajoute les fichiers.

    `start_index` sert à nommer les fichiers de façon unique au sein du
    message courant. Renvoie la liste de MediaGalleryItem."""
    gallery_items = []
    for item in vendor.items:
        icon_bytes = await get_item_icon(item.item_hash, item.icon, item.watermark)
        if icon_bytes is None:
            continue
        fname = f"xur_{vendor.key}_{item.item_hash}.webp"
        files.append(discord.File(BytesIO(icon_bytes), filename=fname))
        gallery_items.append(
            discord.MediaGalleryItem(f"attachment://{fname}", description=item.name)
        )
    return gallery_items


async def _build_vendor_messages(
    vendor: XurVendor, header: str | None
) -> list:
    """Un vendor -> 1+ messages (vue, fichiers). Re-découpe en paquets de 10
    images si le vendor dépasse la limite. `header` (optionnel) est un
    TextDisplay placé en tête du tout premier message global."""
    # Résolution des icônes une seule fois (dans un buffer de fichiers commun
    # qu'on redécoupera ensuite par paquets de 10).
    all_files: list = []
    gallery_items = await _vendor_galleries(vendor, all_files, 0)

    messages: list = []
    if not gallery_items:
        return messages

    # Découpe items ET fichiers en paquets alignés de 10.
    item_chunks = list(_chunk(gallery_items, _FILES_PER_MESSAGE))
    file_chunks = list(_chunk(all_files, _FILES_PER_MESSAGE))

    for part, (items_part, files_part) in enumerate(zip(item_chunks, file_chunks)):
        children: list = []
        # En-tête global seulement sur le tout premier message (part 0 + header).
        if header and part == 0:
            children.append(ui.TextDisplay(header))

        container = ui.Container(accent_color=_ACCENT)
        suffix = "" if len(item_chunks) == 1 else f" ({part + 1}/{len(item_chunks)})"
        container.add_item(ui.TextDisplay(f"## {vendor.emoji} {vendor.label}{suffix}"))
        for gchunk in _chunk(items_part, _GALLERY_MAX):
            container.add_item(ui.MediaGallery(*gchunk))
        children.append(container)

        messages.append((XurView(*children), files_part))

    return messages


async def build_xur_views(
    vendors: list, departure_unix: int | None = None
) -> list:
    """Renvoie une LISTE de (vue, fichiers), un par message à poster.

    Le tout premier message porte l'en-tête « Xûr est là » (+ date de départ).
    Chaque vendor occupe au moins un message ; un vendor de plus de 10 items
    est réparti sur plusieurs messages."""
    header = f"# {_TITLE} Xûr est là !"
    if departure_unix:
        header += (
            f"\n-# Disponible jusqu'au <t:{departure_unix}:F> "
            f"(<t:{departure_unix}:R>)"
        )

    messages: list = []
    first = True
    for vendor in vendors:
        if not vendor.items:
            continue
        vendor_msgs = await _build_vendor_messages(
            vendor, header if first else None
        )
        if vendor_msgs:
            messages.extend(vendor_msgs)
            first = False

    # Repli : rien à afficher -> un unique message d'information.
    if not messages:
        fallback = ui.Container(accent_color=_ACCENT)
        fallback.add_item(ui.TextDisplay(
            f"# {_TITLE} Xûr est là !\n"
            "-# Impossible de récupérer son inventaire pour le moment."
        ))
        messages.append((XurView(fallback), []))

    return messages


def build_xur_departed_view(return_unix: int) -> XurView:
    """Vue « Xûr est parti » (éditée in-place le mardi, sans fichiers)."""
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(
        f"# {_TITLE} Xûr est reparti\n"
        f"Il reviendra le <t:{return_unix}:F> (<t:{return_unix}:R>)."
    ))
    return XurView(container)