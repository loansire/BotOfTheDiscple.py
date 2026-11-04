# -*- coding: utf-8 -*-
"""Récupère les articles Server Status depuis l'API Zendesk."""
from __future__ import annotations

import logging
import time
from typing import Optional

import aiohttp

from bot.core.http import NETWORK_ERRORS, get_session

from .models import Game

logger = logging.getLogger(__name__)

ARTICLES = {
    Game.DESTINY: {
        "base_url": "https://help.bungie.net",
        "article_id": 360049199271,
        "locale": "en-us",
    },
    Game.MARATHON: {
        "base_url": "https://help.marathonthegame.com",
        "article_id": 39001626488596,
        "locale": "en-us",
    },
}


def is_rate_limited(game: Game) -> bool:
    """True tant qu'un 429 récent impose de ne pas interroger ce jeu."""
    return time.monotonic() < _blocked_until.get(game, 0.0)


def _retry_after(resp: aiohttp.ClientResponse) -> int:
    try:
        seconds = int(resp.headers.get("Retry-After", ""))
    except ValueError:
        seconds = DEFAULT_BACKOFF
    return max(MIN_BACKOFF, min(seconds, MAX_BACKOFF))


# Pause après un 429 (secondes) : Retry-After si fourni, borné à [MIN, MAX].
DEFAULT_BACKOFF = 300
MIN_BACKOFF = 60
MAX_BACKOFF = 3600
_blocked_until: dict[Game, float] = {}  # time.monotonic() de reprise, par jeu


async def _fetch_article_raw(game: Game) -> Optional[dict]:
    if is_rate_limited(game):
        return None
    cfg = ARTICLES[game]
    url = (
        f"{cfg['base_url']}/api/v2/help_center"
        f"/{cfg['locale']}/articles/{cfg['article_id']}.json"
    )
    try:
        async with get_session().get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 429:
                delay = _retry_after(resp)
                _blocked_until[game] = time.monotonic() + delay
                logger.warning(
                    "HTTP 429 pour %s : requêtes suspendues %d s (Retry-After)", game.value, delay
                )
                return None
            if resp.status != 200:
                logger.error("Erreur HTTP %d pour %s (%s)", resp.status, game.value, url)
                return None
            data = await resp.json(content_type=None)
            return data.get("article") if isinstance(data, dict) else None
    except (*NETWORK_ERRORS, ValueError) as e:
        logger.error("Erreur réseau pour %s : %s", game.value, e)
        return None


async def fetch_article_body(game: Game) -> tuple[Optional[str], Optional[str]]:
    """Renvoie (body_html, updated_at_iso). (None, None) en cas d'erreur."""
    article = await _fetch_article_raw(game)
    if article is None:
        return None, None
    return article.get("body"), article.get("updated_at")