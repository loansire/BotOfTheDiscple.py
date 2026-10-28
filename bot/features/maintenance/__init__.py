# -*- coding: utf-8 -*-
"""Service maintenance : fetch → parse → filtre (offline dans le futur)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bot.core.logger import log

from .fetcher import fetch_article_body
from .formatter import (
    extract_window,
    format_discord_message,
    offline_iso,
)
from .models import resolve_game
from .parser import parse_maintenance_events

__all__ = [
    "get_maintenances",
    "extract_window",
    "format_discord_message",
]


def _has_future_offline(event: dict) -> bool:
    iso = offline_iso(event)
    if not iso:
        return False
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return dt > datetime.now(timezone.utc)


async def get_maintenances(
    game: str, only_future: bool = True, known_updated_at: str | None = None
) -> Optional[dict]:
    """Maintenances d'un jeu. Par défaut, ne garde que celles dont la mise
    hors ligne est encore à venir (ignore les fausses alertes passées).

    `known_updated_at` : si l'article n'a pas changé depuis, on saute le parse
    HTML (coûteux, fait chaque minute) et on renvoie `unchanged=True`."""
    game_enum = resolve_game(game)

    body, updated_at = await fetch_article_body(game_enum)
    if body is None:
        log.error(f"[Maintenance] Fetch impossible pour {game_enum.value}")
        return None
    if known_updated_at and updated_at == known_updated_at:
        return {"game": game_enum.value, "article_updated_at": updated_at, "unchanged": True}

    events = [e.to_dict() for e in parse_maintenance_events(body, game_enum)]
    if only_future:
        events = [e for e in events if _has_future_offline(e)]

    return {
        "game": game_enum.value,
        "article_updated_at": updated_at,
        "events_count": len(events),
        "events": events,
    }