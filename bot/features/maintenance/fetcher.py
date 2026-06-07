# -*- coding: utf-8 -*-
"""Récupère les articles Server Status depuis l'API Zendesk."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import aiohttp

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


async def _fetch_article_raw(game: Game) -> Optional[dict]:
    cfg = ARTICLES[game]
    url = (
        f"{cfg['base_url']}/api/v2/help_center"
        f"/{cfg['locale']}/articles/{cfg['article_id']}.json"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.error("Erreur HTTP %d pour %s (%s)", resp.status, game.value, url)
                    return None
                data = await resp.json()
                return data.get("article")
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error("Erreur réseau pour %s : %s", game.value, e)
        return None


async def fetch_article_body(game: Game) -> tuple[Optional[str], Optional[str]]:
    """Renvoie (body_html, updated_at_iso). (None, None) en cas d'erreur."""
    article = await _fetch_article_raw(game)
    if article is None:
        return None, None
    return article.get("body"), article.get("updated_at")