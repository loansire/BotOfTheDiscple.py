import json
import requests

def get_entities_info(api_key, base_url, definition_name, hash_identifier, parameters=None):
    BASE_URL = f"{base_url}/Destiny2/Manifest/{definition_name}/{hash_identifier}/"
    headers = {"X-API-Key": api_key}
    response = requests.get(BASE_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        item = data.get('Response', {})

        if parameters:
            filtered_item = {}
            for key in parameters:
                if '.' in key:
                    keys = key.split('.')
                    temp_item = item
                    for k in keys:
                        if isinstance(temp_item, dict) and k in temp_item:
                            temp_item = temp_item[k]
                        else:
                            temp_item = None
                            break
                    if temp_item is not None:
                        # On utilise uniquement la dernière partie de la clé
                        filtered_item[keys[-1]] = temp_item
                elif key in item:
                    filtered_item[key] = item[key]
            return filtered_item
        else:
            return item
    else:
        return {"error": f"Failed to retrieve data: {response.status_code}"}

# Exemple d'utilisation
if __name__ == "__main__":
    import Sources.Bot.ApiKey as APIKey
    from Sources.Bot.CurrentWeeklyActivities.APIWraper import BungieAPI

    bungie_api = BungieAPI(APIKey.bungie_api)
    definition_name = "DestinyActivityInteractableDefinition"
    hash_identifier = "2610536081"
    parameters = ["displayProperties.icon"]

    entity_info = bungie_api.get_entities_info(definition_name, hash_identifier, parameters)
    print(json.dumps(entity_info, indent=2, ensure_ascii=False))
