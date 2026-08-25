# -*- coding: utf-8 -*-
"""Rendu Components V2 de la rotation prédictive (raids / donjons).

Vue ÉPHÉMÈRE, construite à la demande sur clic de bouton. Pure couche de rendu :
elle reçoit les groupes déjà fetchés et délègue tout le calcul à
features.weekly.rotation.

Budget CV2 : 1 Container + 3 TextDisplay (le tableau tient dans un seul bloc
multi-lignes). Aucun fichier joint, aucune image → réponse quasi instantanée.

Dates : rendues via <t:…:d>, donc localisées par le client Discord de chaque
utilisateur (25/08/2026 en FR, 08/25/2026 en US) sans travail côté bot.
"""
from __future__ import annotations

from datetime import datetime

import discord
from discord import ui

from bot.embeds.activity_emojis import (
    DJ_EMOJI,
    RD_EMOJI,
    activity_emoji_for,
)
from bot.features.weekly.models import WeeklyActivity
from bot.features.weekly.rotation import (
    DUNGEON_SEQUENCE,
    RAID_SEQUENCE,
    predict_rotation,
)

_ACCENT = discord.Color.dark_red()

# kind → (activity_type, séquence, emoji de titre, libellé)
_SPECS = {
    "raid": ("Raid", RAID_SEQUENCE, RD_EMOJI, "Raids"),
    "dungeon": ("Donjon", DUNGEON_SEQUENCE, DJ_EMOJI, "Donjons"),
}


class RotationView(ui.LayoutView):
    """LayoutView éphémère non interactive (pas de bouton dans la réponse)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


def _featured_rotation_names(
    groups: list[WeeklyActivity], activity_type: str
) -> list[str]:
    """Noms des activités featured EN ROTATION du type demandé.

    Les activités permanentes (contenu le plus récent, toujours disponible) sont
    exclues : elles ne participent pas au cycle et fausseraient l'ancrage."""
    return [
        g.base_name
        for g in groups
        if g.featured and g.activity_type == activity_type and not g.permanent
    ]


def _slot_label(name: str, activity_type: str) -> str:
    return f"{activity_emoji_for(name, activity_type)} {name}"


def _rotation_lines(
    cycle: list[tuple[int, tuple[str, ...]]], activity_type: str
) -> str:
    """Tableau du cycle : une ligne par semaine, la semaine en cours en gras."""
    lines: list[str] = []
    for week, (ts, names) in enumerate(cycle):
        slots = "  •  ".join(_slot_label(n, activity_type) for n in names)
        if week == 0:
            lines.append(f"**➜ <t:{ts}:d> — {slots}**")
        else:
            lines.append(f"<t:{ts}:d> — {slots}")
    return "\n".join(lines)


def build_rotation_view(
    kind: str,
    groups: list[WeeklyActivity],
    now: datetime | None = None,
) -> RotationView:
    """Vue éphémère du cycle complet pour `kind` ('raid' ou 'dungeon')."""
    activity_type, sequence, title_emoji, label = _SPECS[kind]

    container = ui.Container(accent_color=_ACCENT)
    container.add_item(
        ui.TextDisplay(f"# {title_emoji} Rotation prédictive - {label}")
    )

    names = _featured_rotation_names(groups, activity_type)
    cycle = predict_rotation(names, sequence, now) if names else None

    if cycle is None:
        container.add_item(ui.TextDisplay(
            "-# Impossible d'ancrer la prédiction sur la semaine en cours "
            "(activité inconnue de la séquence de rotation).\n"
            "-# La publication hebdomadaire ci-dessus reste, elle, fiable : "
            "elle vient directement de l'API Bungie."
        ))
        return RotationView(container)

    container.add_item(ui.TextDisplay(
        f"-# Cycle complet · {len(cycle)} semaines · "
        f"{len(cycle[0][1])} activités en rotation"
    ))
    container.add_item(ui.Separator())
    container.add_item(ui.TextDisplay(_rotation_lines(cycle, activity_type)))
    container.add_item(ui.Separator())
    container.add_item(ui.TextDisplay(
        "-# Prédiction déterministe, il est possible que les données ne soient pas exacte en cas de bug ou de doublon d'une semaine à l'autre."
    ))

    return RotationView(container)