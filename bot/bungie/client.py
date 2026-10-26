# -*- coding: utf-8 -*-
import asyncio
import json
from datetime import datetime

import aiohttp

from bot.bungie.errors import (
    BungieMaintenanceError,
    BungieNotReadyError,
    is_maintenance,
    is_transient,
)
from bot.bungie.reset import last_reset
from bot.config import BUNGIE_API_KEY, BUNGIE_CHARACTER, MANIFEST_DIR
from bot.utils.http import NETWORK_ERRORS, get_session
from bot.utils.jsonio import load_json, save_json
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

# Les fichiers de définitions (jusqu'à plusieurs dizaines de Mo) dépassent
# largement le timeout par défaut de la session partagée.
_DEFINITION_TIMEOUT = aiohttp.ClientTimeout(total=300)


class BungieClient:
    """Couche d'accès à l'API Bungie.

    Au-delà du flux RSS news, expose de quoi alimenter les features
    weekly/daily : index du manifest, téléchargement des définitions, et
    activités disponibles du personnage de référence (avec cache aligné
    sur le reset quotidien).

    Hold mode : les appels /Platform (et le téléchargement des définitions)
    lèvent BungieMaintenanceError sur 503/SystemDisabled, et BungieNotReadyError
    sur une panne transitoire NON déclarée (5xx, 429, throttling, corps
    illisible, erreur réseau) au lieu de renvoyer None. La pipeline distingue
    ainsi « indisponible, à retenter » de « vraie erreur définitive »."""

    def __init__(self, api_key: str = BUNGIE_API_KEY):
        self.api_key = api_key
        self._headers = {"X-API-Key": api_key}
        # Cache mémoire des définitions résolues à la volée, par type d'entité
        # (DestinyInventoryItemDefinition, DestinyVendorDefinition).
        self._entity_cache: dict[str, dict[str, dict]] = {}
        # Miroir mémoire du cache disque des activités personnage.
        self._character_cache: dict | None = None

    # ── Bas niveau ────────────────────────────────────────────────────
    async def _auth_headers(self) -> dict | None:
        """Headers avec Bearer OAuth, ou None si l'auth échoue.

        Import différé d'oauth pour éviter tout cycle (oauth → config).
        Une indisponibilité de l'endpoint token (maintenance, 5xx) remonte
        telle quelle (BungieUnavailableError) pour déclencher le hold mode."""
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
        (HTTP 503, ou enveloppe ErrorStatus='SystemDisabled' / ErrorCode=5), et
        BungieNotReadyError sur une panne transitoire. Renvoie None uniquement
        pour une erreur DÉFINITIVE (clé invalide, entité introuvable…). Le corps
        JSON porte le vrai ErrorStatus Bungie, bien plus parlant que le code HTTP."""
        if auth:
            headers = await self._auth_headers()
            if headers is None:
                return None
        else:
            headers = self._headers

        url = f"{PLATFORM_BASE}{endpoint}"
        try:
            async with get_session().get(url, headers=headers, params=params) as resp:
                status_code = resp.status
                try:
                    data = await resp.json(content_type=None)
                except (ValueError, aiohttp.ContentTypeError):
                    data = None
        except NETWORK_ERRORS as e:
            raise BungieNotReadyError(
                f"{endpoint} → erreur réseau ({type(e).__name__}: {e})"
            ) from e

        readable = isinstance(data, dict)
        err_status = data.get("ErrorStatus") if readable else None
        err_code = data.get("ErrorCode") if readable else None
        message = data.get("Message") if readable else None

        # Maintenance (503 / SystemDisabled / code 5) → hold mode.
        if is_maintenance(status_code, err_status, err_code):
            raise BungieMaintenanceError(
                f"{endpoint} → HTTP {status_code} | {err_status} ({message})"
            )

        ok = status_code == 200 and readable and err_status in (None, "Success")
        if ok:
            return data

        detail = (
            f"HTTP {status_code} | {err_status} ({message})"
            if readable else f"HTTP {status_code} (corps illisible)"
        )
        if is_transient(status_code, err_status, readable):
            raise BungieNotReadyError(f"{endpoint} → {detail}")

        log.error(f"[Bungie] GET {endpoint} → {detail}")
        return None

    @staticmethod
    def _character_path(character_id: str | None = None) -> str:
        """/Destiny2/{type}/Profile/{id}/Character/{char}/ (perso principal par défaut)."""
        c = BUNGIE_CHARACTER
        char = character_id or c["character_id"]
        return (
            f"/Destiny2/{c['membership_type']}/Profile/{c['membership_id']}"
            f"/Character/{char}/"
        )

    # ── RSS News ──────────────────────────────────────────────────────
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
        try:
            async with get_session().get(url, headers=self._headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
                log.error(f"[Bungie] RSS NewsArticles → HTTP {resp.status}")
                return None
        except (*NETWORK_ERRORS, ValueError) as e:
            log.warning(f"[Bungie] RSS NewsArticles ({language}) indisponible : {e}")
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

        Lève BungieMaintenanceError sur 503 (au reset du mardi, la mise à jour
        du manifest peut tomber pendant la fenêtre de maintenance) et
        BungieNotReadyError sur une erreur réseau / 5xx.

        Le décodage JSON (fichiers de plusieurs dizaines de Mo) est fait dans
        un thread : sinon il bloquerait l'event loop, et donc le heartbeat
        Discord, pendant plusieurs secondes."""
        url = f"{BUNGIE_BASE}{path}"
        try:
            async with get_session().get(url, timeout=_DEFINITION_TIMEOUT) as resp:
                if is_maintenance(resp.status):
                    raise BungieMaintenanceError(
                        f"download_definition → HTTP {resp.status} ({path})"
                    )
                if resp.status != 200:
                    if is_transient(resp.status):
                        raise BungieNotReadyError(
                            f"download_definition → HTTP {resp.status} ({path})"
                        )
                    log.error(f"[Bungie] DL définition → HTTP {resp.status} ({path})")
                    return None
                raw = await resp.read()
        except NETWORK_ERRORS as e:
            raise BungieNotReadyError(
                f"download_definition → erreur réseau ({type(e).__name__}) ({path})"
            ) from e

        try:
            return await asyncio.to_thread(json.loads, raw)
        except ValueError as e:
            raise BungieNotReadyError(
                f"download_definition → JSON illisible ({path}) : {e}"
            ) from e

    # ── Activités du personnage de référence ─────────────────────────
    async def get_character_activities(self, *, force: bool = False) -> dict | None:
        """Bloc `Response` du profil (components=204) : availableActivities
        + availableActivityInteractables.

        Cache aligné sur le reset : les données restent valides jusqu'au
        prochain reset quotidien. `force=True` ignore le cache. Miroir mémoire
        pour éviter de relire le fichier disque à chaque appel.

        Note hold mode : à un reset, le cache est périmé (cached_reset < le
        nouveau last_reset) → on refait l'appel → _get peut lever
        BungieMaintenanceError / BungieNotReadyError. Le cache ne masque donc
        jamais la maintenance au moment du reset. Si l'appelant juge les
        données reçues pas encore prêtes, il appelle
        invalidate_character_cache() pour qu'elles ne soient pas figées."""
        if not force:
            cached = self._character_cache or load_json(_CHARACTER_CACHE)
            if cached:
                try:
                    cached_reset = datetime.fromisoformat(cached["reset"])
                except (KeyError, ValueError, TypeError):
                    cached_reset = None
                if cached_reset and cached_reset >= last_reset():
                    self._character_cache = cached
                    log.debug("[Bungie] Activités personnage servies depuis le cache.")
                    return cached.get("data")

        data = await self._get(self._character_path(), params={"components": "204"})
        if not data or "Response" not in data:
            log.error("[Bungie] Récupération des activités personnage impossible.")
            return None

        response = data["Response"]
        self._character_cache = {"reset": last_reset().isoformat(), "data": response}
        save_json(_CHARACTER_CACHE, self._character_cache, indent=None)
        return response

    def invalidate_character_cache(self) -> None:
        """Oublie les activités en cache (données jugées pas prêtes / périmées)."""
        self._character_cache = None
        try:
            _CHARACTER_CACHE.unlink(missing_ok=True)
        except OSError as e:
            log.warning(f"[Bungie] Suppression du cache activités impossible : {e}")

    # ── Vendors ───────────────────────────────────────────────────────
    async def _get_vendor_response(
        self, vendor_hash: int | None, components: str, character_id: str | None
    ) -> dict | None:
        """`Response` de GetVendor (vendor_hash) ou GetVendors (None), auth OAuth."""
        endpoint = f"{self._character_path(character_id)}Vendors/"
        if vendor_hash is not None:
            endpoint += f"{vendor_hash}/"
        data = await self._get(endpoint, params={"components": components}, auth=True)
        if not data or "Response" not in data:
            label = vendor_hash if vendor_hash is not None else "(tous)"
            log.error(f"[Bungie] Vendor {label} indisponible.")
            return None
        return data["Response"]

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
        None en cas d'échec définitif."""
        resp = await self._get_vendor_response(vendor_hash, _VENDOR_COMPONENTS, character_id)
        if resp is None:
            return None
        return resp.get("sales", {}).get("data", {})

    async def get_vendor_sales_sockets(
        self, vendor_hash: int, character_id: str | None = None
    ) -> tuple[dict, dict] | None:
        """(sales.data, itemComponents.sockets.data) d'un vendor (components=402,305).

        Variante de get_vendor_sales dédiée à Xûr : demande EN PLUS le composant
        305 (ItemSockets) pour obtenir les plugHash par position — nécessaires à
        l'affichage des perks (colonnes 3/4) des armes légendaires. Le bloc
        sockets est indexé par la MÊME clé que sales.data.

        Renvoie le tuple (sales, sockets) — `sockets` peut être {} si le vendor
        n'expose pas de sockets — ou None en cas d'échec définitif."""
        resp = await self._get_vendor_response(
            vendor_hash, _VENDOR_COMPONENTS_SOCKETS, character_id
        )
        if resp is None:
            return None
        sales = resp.get("sales", {}).get("data", {})
        sockets = resp.get("itemComponents", {}).get("sockets", {}).get("data", {})
        return sales, sockets

    async def get_all_vendor_sales(self) -> dict | None:
        """Bloc `Response.sales.data` de TOUS les vendors visibles d'un coup
        (GetVendors PLURIEL, components=402).

        Structure imbriquée (vs get_vendor_sales, singulier) :
            { "<vendorHash>": { "saleItems": { "<index>": { "itemHash": ..., } } } }

        Utilisé par la feature Eververse : les items en rotation sont éclatés
        sur plusieurs sous-vendors rotator, tous récupérés en un seul appel."""
        resp = await self._get_vendor_response(None, _VENDOR_COMPONENTS, None)
        if resp is None:
            return None
        return resp.get("sales", {}).get("data", {})

    # ── Définitions résolues à la volée ──────────────────────────────
    async def _get_entity(self, entity_type: str, entity_hash: int) -> dict | None:
        """Résout une définition via l'API Manifest, avec cache mémoire.

        Sert aux définitions volontairement absentes du cache disque
        (DestinyInventoryItemDefinition, trop volumineuse ; DestinyVendorDefinition,
        seuls quelques hashes utiles)."""
        cache = self._entity_cache.setdefault(entity_type, {})
        key = str(entity_hash)
        if key in cache:
            return cache[key]

        data = await self._get(f"/Destiny2/Manifest/{entity_type}/{entity_hash}/")
        if not data or "Response" not in data:
            log.warning(f"[Bungie] {entity_type} {entity_hash} introuvable.")
            return None

        defn = data["Response"]
        cache[key] = defn
        return defn

    async def get_item_definition(self, item_hash: int) -> dict | None:
        return await self._get_entity("DestinyInventoryItemDefinition", item_hash)

    async def get_vendor_definition(self, vendor_hash: int) -> dict | None:
        """Utilisé pour displayProperties.largeIcon (en-tête des catégories Xûr)."""
        return await self._get_entity("DestinyVendorDefinition", vendor_hash)


# Instance partagée
bungie = BungieClient()
