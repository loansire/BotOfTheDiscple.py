# -*- coding: utf-8 -*-
"""Cache local du manifest Bungie + résolution de hashes hors-ligne.

Philosophie : on télécharge une fois le sous-ensemble de définitions utile
(jamais tout le manifest — DestinyInventoryItemDefinition est énorme), on le
garde sur disque, et on résout les hashes localement (aucune requête par
hash). Le re-téléchargement n'a lieu que si la *version* du manifest a changé,
ce qui ne se produit qu'au reset quotidien lors d'une mise à jour Bungie.
"""
import json

from bot.bungie.client import bungie
from bot.config import MANIFEST_DIR
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

_VERSION_FILE = MANIFEST_DIR / "_version.json"


def _load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ManifestStore:
    """Gère le cache disque des définitions et leur résolution mémoire."""

    def __init__(self, lang: str = "fr", client=bungie):
        self.lang = lang
        self.client = client
        self._cache: dict[str, dict] = {}

    # ── Synchronisation ───────────────────────────────────────────────
    async def sync(self) -> str | None:
        """Met le cache local à jour si la version distante a changé.

        Renvoie la version courante du manifest, ou None en cas d'échec.
        Ne télécharge QUE si la version diffère du cache local."""
        index = await self.client.get_manifest_index(self.lang)
        if index is None:
            return None
        version, paths = index

        local = _load_json(_VERSION_FILE)
        if local and local.get("version") == version and local.get("lang") == self.lang:
            log.debug(f"[Manifest] Déjà à jour (version {version}).")
            return version

        log.info(f"[Manifest] Nouvelle version détectée : {version} — téléchargement.")
        for name in MANIFEST_DEFINITIONS:
            path = paths.get(name)
            if not path:
                log.warning(f"[Manifest] {name} absent de l'index (lang={self.lang}).")
                continue
            defn = await self.client.download_definition(path)
            if defn is not None:
                _save_json(MANIFEST_DIR / f"{name}.json", defn)
                log.info(f"[Manifest] {name} enregistré ({len(defn)} entrées).")
            else:
                log.error(f"[Manifest] Échec du téléchargement de {name}.")

        _save_json(_VERSION_FILE, {"version": version, "lang": self.lang})
        self._cache.clear()  # le cache mémoire est invalidé après update
        return version

    # ── Résolution ────────────────────────────────────────────────────
    def _load_definition(self, name: str) -> dict:
        """Charge une définition locale (cache mémoire)."""
        if name in self._cache:
            return self._cache[name]
        data = _load_json(MANIFEST_DIR / f"{name}.json") or {}
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


# Instance partagée
manifest = ManifestStore()