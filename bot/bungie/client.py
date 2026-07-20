# -*- coding: utf-8 -*-
import json
from datetime import datetime

import aiohttp

from bot.bungie.errors import BungieMaintenanceError, is_maintenance
from bot.bungie.reset import last_reset
from bot.config import BUNGIE_API_KEY, BUNGIE_CHARACTER, MANIFEST_DIR
from bot.utils.logger import log

BUNGIE_BASE = "https://www.bungie.net"
PLATFORM_BASE = f"{BUNGIE_BASE}/Platform"

# Composant Vendors demandé (sales = items en vente). Défini ici (et non importé
# depuis features/xur) pour éviter un cycle d'import : client.py est importé très
# tôt, avant les packages features.
_VENDOR_COMPONENTS = "402"

# Xûr : sales (402) + sockets (305). Le 305 (ItemSockets) porte les plugHash par
# position, indispensables pour afficher les perks (colonnes 3/4) des armes
# légendaires. Indexé par la MÊME clé que sales.data.
_VENDOR_COMPONENTS_SOCKETS = "402,305"

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
    sur le reset quotidien).

    Hold mode : les appels /Platform (et le téléchargement des définitions)
    lèvent BungieMaintenanceError sur 503/SystemDisabled au lieu de renvoyer
    None, pour que la pipeline distingue « maintenance » de « vraie erreur »
    et retente au prochain reset-poll."""

    def __init__(self, api_key: str = BUNGIE_API_KEY):
        self.api_key = api_key
        self._headers = {"X-API-Key": api_key}
        # Cache mémoire des définitions d'items résolues à la volée (Xûr).
        self._item_def_cache: dict[str, dict] = {}
        # Cache mémoire des définitions de vendors résolues à la volée (Xûr).
        self._vendor_def_cache: dict[str, dict] = {}

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

        `auth=True` ajoute le Bearer OAuth (requis pour GetVendor → Xûr).

        Lève BungieMaintenanceError si la réponse traduit une maintenance
        (HTTP 503, ou enveloppe ErrorStatus='SystemDisabled' / ErrorCode=5).
        Le corps JSON porte le vrai ErrorStatus Bungie (ApiInvalidOrExpiredKey,
        InsufficientPrivileges…), bien plus parlant que le seul code HTTP."""
        if auth:
            headers = await self._auth_headers()
            if headers is None:
                return None
        else:
            headers = self._headers

        url = f"{PLATFORM_BASE}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                status_code = resp.status
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None

        err_status = data.get("ErrorStatus") if isinstance(data, dict) else None
        err_code = data.get("ErrorCode") if isinstance(data, dict) else None
        message = data.get("Message") if isinstance(data, dict) else None

        # Maintenance (503 / SystemDisabled / code 5) → hold mode.
        if is_maintenance(status_code, err_status, err_code):
            raise BungieMaintenanceError(
                f"{endpoint} → HTTP {status_code} | {err_status} ({message})"
            )

        if status_code != 200:
            if isinstance(data, dict):
                log.error(
                    f"[Bungie] GET {endpoint} → HTTP {status_code} | "
                    f"{err_status} ({message})"
                )
            else:
                log.error(
                    f"[Bungie] GET {endpoint} → HTTP {status_code} (corps illisible)"
                )
            return None

        if not isinstance(data, dict):
            log.error(f"[Bungie] GET {endpoint} → HTTP 200 mais corps illisible.")
            return None

        if err_status and err_status != "Success":
            log.error(f"[Bungie] {endpoint} → {err_status} ({message})")
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
        """Renvoie (version, jsonWorldComponentContentPaths[lang]) ou None.

        Propage BungieMaintenanceError si /Destiny2/Manifest/ est en maintenance
        (c'est en général le tout premier appel d'un reset → détection au plus
        tôt)."""
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
        """Télécharge un fichier de définition (hébergé sur bungie.net).

        Lève BungieMaintenanceError sur 503 : au reset du mardi, la mise à jour
        du manifest peut tomber pendant la fenêtre de maintenance."""
        url = f"{BUNGIE_BASE}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if is_maintenance(resp.status):
                    raise BungieMaintenanceError(
                        f"download_definition → HTTP {resp.status} ({path})"
                    )
                if resp.status != 200:
                    log.error(f"[Bungie] DL définition → HTTP {resp.status} ({path})")
                    return None
                return await resp.json(content_type=None)

    # ── Activités du personnage de référence ─────────────────────────
    async def get_character_activities(self, *, force: bool = False) -> dict | None:
        """Bloc `Response` du profil (components=204) : availableActivities
        + availableActivityInteractables.

        Cache aligné sur le reset : les données restent valides jusqu'au
        prochain reset quotidien. `force=True` ignore le cache.

        Note hold mode : à un reset, le cache est périmé (cached_reset < le
        nouveau last_reset) → on refait l'appel → _get peut lever
        BungieMaintenanceError. Le cache ne masque donc jamais la maintenance
        au moment du reset."""
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
    async def get_vendor_sales(
        self, vendor_hash: int, character_id: str | None = None
    ) -> dict | None:
        """Bloc `Response.sales.data` d'un vendor (components=402).

        `character_id` (optionnel) permet d'interroger le vendor avec un
        personnage AUTRE que le principal — nécessaire pour les vendors dont
        l'inventaire dépend de la classe (ornements d'armure Eververse :
        Titan/Arcaniste/Chasseur). Défaut = personnage principal
        (BUNGIE_CHARACTER_ID).

        Renvoie le dict { "<saleItemIndex>": { "itemHash": ..., ... } } ou
        None en cas d'échec. Pas de cache : appelé seulement au reset du
        vendredi (Xûr ne change pas de la semaine)."""
        c = BUNGIE_CHARACTER
        char = character_id or c["character_id"]
        endpoint = (
            f"/Destiny2/{c['membership_type']}/Profile/{c['membership_id']}"
            f"/Character/{char}/Vendors/{vendor_hash}/"
        )
        data = await self._get(
            endpoint, params={"components": _VENDOR_COMPONENTS}, auth=True
        )
        if not data or "Response" not in data:
            log.error(f"[Bungie] Vendor {vendor_hash} indisponible.")
            return None
        return data["Response"].get("sales", {}).get("data", {})

    async def get_vendor_sales_sockets(
        self, vendor_hash: int, character_id: str | None = None
    ) -> tuple[dict, dict] | None:
        """(sales.data, itemComponents.sockets.data) d'un vendor (components=402,305).

        Variante de get_vendor_sales dédiée à Xûr : demande EN PLUS le composant
        305 (ItemSockets) pour obtenir les plugHash par position — nécessaires à
        l'affichage des perks (colonnes 3/4) des armes légendaires. Le bloc
        sockets est indexé par la MÊME clé que sales.data.

        Renvoie le tuple (sales, sockets) — `sockets` peut être {} si le vendor
        n'expose pas de sockets — ou None en cas d'échec. Auth OAuth requise
        (même contrainte que get_vendor_sales). Pas de cache : appelé au reset du
        vendredi. Le hold mode est préservé (BungieMaintenanceError remonte via
        _get)."""
        c = BUNGIE_CHARACTER
        char = character_id or c["character_id"]
        endpoint = (
            f"/Destiny2/{c['membership_type']}/Profile/{c['membership_id']}"
            f"/Character/{char}/Vendors/{vendor_hash}/"
        )
        data = await self._get(
            endpoint, params={"components": _VENDOR_COMPONENTS_SOCKETS}, auth=True
        )
        if not data or "Response" not in data:
            log.error(f"[Bungie] Vendor {vendor_hash} (sockets) indisponible.")
            return None
        resp = data["Response"]
        sales = resp.get("sales", {}).get("data", {})
        sockets = resp.get("itemComponents", {}).get("sockets", {}).get("data", {})
        return sales, sockets

    async def get_all_vendor_sales(self) -> dict | None:
        """Bloc `Response.sales.data` de TOUS les vendors visibles d'un coup
        (GetVendors PLURIEL, components=402).

        Structure imbriquée (vs get_vendor_sales, singulier) :
            { "<vendorHash>": { "saleItems": { "<index>": { "itemHash": ..., } } } }

        Auth OAuth requise (même contrainte que Xûr). Utilisé par la feature
        Eververse : les items en rotation sont éclatés sur plusieurs sous-vendors
        rotator, tous récupérés en un seul appel. Pas de cache : appelé au reset
        quotidien (rotation Eververse quotidienne)."""
        c = BUNGIE_CHARACTER
        endpoint = (
            f"/Destiny2/{c['membership_type']}/Profile/{c['membership_id']}"
            f"/Character/{c['character_id']}/Vendors/"
        )
        data = await self._get(
            endpoint, params={"components": _VENDOR_COMPONENTS}, auth=True
        )
        if not data or "Response" not in data:
            log.error("[Bungie] GetVendors (pluriel) indisponible.")
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

    async def get_vendor_definition(self, vendor_hash: int) -> dict | None:
        """Résout un vendor à la volée via l'API Manifest.

        DestinyVendorDefinition n'est pas dans le cache disque (les 3 vendor
        hashes Xûr sont connus à l'avance, inutile de cacher tout le manifest).
        On résout donc chaque hash par un appel dédié, avec petit cache mémoire
        (appelé seulement au reset du vendredi → 3 appels max).

        Utilisé pour récupérer displayProperties.largeIcon (image d'en-tête de
        chaque catégorie Xûr)."""
        key = str(vendor_hash)
        if key in self._vendor_def_cache:
            return self._vendor_def_cache[key]

        data = await self._get(
            f"/Destiny2/Manifest/DestinyVendorDefinition/{vendor_hash}/"
        )
        if not data or "Response" not in data:
            log.warning(f"[Bungie] Définition vendor {vendor_hash} introuvable.")
            return None

        defn = data["Response"]
        self._vendor_def_cache[key] = defn
        return defn


# Instance partagée
bungie = BungieClient()