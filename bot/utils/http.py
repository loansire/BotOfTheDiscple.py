# -*- coding: utf-8 -*-
"""Session HTTP aiohttp partagée par tout le bot.

Une seule ClientSession (pool de connexions + cache DNS/TLS) au lieu d'une
session par requête. Créée paresseusement au premier appel (il faut une boucle
asyncio active) et fermée à l'arrêt du bot (cf. Main.py).

Timeout par défaut : 30 s au total. Sans timeout explicite, aiohttp attend
jusqu'à 300 s, ce qui figerait la pipeline sur une requête pendante. Les gros
téléchargements (définitions du manifest) passent leur propre timeout."""
from __future__ import annotations

import aiohttp

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Erreurs réseau « transitoires » à traiter comme une indisponibilité.
NETWORK_ERRORS = (aiohttp.ClientError, TimeoutError)

_session: aiohttp.ClientSession | None = None


def get_session() -> aiohttp.ClientSession:
    """Session partagée (recréée si elle a été fermée)."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
    return _session


async def close_session() -> None:
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None
