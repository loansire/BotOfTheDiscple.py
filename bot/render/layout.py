# -*- coding: utf-8 -*-
"""Briques de mise en page Components V2 partagées par les vues des features.

- StaticView    : LayoutView non interactive et sans timeout (messages publiés).
- chunked()     : découpe une liste d'items en paquets (plafond CV2 par message).
- refresh_line(): ligne « Actualisation: <date> (<relatif>) ».
"""
from __future__ import annotations

from typing import Iterator, Sequence, TypeVar

from discord import ui

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

