import requests
import json
import Sources.Bot.ApiKey as APIKey


def get_bungie_character_data(membership_type=3, membership_id="4611686018487115429",
                              character_id="2305843009487014305"):
    """
    Récupère les données du personnage Destiny 2 via l'API de Bungie.
    Retourne le contenu du JSON formaté.
    """
    API_KEY = APIKey.bungie_api
    BASE_URL = "https://www.bungie.net/Platform/Destiny2/{membership_type}/Profile/{membership_id}/Character/{character_id}/"
    components = "204"

    url = BASE_URL.format(membership_type=membership_type, membership_id=membership_id, character_id=character_id)
    headers = {"X-API-Key": API_KEY}

    response = requests.get(url, headers=headers, params={"components": components})
    if response.status_code == 200:
        return json.dumps(response.json(), indent=2, ensure_ascii=False)
    else:
        return f"Erreur {response.status_code}: {response.text}"


# Exemple d'utilisation
if __name__ == "__main__":
    print(get_bungie_character_data())