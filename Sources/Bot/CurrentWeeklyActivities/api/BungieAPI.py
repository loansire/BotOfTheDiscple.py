import requests
import os
import json

from datetime import datetime, timedelta

from engine.definitions import DEFINITION  # <- liste de définitions
from api.ApiKey import bungie_api, character


class BungieAPI:
    """
    Classe permettant d’interagir avec l’API Bungie pour Destiny 2 et
    de gérer un cache local des manifests et définitions.

    Fonctionnalités principales :
    - Téléchargement et mise en cache du manifest Destiny 2.
    - Téléchargement des activités du personnage.
    - Téléchargement local des définitions listées dans Config.DEFINITION.
    - Recherche locale d’une entité par son hash.
    """

    BASE_URL = "https://www.bungie.net/Platform"
    MANIFEST_ENDPOINT = "/Destiny2/Manifest/"
    MANIFEST_FILE = "data/definitions/manifest.json"

    def __init__(self, lang: str = "fr"):
        """
        Initialise la classe BungieAPI.

        Parameters
        ----------
        api_key : str
            Clé API Bungie.
        lang : str, optional
            Langue pour les définitions (par défaut "fr").
        membership_type : int, optional
            Type de membership (ex: 1 = Xbox, 2 = PSN, 3 = Steam).
        destiny_membership_id : str, optional
            ID Bungie du joueur.
        character_id : str, optional
            ID du personnage Destiny 2.
        """
        self.api_key = bungie_api
        self.lang = lang
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key})

        os.makedirs("data/definitions", exist_ok=True)

        # Attributs pour le personnage
        self.membership_type = character["membership_type"]
        self.destiny_membership_id = character["membership_id"]
        self.character_id = character["character_id"]

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
        print(f"[REQUEST] Manifest ...")
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"[HTTP ERROR] {response.status_code} - {response.text}")
            return None

        data = response.json()
        print(f"[BUNGIE] Status={data.get('ErrorStatus')} "
              f"Message={data.get('Message')} "
              f"Code={data.get('ErrorCode')}")
        return data

    def get_character_profile(self, components: list = [204]):
        """
        Récupère les informations du personnage avec cache de 24h
        stocké directement dans le JSON via "timestamp".
        """
        if not all([self.membership_type, self.destiny_membership_id, self.character_id]):
            print("[ERREUR] membership_type, destiny_membership_id ou character_id non défini.")
            return None

        os.makedirs("data/activities", exist_ok=True)
        output_file = "data/activities/CharacterActivities.json"

        # Vérifie si le fichier existe et si le cache est encore valide
        cached_data = self._load_json(output_file)
        if cached_data and "timestamp" in cached_data:
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            if datetime.now() - timestamp < timedelta(hours=24):
                print("[CACHE] Données CharacterActivities valides (<24h), lecture depuis le fichier.")
                # Supprime le champ timestamp avant de retourner les données
                cached_data.pop("timestamp")
                return cached_data

        # Sinon, télécharge depuis l'API
        comp_str = ",".join(map(str, components))
        endpoint = f"/Destiny2/{self.membership_type}/Profile/{self.destiny_membership_id}/Character/{self.character_id}/?components={comp_str}"

        print(f"[REQUEST] Interrogation de l’API pour character_id={self.character_id} avec components={components}")
        data = self._get(endpoint)

        if data is None or "Response" not in data:
            print(f"[ERREUR] Impossible de récupérer les données du personnage {self.character_id}.")
            return None

        # Ajoute le timestamp dans les données avant de sauvegarder
        response_data = data["Response"]
        response_data["timestamp"] = datetime.now().isoformat()
        self._save_json(output_file, response_data)
        print(f"[OK] Données sauvegardées dans CharacterActivities.json")
        return response_data

    @staticmethod
    def _load_json(file_path: str):
        """
        Charge un fichier JSON depuis un chemin donné.

        Parameters
        ----------
        file_path : str
            Chemin du fichier JSON.

        Returns
        -------
        dict | None
            Contenu JSON du fichier, ou None si le fichier n’existe pas.
        """
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @staticmethod
    def _save_json(file_path: str, data: dict, indent: int | None = None):
        """
        Sauvegarde un dictionnaire en fichier JSON.

        Parameters
        ----------
        file_path : str
            Chemin du fichier de sortie.
        data : dict
            Contenu à sauvegarder.
        indent : int | None, optional
            Indentation pour le JSON (None = compact).
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)


    def download_manifest_definitions(self):
        """
        Télécharge et met en cache le manifest Destiny 2,
        ainsi que les définitions listées dans Config.DEFINITION.

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
        local_manifest = self._load_json(self.MANIFEST_FILE)
        if local_manifest and local_manifest.get("version") == version:
            print(f"[CACHE] Manifest déjà à jour (version {version})")
            return version

        print(f"[UPDATE] Nouvelle version manifest détectée : {version}")

        # Sauvegarde du manifest local
        manifest_data = {
            "version": version,
            "lang": self.lang,
            "paths": {k: lang_paths[k] for k in DEFINITION if k in lang_paths}
        }
        self._save_json(self.MANIFEST_FILE, manifest_data, indent=2)

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
                self._save_json(output_path, def_data)
                print(f"[OK] {def_name} sauvegardé ({len(def_data)} entrées)")
            else:
                print(f"[HTTP ERROR] {def_response.status_code} pour {def_name}")

        return version