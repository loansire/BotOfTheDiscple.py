import requests
import os
import json

from utils.Config import DEFINITION  # <- liste de définitions


class BungieAPI:
    BASE_URL = "https://www.bungie.net/Platform"
    MANIFEST_ENDPOINT = "/Destiny2/Manifest/"
    MANIFEST_FILE = "data/definitions/manifest.json"

    def __init__(self, api_key: str, lang: str = "fr"):
        self.api_key = api_key
        self.lang = lang
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key})

        os.makedirs("data/definitions", exist_ok=True)

    def _get(self, endpoint: str):
        """Méthode interne GET avec gestion des erreurs Bungie."""
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
        """Charge le manifest local s’il existe."""
        if os.path.exists(self.MANIFEST_FILE):
            with open(self.MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_local_manifest(self, version: str, lang_paths: dict):
        """Sauvegarde le manifest dans un fichier local."""
        manifest_data = {
            "version": version,
            "lang": self.lang,
            "paths": {k: lang_paths[k] for k in DEFINITION if k in lang_paths}
        }
        with open(self.MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    def download_manifest_definitions(self):
        """Télécharge les définitions listées dans Config.py depuis le manifest Destiny2,
        uniquement si la version a changé."""
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
