import requests
import os
import json

api_key = ApiKey.bungie_api
HEADERS = {
    'X-API-Key': api_key
}

# Variables Personnage de Loan
membership_type = 3
membership_id = '4611686018487115429'
character_id = '2305843009487014305'


def download_manifest_json():
    # Récupérer l'URL du manifeste en JSON
    url = "https://www.bungie.net/Platform/Destiny2/Manifest/"
    response = requests.get(url, headers=HEADERS)
    manifest_url = "https://www.bungie.net" + response.json()['Response']['jsonWorldContentPaths'][
        'fr']  # 'fr' pour le fichier en français

    # Télécharge le manifeste JSON
    manifest_file = "manifest.json"
    with open(manifest_file, "wb") as f:
        f.write(requests.get(manifest_url).content)
    return manifest_file


def load_manifest_data(manifest_file):
    with open(manifest_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_activity_details(activity_hash, manifest_data):
    # Recherche de l'activité dans DestinyActivityDefinition
    activity_data = manifest_data['DestinyActivityDefinition'].get(str(activity_hash))
    if activity_data:
        name = activity_data['displayProperties']['name']
        activity_type_hash = activity_data.get('activityTypeHash')
        # Recherche du nom du type d'activité dans DestinyActivityModeDefinition
        activity_type_name = get_activity_type_name(activity_type_hash, manifest_data)
        return name, activity_type_name
    return None, None


def get_activity_type_name(activity_type_hash, manifest_data):
    # Recherche du type d'activité dans DestinyActivityModeDefinition
    if activity_type_hash:
        activity_type_data = manifest_data['DestinyActivityTypeDefinition'].get(str(activity_type_hash))
        if activity_type_data:
            return activity_type_data['displayProperties']['name']
    return "Type inconnu"


def get_current_activity():
    # URL pour récupérer l’activité en cours
    url = f"https://www.bungie.net/Platform/Destiny2/{membership_type}/Profile/{membership_id}/Character/{character_id}/?components=204"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        data = response.json()
        activity_data = data['Response']['activities']['data']
        current_activity_hash = activity_data.get('currentActivityHash', None)

        # Charger les données du manifeste JSON
        manifest_file = download_manifest_json()
        manifest_data = load_manifest_data(manifest_file)

        if current_activity_hash:
            name, activity_type = get_activity_details(current_activity_hash, manifest_data)
            print(f"Le personnage est actuellement dans l'activité : {name} (Type: {activity_type})")
        else:
            print("Le personnage n'est dans aucune activité en ce moment.")
            # Récupérer et afficher les activités disponibles
            available_activities = activity_data.get('availableActivities', [])
            if available_activities:
                print("Activités disponibles :")
                for index, activity in enumerate(available_activities, start=1):
                    activity_hash = activity['activityHash']
                    name, activity_type = get_activity_details(activity_hash, manifest_data)
                    print(f"{index};{activity_type};{name};{activity_hash}")
            else:
                print("Aucune activité disponible.")

        # Supprime le fichier JSON après utilisation
        os.remove(manifest_file)
    else:
        print(f"Erreur lors de la requête API: {response.status_code}")
        print(response.json())


# Appel de la fonction
get_current_activity()