from api.ApiKey import bungie_api
from api.BungieAPI import BungieAPI

if __name__ == "__main__":
    api = BungieAPI(api_key=bungie_api, lang="fr")

    version = api.download_manifest_definitions()
    print(f"Manifest Destiny2 version: {version}")
