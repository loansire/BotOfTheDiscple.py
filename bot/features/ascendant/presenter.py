# -*- coding: utf-8 -*-
"""Calcul de la publication Défis ascendants (un message, édité chaque semaine).

En-tête + défi ACTIF (secteur, type d'entrée, malédiction, position de Petra)
+ fin de semaine, puis image pleine largeur optionnelle.

Les heures sont des timestamps dynamiques Discord. L'image vit dans
Ressources/Ascendant/<clé>.png ; si absente, placeholder.png ; sinon le
message est publié sans image.

hash_contrat optionnel : contrat Petra (composant 402) passé en override de
validation. None → résolution par la formule déterministe."""
from __future__ import annotations

from datetime import datetime

from bot.compute import mime_of, read_resource
from bot.content.model import Message, Post, image, text
from bot.core.config import RESOURCES_DIR
from bot.features.ascendant import TOPIC, AscendantWindow, resolve
from bot.features.ascendant.constants import ASCENDANT_EMOJI, image_filename

ACCENT = 0x7A5FB8  # violet « ascendant » (plan Ascendant)
ASCENDANT_DIR = RESOURCES_DIR / "Ascendant"

_MALEDICTION_LABEL = {
    "faible": "Faible",
    "croissante": "Croissante",
    "forte": "Forte",
}


def _active_block(meta: dict, win: AscendantWindow) -> str:
    malediction = _MALEDICTION_LABEL.get(meta["malediction"], meta["malediction"])
    return (
        f"# {ASCENDANT_EMOJI} Défi ascendant de la semaine\n"
        f"## {meta['nom']}\n"
        f"**Lieu :** {meta['secteur']} - *{meta['entree']}*\n"
        f"**Malédiction :** {malediction}"
        f"  •  **Petra :** {meta['petra']}\n"
        f"-# Actualisation : <t:{win.end_unix}:F> (<t:{win.end_unix}:R>)"
    )


def build_post(now: datetime | None = None, hash_contrat: int | None = None) -> Post:
    state = resolve(hash_contrat, now)
    win: AscendantWindow = state["window"]
    message = Message(accent_color=ACCENT).add(text(_active_block(state, win)))

    for fname in (image_filename(state["cle"]), "placeholder.png"):
        path = ASCENDANT_DIR / fname
        data = read_resource(path)
        if data is not None:
            message.add(image("gallery", data, path.name, mime=mime_of(path)))
            break

    return Post(
        TOPIC, "edit", {"default": [message]},
        period_start=win.start, expires_at=win.end,
    )
