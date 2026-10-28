# -*- coding: utf-8 -*-
"""Briques de mise en page Components V2 partagées par les vues des features.

- StaticView    : LayoutView non interactive et sans timeout (messages publiés).
- chunked()     : découpe une liste d'items en paquets (plafond CV2 par message).
- refresh_line(): ligne « Actualisation: <date> (<relatif>) ».
- item_section(): Section d'un item (texte à gauche, icône composée à droite).
"""
from __future__ import annotations

from io import BytesIO
from typing import Iterator, Sequence, TypeVar

import discord
from discord import ui

from bot.render.item_icon import get_item_icon

T = TypeVar("T")


class StaticView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


def chunked(seq: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Découpe une liste en tranches de `size`."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def refresh_line(unix: int) -> str:
    """« Actualisation: <date complète> (<relatif>) » en timestamps Discord
    (affichés dans le fuseau de chaque utilisateur)."""
    return f"Actualisation: <t:{unix}:F> (<t:{unix}:R>)"


async def item_section(
    item,
    lines: list[str],
    filename: str,
    files: list[discord.File],
    *,
    feature: str | None = None,
) -> ui.Section | None:
    """Section d'un item : `lines` (vides ignorées) à gauche, icône composée
    (icône + watermark, cf. render/item_icon.py) en vignette à droite.

    Ajoute le fichier image à `files`. Renvoie None si l'icône est
    indisponible (l'item est alors ignoré par l'appelant). `feature` choisit le
    sous-dossier de cache (défaut : celui de Xûr)."""
    kwargs = {"feature": feature} if feature else {}
    icon_bytes = await get_item_icon(item.item_hash, item.icon, item.watermark, **kwargs)
    if icon_bytes is None:
        return None
    files.append(discord.File(BytesIO(icon_bytes), filename=filename))
    return ui.Section(
        ui.TextDisplay("\n".join(line for line in lines if line)),
        accessory=ui.Thumbnail(f"attachment://{filename}"),
    )
