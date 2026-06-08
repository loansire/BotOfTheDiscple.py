# -*- coding: utf-8 -*-
import json
from datetime import datetime

import aiohttp

from bot.bungie.reset import last_reset
from bot.config import BUNGIE_API_KEY, BUNGIE_CHARACTER, MANIFEST_DIR
from bot.utils.logger import log

BUNGIE_BASE = "https://www.bungie.net"
PLATFORM_BASE = f"{BUNGIE_BASE}/Platform"

# Cache disque des activités du personnage de référence.
_CHARACTER_CACHE = MANIFEST_DIR / "character_activities.json"


def _load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class BungieClient:
    """Couche d'accès à l'API Bungie.

    Au-delà du flux RSS news, expose de quoi alimenter les features
    weekly/daily : index du manifest, téléchargement des définitions, et
    activités disponibles du personnage de référence (avec cache aligné
    sur le reset quotidien)."""

    def __init__(self, api_key: str = BUNGIE_API_KEY):
        self.api_key = api_key
        self._headers = {"X-API-Key": api_key}

    # ── Bas niveau ────────────────────────────────────────────────────
    async def _get(self, endpoint: str, params: dict | None = None) -> dict | None:
        """GET générique sur /Platform. Renvoie le JSON complet ou None."""
        url = f"{PLATFORM_BASE}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers, params=params) as resp:
                if resp.status != 200:
                    log.error(f"[Bungie] GET {endpoint} → HTTP {resp.status}")
                    return None
                data = await resp.json(content_type=None)

        status = data.get("ErrorStatus")
        if status and status != "Success":
            log.error(f"[Bungie] {endpoint} → {status} ({data.get('Message')})")
            return None
        return data

    # ── RSS News (inchangé) ───────────────────────────────────────────
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

    # ── Manifest ──────────────────────────────────────────────────────
    async def get_manifest_index(self, lang: str = "fr") -> tuple[str, dict] | None:
        """Renvoie (version, jsonWorldComponentContentPaths[lang]) ou None."""
        data = await self._get("/Destiny2/Manifest/")
        if not data or "Response" not in data:
            return None

        resp = data["Response"]
        version = resp.get("version")
        paths = resp.get("jsonWorldComponentContentPaths", {}).get(lang, {})
        if not version or not paths:
            log.error(f"[Bungie] Index manifest incomplet (lang={lang}).")
            return None
        return version, paths

    async def download_definition(self, path: str) -> dict | None:
        """Télécharge un fichier de définition (hébergé sur bungie.net)."""
        url = f"{BUNGIE_BASE}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(f"[Bungie] DL définition → HTTP {resp.status} ({path})")
                    return None
                return await resp.json(content_type=None)

    # ── Activités du personnage de référence ─────────────────────────
    async def get_character_activities(self, *, force: bool = False) -> dict | None:
        """Bloc `Response` du profil (components=204) : availableActivities
        + availableActivityInteractables.

        Cache aligné sur le reset : les données restent valides jusqu'au
        prochain reset quotidien. `force=True` ignore le cache."""
        if not force:
            cached = _load_json(_CHARACTER_CACHE)
            if cached:
                try:
                    cached_reset = datetime.fromisoformat(cached["reset"])
                except (KeyError, ValueError, TypeError):
                    cached_reset = None
                if cached_reset and cached_reset >= last_reset():
                    log.debug("[Bungie] Activités personnage servies depuis le cache.")
                    return cached.get("data")

        c = BUNGIE_CHARACTER
        endpoint = (
            f"/Destiny2/{c['membership_type']}/Profile/{c['membership_id']}"
            f"/Character/{c['character_id']}/"
        )
        data = await self._get(endpoint, params={"components": "204"})
        if not data or "Response" not in data:
            log.error("[Bungie] Récupération des activités personnage impossible.")
            return None

        response = data["Response"]
        _save_json(
            _CHARACTER_CACHE, {"reset": last_reset().isoformat(), "data": response}
        )
        return response


# Instance partagée
bungie = BungieClient()