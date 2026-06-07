# -*- coding: utf-8 -*-
import aiohttp

from bot.config import BUNGIE_API_KEY
from bot.utils.logger import log

BUNGIE_BASE = "https://www.bungie.net"
PLATFORM_BASE = f"{BUNGIE_BASE}/Platform"


class BungieClient:
    """Couche d'accès à l'API Bungie. Minimal : seul le flux RSS news
    est utilisé pour l'instant. Étendre ici si besoin d'autres endpoints."""

    def __init__(self, api_key: str = BUNGIE_API_KEY):
        self.api_key = api_key
        self._headers = {"X-API-Key": api_key}

    async def get_rss_articles(
        self,
        language: str = "en",
        page_token: str = "0",
        includebody: bool = False,
    ) -> dict | None:
        url = f"{PLATFORM_BASE}/Content/Rss/NewsArticles/{page_token}/"
        params = {
            "lc": language,
            "includebody": "true" if includebody else "false",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                log.error(f"[Bungie] RSS NewsArticles → HTTP {resp.status}")
                return None


# Instance partagée
bungie = BungieClient()