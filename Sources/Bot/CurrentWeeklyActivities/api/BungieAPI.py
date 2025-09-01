import requests
import os
import json

from utils.Config import DEFINITION  # <- liste de définitions


class BungieAPI:
    """
    Classe permettant d’interagir avec l’API Bungie pour Destiny 2 et
    de gérer un cache local des manifests et définitions.

    Fonctionnalités principales :
    - Téléchargement et mise en cache du manifest Destiny 2.
    - Téléchargement local des définitions demandées (Config.DEFINITION).
    - Recherche locale d’une entité par son hash (équivalent du
      endpoint Destiny2.GetDestinyEntityDefinition).

    Attributs
    ----------
    BASE_URL : str
        URL de base de l’API Bungie.
    MANIFEST_ENDPOINT : str
        Endpoint pour récupérer le manifest Destiny 2.
    MANIFEST_FILE : str
        Chemin du fichier manifest local en cache.
    api_key : str
        Clé API Bungie.
    lang : str
        Langue des définitions (par défaut "fr").
    session : requests.Session
        Session HTTP réutilisée avec header API Key.
    """

    BASE_URL = "https://www.bungie.net/Platform"
    MANIFEST_ENDPOINT = "/Destiny2/Manifest/"
    MANIFEST_FILE = "data/definitions/manifest.json"

    def __init__(self, api_key: str, lang: str = "fr"):
        """
        Initialise la classe BungieAPI.

        Parameters
        ----------
        api_key : str
            Clé API Bungie.
        lang : str, optional
            Langue pour les définitions (par défaut "fr").
        """
        self.api_key = api_key
        self.lang = lang
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key})

        os.makedirs("data/definitions", exist_ok=True)

    def _get(self, endpoint: str):
        """
        Effectue une requête GET vers un endpoint de l’API Bungie.

        Parameters
        ----------
        endpoint : str
            L’endpoint (ex: "/Destiny2/Manifest/").

        Returns
        -------
        dict | None
            Réponse JSON de l’API en dict si succès, None sinon.
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"[HTTP ERROR] {response.status_code} - {response.text}")
            return None

        data = response.json()
        # Log Bungie API
        print(f"[BUNGIE] Status={data.get('ErrorStatus')} "
              f"Message={data.get('Message')} "
              f"Code={data.get('ErrorCode')}")
        return data

    def _load_local_manifest(self):
        """
        Charge le manifest local en cache.

        Returns
        -------
        dict | None
            Contenu JSON du manifest si disponible, sinon None.
        """
        if os.path.exists(self.MANIFEST_FILE):
            with open(self.MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_local_manifest(self, version: str, lang_paths: dict):
        """
        Sauvegarde le manifest téléchargé en local.

        Parameters
        ----------
        version : str
            Version du manifest.
        lang_paths : dict
            Dictionnaire des chemins de définitions pour une langue donnée.
        """
        manifest_data = {
            "version": version,
            "lang": self.lang,
            "paths": {k: lang_paths[k] for k in DEFINITION if k in lang_paths}
        }
        with open(self.MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    def download_manifest_definitions(self):
        """
        Télécharge et met en cache le manifest Destiny 2,
        ainsi que les définitions listées dans `Config.DEFINITION`.

        Si le manifest local est déjà à jour, il est réutilisé.

        Returns
        -------
        str | None
            Version du manifest téléchargé ou None en cas d’échec.
        """
        data = self._get(self.MANIFEST_ENDPOINT)
        if not data or "Response" not in data:
            return None

        response = data["Response"]
        version = response.get("version")
        paths = response.get("jsonWorldComponentContentPaths", {})
        lang_paths = paths.get(self.lang)

        if not lang_paths:
            print(f"[ERREUR] Pas de chemins pour la langue '{self.lang}'")
            return None

        # Vérifie si manifest déjà en cache
        local_manifest = self._load_local_manifest()
        if local_manifest and local_manifest.get("version") == version:
            print(f"[CACHE] Manifest déjà à jour (version {version})")
            return version

        print(f"[UPDATE] Nouvelle version manifest détectée : {version}")
        # Sauvegarde du manifest local
        self._save_local_manifest(version, lang_paths)

        # Télécharge les définitions
        for def_name in DEFINITION:
            if def_name not in lang_paths:
                print(f"[WARN] {def_name} non trouvé dans le manifest")
                continue

            def_url = f"https://www.bungie.net{lang_paths[def_name]}"
            def_response = self.session.get(def_url)

            if def_response.status_code == 200:
                def_data = def_response.json()
                output_path = os.path.join("data/definitions", f"{def_name}.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(def_data, f, ensure_ascii=False)
                print(f"[OK] {def_name} sauvegardé ({len(def_data)} entrées)")
            else:
                print(f"[HTTP ERROR] {def_response.status_code} pour {def_name}")

        return version

    def get_definition_entity(self, definition: str, entity_hash: int):
        """
        Recherche locale d’un hash dans une définition donnée.
        Simule le comportement de `Destiny2.GetDestinyEntityDefinition`.

        Parameters
        ----------
        definition : str
            Nom de la définition (ex: "DestinyInventoryItemDefinition").
        entity_hash : int
            Hash numérique de l’item ou entité.

        Returns
        -------
        dict | None
            Données de l’entité trouvée, ou None si absente.
        """
        file_path = os.path.join("data/definitions", f"{definition}.json")

        if not os.path.exists(file_path):
            print(f"[ERREUR] La définition {definition} n’est pas disponible localement.")
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entity_hash = str(entity_hash)  # Bungie stocke les clés en string
        entity = data.get(entity_hash)

        if entity is None:
            print(f"[INFO] Hash {entity_hash} introuvable dans {definition}.")
        return entity
