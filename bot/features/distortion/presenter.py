# -*- coding: utf-8 -*-
"""Calcul de la publication Distorsion (un message, édité chaque heure).

- en-tête + image pleine largeur de la destination ACTIVE + heure de fin ;
- séparateur ;
- liste des destinations SUIVANTES — cycle complet SANS doublon — chacune
  avec son heure de début.

Les heures sont des timestamps dynamiques Discord (fuseau de chaque
utilisateur). L'image vit dans Ressources/Distortion/<Nom_sans_accents>.png ;
si absente, le message est publié sans image."""
from __future__ import annotations

from datetime import datetime

from bot.compute import mime_of, read_resource
from bot.content.model import Message, Post, image, separator, text
from bot.core.config import RESOURCES_DIR
from bot.features.distortion import TOPIC, DistortionWindow, current_window, upcoming_windows
from bot.features.distortion.constants import DISTORTION_EMOJI, image_filename

ACCENT = 0xA62432  # crimson « distorsion » (couleur du blason)
DISTORTION_DIR = RESOURCES_DIR / "Distortion"


def _active_block(window: DistortionWindow) -> str:
    return (
        f"# {DISTORTION_EMOJI} Distorsion active\n"
        f"## {window.key}\n"
        f"-# Fin : <t:{window.end_unix}:t> (<t:{window.end_unix}:R>)"
    )


def _upcoming_line(window: DistortionWindow) -> str:
    return (
        f"**{window.key}**\n"
        f"-# Début : <t:{window.start_unix}:t> (<t:{window.start_unix}:R>)"
    )


def build_post(now: datetime | None = None) -> Post:
    active = current_window(now)
    message = Message(accent_color=ACCENT).add(text(_active_block(active)))

    path = DISTORTION_DIR / image_filename(active.key)
    data = read_resource(path)
    if data is not None:
        message.add(image("gallery", data, path.name, mime=mime_of(path)))

    message.add(separator()).add(text("# Prochaines distorsions"))
    for window in upcoming_windows(now):
        message.add(text(_upcoming_line(window)))

    return Post(
        TOPIC, "edit", {"default": [message]},
        period_start=active.start, expires_at=active.end,
    )
