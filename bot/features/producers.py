# -*- coding: utf-8 -*-
"""Branchement du calcul sur les publications (bot live uniquement).

Chaque handler de feature enregistre son étape de calcul à l'import
(bot/publishing/producers.py). load() importe tous ces handlers : à appeler
une fois au démarrage du bot qui calcule, avant toute publication."""
from __future__ import annotations

import importlib

_HANDLERS = (
    "bot.features.ada.handler",
    "bot.features.ascendant.handler",
    "bot.features.distortion.handler",
    "bot.features.eververse.handler",
    "bot.features.vanguard.handler",
    "bot.features.weekly.handler",
    "bot.features.xur.handler",
)


def load() -> None:
    for name in _HANDLERS:
        importlib.import_module(name)
