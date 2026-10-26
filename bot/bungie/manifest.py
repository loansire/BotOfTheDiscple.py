# -*- coding: utf-8 -*-
"""Cache local du manifest Bungie + résolution de hashes hors-ligne.

Philosophie : on télécharge une fois le sous-ensemble de définitions utile
(jamais tout le manifest — DestinyInventoryItemDefinition est énorme), on le
garde sur disque, et on résout les hashes localement (aucune requête par
hash). Le re-téléchargement n'a lieu que si la *version* du manifest a changé,
ce qui ne se produit qu'au reset quotidien lors d'une mise à jour Bungie.

Surcouche de noms FR (Xûr) : on télécharge en plus, au changement de version,
DestinyInventoryItemLiteDefinition (FR) — version allégée de l'item def, sans
les gros blocs (sockets/stats) — pour en EXTRAIRE un fichier léger
`item_names_fr.json` = { "<hash>": "<nom FR>" } (noms non vides uniquement). La
définition Lite brute n'est jamais conservée sur disque : seul l'extrait l'est.
Cet extrait sert de surcouche de traduction au-dessus des items Xûr résolus en
anglais via l'API live (cf. features/xur/service.py).

Extrait Portail (Avant-garde) : au changement de version, on télécharge aussi
les constantes globales et le graphe Fireteam Finder pour en EXTRAIRE
`portal_activities.json` = { "categories": { "<nœud racine>": [activityHash…] },
"alerts": [activityHash…] }. Comme pour les noms FR, les définitions brutes ne
sont pas conservées."""
import asyncio

from bot.bungie.client import bungie
from bot.config import MANIFEST_DIR
from bot.utils.jsonio import load_json, save_json
from bot.utils.logger import log

# Sous-ensemble de définitions téléchargées localement.
# Volontairement SANS DestinyInventoryItemDefinition (trop volumineux) :
# on ne l'ajoutera que si l'affichage des récompenses l'exige.
MANIFEST_DEFINITIONS = [
    "DestinyActivityDefinition",
    "DestinyActivityTypeDefinition",
    "DestinyActivityModifierDefinition",
    "DestinyActivityInteractableDefinition",
    "DestinyDestinationDefinition",
    "DestinyPlaceDefinition",
]

# clé d'objet JSON → définition à utiliser pour la résoudre.
KEY_MAP = {
    "activityHash": "DestinyActivityDefinition",
    "activityTypeHash": "DestinyActivityTypeDefinition",
    "modifierHashes": "DestinyActivityModifierDefinition",
    "activityModifierHash": "DestinyActivityModifierDefinition",
    "activityInteractableHash": "DestinyActivityInteractableDefinition",
    "destinationHash": "DestinyDestinationDefinition",
    "placeHash": "DestinyPlaceDefinition",
}

# Définition (allégée) téléchargée UNIQUEMENT pour en extraire les noms FR.
# Jamais conservée telle quelle : on n'en garde que l'extrait {hash: name}.
_ITEM_NAMES_SOURCE_DEFINITION = "DestinyInventoryItemLiteDefinition"

_VERSION_FILE = MANIFEST_DIR / "_version.json"

# Extrait léger des noms d'items FR : { "<hash>": "<nom FR>" }.
_ITEM_NAMES_FR_FILE = MANIFEST_DIR / "item_names_fr.json"

# Définitions téléchargées UNIQUEMENT pour en extraire le classement Portail.
_GLOBAL_CONSTANTS_DEFINITION = "DestinyGlobalConstantsDefinition"
_FT_GRAPH_DEFINITION = "DestinyFireteamFinderActivityGraphDefinition"
_FT_SET_DEFINITION = "DestinyFireteamFinderActivitySetDefinition"

# Extrait Portail : { "categories": {"<root>": [hash…]}, "alerts": [hash…] }.
PORTAL_ACTIVITIES_FILE = MANIFEST_DIR / "portal_activities.json"


async def _save_json_async(path, data) -> None:
    """Écriture (atomique, compacte) dans un thread : les définitions pèsent
    plusieurs dizaines de Mo, les sérialiser dans l'event loop le bloquerait."""
    await asyncio.to_thread(save_json, path, data, indent=None)


def _extract_item_names(defn: dict) -> dict[str, str]:
    """Réduit une DestinyInventoryItemLiteDefinition brute à { hash: name }.

    Ne garde que les entrées dont displayProperties.name est non vide. Les
    clés sont conservées en str (cohérent avec le reste du cache manifest)."""
    names: dict[str, str] = {}
    for item_hash, item in defn.items():
        if not isinstance(item, dict):
            continue
        name = (item.get("displayProperties") or {}).get("name") or ""
        name = name.strip()
        if name:
            names[str(item_hash)] = name
    return names


def _graph_activities(graph: dict, sets: dict, root_hash: int) -> list[int]:
    """Activités rattachées à un nœud du graphe Fireteam Finder (lui compris
    et tous ses descendants), via leurs activity sets."""
    root = graph.get(str(root_hash)) or {}
    out: list[int] = []
    for node_hash in root.get("selfAndAllDescendantHashes") or [root_hash]:
        node = graph.get(str(node_hash)) or {}
        for set_hash in node.get("relatedActivitySetHashes", []):
            for ah in (sets.get(str(set_hash)) or {}).get("activityHashes", []):
                if ah not in out:
                    out.append(ah)
    return out


def _extract_portal(constants: dict, graph: dict, sets: dict) -> dict:
    """Réduit constantes globales + graphe Fireteam Finder à l'extrait Portail.

    Les nœuds racines des catégories du Portail sont lus dans
    `portalActivityGraphRootNodesWithIcons`, celui des alertes de l'Avant-garde
    dans `vanguardAlertsFireteamFinderActivityGraphRootNodeHash`."""
    entry = next(iter(constants.values()), {}) if constants else {}
    roots = entry.get("portalActivityGraphRootNodesWithIcons") or {}
    alert_root = entry.get("vanguardAlertsFireteamFinderActivityGraphRootNodeHash")
    return {
        "categories": {
            str(root): _graph_activities(graph, sets, int(root)) for root in roots
        },
        "alerts": _graph_activities(graph, sets, alert_root) if alert_root else [],
    }


class ManifestStore:
    """Gère le cache disque des définitions et leur résolution mémoire."""

    def __init__(self, lang: str = "fr", client=bungie):
        self.lang = lang
        self.client = client
        self._cache: dict[str, dict] = {}
        # Cache mémoire dédié de l'extrait de noms FR (chargé paresseusement).
        self._item_names_fr: dict[str, str] | None = None
        # Cache mémoire de l'extrait Portail (chargé paresseusement).
        self._portal: dict | None = None

    # ── Synchronisation ───────────────────────────────────────────────
    async def sync(self) -> str | None:
        """Met le cache local à jour si la version distante a changé.

        Renvoie la version courante du manifest, ou None en cas d'échec.
        Ne télécharge QUE si la version diffère du cache local.

        La version locale n'est enregistrée que si TOUTES les définitions ont
        été téléchargées : sinon une définition manquante ne serait plus jamais
        retéléchargée avant la version suivante, et resolve() renverrait {} en
        silence (activités ignorées). En cas d'échec partiel, on retente au
        prochain sync."""
        index = await self.client.get_manifest_index(self.lang)
        if index is None:
            return None
        version, paths = index

        local = load_json(_VERSION_FILE)
        if local and local.get("version") == version and local.get("lang") == self.lang:
            # Extrait Portail ajouté après coup : généré sans attendre une
            # nouvelle version du manifest s'il manque.
            if not PORTAL_ACTIVITIES_FILE.exists():
                await self._sync_portal(paths)
            log.debug(f"[Manifest] Déjà à jour (version {version}).")
            return version

        log.info(f"[Manifest] Nouvelle version détectée : {version} — téléchargement.")
        complete = True
        for name in MANIFEST_DEFINITIONS:
            path = paths.get(name)
            if not path:
                log.warning(f"[Manifest] {name} absent de l'index (lang={self.lang}).")
                continue
            defn = await self.client.download_definition(path)
            if defn is not None:
                await _save_json_async(MANIFEST_DIR / f"{name}.json", defn)
                log.info(f"[Manifest] {name} enregistré ({len(defn)} entrées).")
            else:
                complete = False
                log.error(f"[Manifest] Échec du téléchargement de {name}.")

        # Surcouche FR : extraction des noms d'items (Lite → {hash: name}).
        await self._sync_item_names_fr(paths)
        # Extrait Portail (catégories + alertes de l'Avant-garde).
        await self._sync_portal(paths)

        self._cache.clear()         # cache mémoire des définitions invalidé
        self._item_names_fr = None  # extrait de noms rechargé au prochain accès
        self._portal = None         # extrait Portail rechargé au prochain accès
        if not complete:
            log.error("[Manifest] Synchro incomplète — version NON enregistrée, retentée au prochain sync.")
            return None
        save_json(_VERSION_FILE, {"version": version, "lang": self.lang})
        return version

    def mark_stale(self) -> None:
        """Force un re-téléchargement complet au prochain sync().

        Appelé quand des hashes du profil sont introuvables dans les
        définitions locales : signe d'un cache local en retard sur Bungie."""
        try:
            _VERSION_FILE.unlink(missing_ok=True)
        except OSError as e:
            log.warning(f"[Manifest] Invalidation de la version locale impossible : {e}")

    async def preload(self, name: str) -> None:
        """Charge une définition en mémoire dans un thread (gros JSON) pour que
        le premier resolve() ne bloque pas l'event loop."""
        if name not in self._cache:
            data = await asyncio.to_thread(load_json, MANIFEST_DIR / f"{name}.json", {})
            self._cache[name] = data or {}

    async def _sync_item_names_fr(self, paths: dict) -> None:
        """Télécharge la def Lite, en extrait {hash: name}, écrit l'extrait.

        La définition brute (volumineuse) n'est PAS conservée : on ne sauve que
        l'extrait léger. En cas d'absence du chemin ou d'échec de
        téléchargement, on loggue et on laisse l'extrait précédent en place
        (pas d'écrasement par du vide). Une BungieMaintenanceError éventuelle
        (levée par download_definition sur 503) remonte volontairement à
        l'appelant (sync → pipeline) pour activer le hold mode."""
        path = paths.get(_ITEM_NAMES_SOURCE_DEFINITION)
        if not path:
            log.warning(
                f"[Manifest] {_ITEM_NAMES_SOURCE_DEFINITION} absent de l'index "
                f"(lang={self.lang}) — noms FR non régénérés."
            )
            return

        defn = await self.client.download_definition(path)
        if defn is None:
            log.error(
                f"[Manifest] Échec du téléchargement de "
                f"{_ITEM_NAMES_SOURCE_DEFINITION} — noms FR non régénérés."
            )
            return

        names = await asyncio.to_thread(_extract_item_names, defn)
        # `defn` (volumineux) n'est référencé nulle part ailleurs → libérable.
        await _save_json_async(_ITEM_NAMES_FR_FILE, names)
        log.info(f"[Manifest] Noms d'items FR extraits ({len(names)} entrées).")

    async def _sync_portal(self, paths: dict) -> None:
        """Télécharge constantes globales + graphe Fireteam Finder, en extrait
        le classement Portail et l'écrit. Même politique d'échec que
        _sync_item_names_fr : on loggue et on garde l'extrait précédent."""
        defs = {}
        for name in (_GLOBAL_CONSTANTS_DEFINITION, _FT_GRAPH_DEFINITION, _FT_SET_DEFINITION):
            path = paths.get(name)
            defn = await self.client.download_definition(path) if path else None
            if not defn:
                log.error(f"[Manifest] {name} indisponible — extrait Portail non régénéré.")
                return
            defs[name] = defn

        portal = await asyncio.to_thread(
            _extract_portal,
            defs[_GLOBAL_CONSTANTS_DEFINITION],
            defs[_FT_GRAPH_DEFINITION],
            defs[_FT_SET_DEFINITION],
        )
        save_json(PORTAL_ACTIVITIES_FILE, portal, indent=None)
        self._portal = None
        log.info(
            f"[Manifest] Extrait Portail : {len(portal['categories'])} catégorie(s), "
            f"{len(portal['alerts'])} activité(s) d'alerte."
        )

    # ── Résolution ────────────────────────────────────────────────────
    def _load_definition(self, name: str) -> dict:
        """Charge une définition locale (cache mémoire)."""
        if name in self._cache:
            return self._cache[name]
        data = load_json(MANIFEST_DIR / f"{name}.json") or {}
        self._cache[name] = data
        return data

    def resolve(self, hash_value, definition_name: str) -> dict:
        """Définition correspondant à un hash, ou {} si introuvable."""
        return self._load_definition(definition_name).get(str(hash_value), {})

    def enrich_object(self, obj: dict) -> dict:
        """Ajoute une clé `<clé>_def` pour chaque hash résoluble via KEY_MAP."""
        enriched = dict(obj)
        for key, def_name in KEY_MAP.items():
            if key not in obj:
                continue
            value = obj[key]
            if isinstance(value, int):
                enriched[f"{key}_def"] = self.resolve(value, def_name)
            elif isinstance(value, list) and all(isinstance(v, int) for v in value):
                enriched[f"{key}_def"] = [self.resolve(v, def_name) for v in value]
        return enriched

    # ── Surcouche noms FR (Xûr) ───────────────────────────────────────
    def _load_item_names_fr(self) -> dict[str, str]:
        """Charge l'extrait de noms FR (cache mémoire, lazy)."""
        if self._item_names_fr is None:
            self._item_names_fr = load_json(_ITEM_NAMES_FR_FILE) or {}
        return self._item_names_fr

    def item_name_fr(self, item_hash) -> str | None:
        """Nom FR d'un item depuis l'extrait local, ou None si absent.

        Surcouche de traduction : l'appelant garde le nom EN (résolu via l'API
        live) en cas de None. Aucun appel réseau ici."""
        return self._load_item_names_fr().get(str(item_hash)) or None

    # ── Extrait Portail (Avant-garde) ─────────────────────────────────
    def portal(self) -> dict:
        """Extrait Portail (cache mémoire, lazy) : {"categories", "alerts"}.
        Vide tant que le premier sync ne l'a pas généré."""
        if self._portal is None:
            self._portal = load_json(PORTAL_ACTIVITIES_FILE) or {}
        return self._portal


# Instance partagée
manifest = ManifestStore()