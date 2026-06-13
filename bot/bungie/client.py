# -*- coding: utf-8 -*-
import json
from datetime import datetime

import aiohttp

from bot.bungie.reset import last_reset
from bot.config import BUNGIE_API_KEY, BUNGIE_CHARACTER, MANIFEST_DIR
from bot.utils.logger import log

BUNGIE_BASE = "https://www.bungie.net"
PLATFORM_BASE = f"{BUNGIE_BASE}/Platform"

# Composant Vendors demandé pour Xûr (sales = items en vente). Défini ici (et
# non importé depuis features/xur) pour éviter un cycle d'import : client.py est
# importé très tôt, avant le package features.xur.
_VENDOR_COMPONENTS = "402"

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
        # Cache mémoire des définitions d'items résolues à la volée (Xûr).
        self._item_def_cache: dict[str, dict] = {}

    # ── Bas niveau ────────────────────────────────────────────────────
    async def _auth_headers(self) -> dict | None:
        """Headers avec Bearer OAuth, ou None si l'auth échoue.

        Import différé d'oauth pour éviter tout cycle (oauth → config)."""
        from bot.bungie.oauth import OAuthError, get_access_token
        try:
            token = await get_access_token()
        except OAuthError as e:
            log.error(f"[Bungie] OAuth indisponible : {e}")
            return None
        headers = dict(self._headers)
        headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get(
        self, endpoint: str, params: dict | None = None, *, auth: bool = False
    ) -> dict | None:
        """GET générique sur /Platform. Renvoie le JSON complet ou None.

        `auth=True` ajoute le Bearer OAuth (requis pour GetVendor → Xûr)."""
        if auth:
            headers = await self._auth_headers()
            if headers is None:
                return None
        else:
            headers = self._headers

        url = f"{PLATFORM_BASE}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    # On lit le corps : c'est lui qui porte le vrai ErrorStatus
                    # Bungie (ApiInvalidOrExpiredKey, OriginHeaderDoesNotMatchKey,
                    # InsufficientPrivileges…), bien plus parlant que le code HTTP.
                    try:
                        body = await resp.json(content_type=None)
                        log.error(
                            f"[Bungie] GET {endpoint} → HTTP {resp.status} | "
                            f"{body.get('ErrorStatus')} ({body.get('Message')})"
                        )
                    except Exception:
                        log.error(
                            f"[Bungie] GET {endpoint} → HTTP {resp.status} (corps illisible)"
                        )
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

    # ── Vendors (Xûr) ─────────────────────────────────────────────────
    async def get_vendor_sales(self, vendor_hash: int) -> dict | None:
        """Bloc `Response.sales.data` d'un vendor (components=402).

        Renvoie le dict { "<saleItemIndex>": { "itemHash": ..., ... } } ou
        None en cas d'échec. Pas de cache : appelé seulement au reset du
        vendredi (Xûr ne change pas de la semaine)."""
        c = BUNGIE_CHARACTER
        endpoint = (
            f"/Destiny2/{c['membership_type']}/Profile/{c['membership_id']}"
            f"/Character/{c['character_id']}/Vendors/{vendor_hash}/"
        )
        data = await self._get(
            endpoint, params={"components": _VENDOR_COMPONENTS}, auth=True
        )
        if not data or "Response" not in data:
            log.error(f"[Bungie] Vendor {vendor_hash} indisponible.")
            return None
        return data["Response"].get("sales", {}).get("data", {})

    async def get_item_definition(self, item_hash: int) -> dict | None:
        """Résout un item à la volée via l'API Manifest.

        DestinyInventoryItemDefinition n'est volontairement PAS dans le cache
        disque (trop volumineux). On résout donc chaque hash par un appel
        dédié. Petit cache mémoire pour éviter de refetch un hash déjà vu."""
        key = str(item_hash)
        if key in self._item_def_cache:
            return self._item_def_cache[key]

        data = await self._get(
            f"/Destiny2/Manifest/DestinyInventoryItemDefinition/{item_hash}/"
        )
        if not data or "Response" not in data:
            log.warning(f"[Bungie] Définition item {item_hash} introuvable.")
            return None

        defn = data["Response"]
        self._item_def_cache[key] = defn
        return defn


# Instance partagée
bungie = BungieClient()