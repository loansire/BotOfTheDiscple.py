# -*- coding: utf-8 -*-
"""Rendu Components V2 de la Distorsion.

Un unique message persistant, ÉDITÉ en place chaque heure (aucun ping) :
- en-tête + image pleine largeur de la destination ACTIVE + heure de fin ;
- séparateur ;
- liste (avec séparateurs) des destinations SUIVANTES — cycle complet SANS
  doublon — chacune avec son heure de début.

Les heures sont rendues en timestamps dynamiques Discord (fuseau de chaque
utilisateur). L'image vit dans Ressources/Distortion/<Nom_sans_accents>.png ;
si absente, on affiche le texte sans image (placeholder tolérant)."""
from __future__ import annotations

import discord
from discord import ui

from bot.config import RESOURCES_DIR
from bot.features.distortion import (
    DistortionWindow,
    current_window,
    upcoming_windows,
)
from bot.features.distortion.constants import DISTORTION_EMOJI, image_filename

_ACCENT = discord.Color(0xA62432)  # crimson « distorsion » (couleur du blason)
DISTORTION_DIR = RESOURCES_DIR / "Distortion"


class DistortionView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, container: ui.Container):
        super().__init__(timeout=None)
        self.add_item(container)


def _image_file(destination: str) -> discord.File | None:
    fname = image_filename(destination)
    path = DISTORTION_DIR / fname
    if path.is_file():
        return discord.File(path, filename=fname)
    return None


def _active_block(window: DistortionWindow) -> str:
    return (
        f"# {DISTORTION_EMOJI} Distorsion active\n"
        f"## {window.destination}\n"
        f"-# Fin : <t:{window.end_unix}:t> (<t:{window.end_unix}:R>)"
    )


def _upcoming_line(window: DistortionWindow) -> str:
    return (
        f"**{window.destination}**\n"
        f"-# Début : <t:{window.start_unix}:t> (<t:{window.start_unix}:R>)"
    )


def content_hash(now=None) -> str:
    """Identité du contenu = numéro d'heure absolu de la distorsion active.
    Change à chaque changement d'heure → déclenche l'édition du message."""
    return f"distortion:{current_window(now).index}"


def build_distortion_view(now=None) -> tuple[DistortionView, list[discord.File]]:
    """Construit (vue, fichiers NEUFS) pour l'état de distorsion à `now`.

    Un discord.File est consommé après envoi : renvoyer des File neufs à chaque
    appel est indispensable."""
    active = current_window(now)
    nexts = upcoming_windows(now)

    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(_active_block(active)))

    img = _image_file(active.destination)
    if img is not None:
        files.append(img)
        container.add_item(
            ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{img.filename}"))
        )

    container.add_item(ui.Separator())
    container.add_item(ui.TextDisplay("# Prochaines distorsions"))
    for w in nexts:
        container.add_item(ui.TextDisplay(_upcoming_line(w)))

    return DistortionView(container), files