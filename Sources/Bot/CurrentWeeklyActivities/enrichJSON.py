import requests
import json
import Sources.Bot.ApiKey as APIKey
from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.JsonFilter import get_only_challenges_activities

# Clé API Bungie (remplacez par la vôtre)
API_KEY = APIKey.bungie_api
BASE_URL = "https://www.bungie.net/Platform/Destiny2/Manifest/"
BUNGIE_BASE_URL = "https://www.bungie.net"

# Fonction pour effectuer une requête à l'API Bungie et obtenir le manifest
def get_manifest():
    headers = {"X-API-Key": API_KEY}
    response = requests.get(BASE_URL, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur lors de la récupération du manifest : {response.status_code}")
        return None


# Fonction pour récupérer les détails de l'activité (DestinyActivityDefinition)
def get_activity_details(activity_hash, manifest):
    # Récupérer l'URL du fichier contenant les informations sur les activités
    destiny_activity_definition_url = manifest.get('Response', {}).get('jsonWorldComponentContentPaths', {}).get('fr', {}).get('DestinyActivityDefinition', None)
    if destiny_activity_definition_url:
        # Ajouter le schéma manquant pour former une URL complète
        full_url = BUNGIE_BASE_URL + destiny_activity_definition_url
        # Télécharger le fichier JSON contenant les activités
        response = requests.get(full_url)
        if response.status_code == 200:
            activity_data = response.json()
            # Rechercher l'activité par hash
            activity_info = activity_data.get(str(activity_hash), {})
            if activity_info:
                return activity_info.get('displayProperties', {}).get('name', 'Nom inconnu'), activity_info.get('activityTypeHash', None), activity_info.get('activityLightLevel', None)
    return None


# Fonction pour récupérer les détails du type d'activité (DestinyActivityTypeDefinition)
def get_activity_type_details(activity_type_hash, manifest):
    # Récupérer l'URL du fichier contenant les informations sur les types d'activités
    destiny_activity_type_url = manifest.get('Response', {}).get('jsonWorldComponentContentPaths', {}).get('fr', {}).get('DestinyActivityTypeDefinition', None)
    if destiny_activity_type_url:
        # Ajouter le schéma manquant pour former une URL complète
        full_url = BUNGIE_BASE_URL + destiny_activity_type_url
        # Télécharger le fichier JSON contenant les types d'activités
        response = requests.get(full_url)
        if response.status_code == 200:
            activity_type_data = response.json()
            # Rechercher le type d'activité par hash
            activity_type_info = activity_type_data.get(str(activity_type_hash), {})
            if activity_type_info:
                return activity_type_info.get('displayProperties', {}).get('name', 'Type d\'activité inconnu')
    return None


# Fonction principale pour ajouter les informations d'activités au MainJson
def add_activityinfo_data(MainJson):
    # Vérifier si la clé 'availableActivities' existe et si c'est une liste
    activities = MainJson.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', [])

    # Récupérer le manifest une seule fois
    manifest = get_manifest()
    if not manifest:
        print("Erreur lors de la récupération du manifest.")
        return MainJson  # Retourner les données sans modification si le manifest n'est pas récupéré

    # Parcours des activités disponibles
    for i, item in enumerate(activities):
        if isinstance(item, dict):  # Assurer que chaque élément est un dictionnaire
            activity_hash = item.get('activityHash')
            if activity_hash:
                # Récupérer les informations sur l'activité
                activity_details = get_activity_details(activity_hash, manifest)
                if activity_details:
                    name, activity_type_hash, light_level = activity_details

                    # Récupérer les détails du type d'activité
                    activity_type_name = get_activity_type_details(activity_type_hash,
                                                                   manifest) if activity_type_hash else None

                    # Construire le dictionnaire avec les clés obligatoires
                    new_activity = {
                        'activityName': name,
                        'activityHash': activity_hash,
                        'activityTypeName': activity_type_name,
                        'activityTypeHash': activity_type_hash,
                    }

                    # Ajouter les clés conditionnelles si elles ne sont pas vides
                    if item.get('challenges'):
                        new_activity['challenges'] = item['challenges']

                    if item.get('modifierHashes'):
                        new_activity['modifierHashes'] = item['modifierHashes']

                    # Remplacer l'activité existante par la nouvelle version ordonnée
                    activities[i] = new_activity
        else:
            print(f"Élément ignoré car ce n'est pas un dictionnaire : {item}")

    # Retourner le JSON mis à jour
    return MainJson


# Exemple d'utilisation avec un JSON MainJson
if __name__ == "__main__":
    # Exemple de données JSON
    MainJson = get_bungie_character_data()  # Cette fonction renvoie maintenant une chaîne JSON

    # Convertir MainJson en dictionnaire si c'est une chaîne JSON
    if isinstance(MainJson, str):
        MainJson = json.loads(MainJson)  # Convertir la chaîne JSON en dictionnaire

    # Récupère uniquement les activitées posédant un challenge + clean le résultat
    MainJson = get_only_challenges_activities(MainJson)

    # Ajouter les informations d'activités au MainJson
    updated_json = add_activityinfo_data(MainJson)

    # Afficher les résultats de manière jolie
    print(json.dumps(updated_json['Response']['activities']['data']['availableActivities'], ensure_ascii=False, indent=2))

