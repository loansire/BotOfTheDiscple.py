import json
import requests

def get_bungie_character_data(api_key, base_url, character):
    headers = {"X-API-Key": api_key}
    url = f"{base_url}/Destiny2/{character['membership_type']}/Profile/{character['membership_id']}/Character/{character['character_id']}/"
    components = "204"

    print("Getting current activities")
    response = requests.get(url, headers=headers, params={"components": components})

    if response.status_code == 200:
        data = response.json()
        playlist_activities = data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', {})
        flag_activities = data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivityInteractables', {})
        return response, playlist_activities, flag_activities
    else:
        # Assurez-vous de retourner trois valeurs même en cas d'erreur
        return response, None, None

# Exemple d'utilisation
if __name__ == "__main__":
    import Sources.Bot.ApiKey as APIKey
    from Sources.Bot.CurrentWeeklyActivities.APIWraper import BungieAPI

    # Appel de la class BungieAPI(APIKey)
    bungie_api = BungieAPI(APIKey.bungie_api)

    # Exemple d'utilisation de get_bungie_character_data
    response, _, data = bungie_api.get_bungie_character_data()
    print("Response:", response)
    print("Playlist Activities:", json.dumps(data, indent=2, ensure_ascii=False))
    # print("Flag Activities:", json.dumps(flag_activities, indent=2, ensure_ascii=False))
