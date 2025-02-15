import requests
import json
import Sources.Bot.ApiKey as APIKey
from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities import Config
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


# Fonction pour récupérer les détails d'un item à partir de son HASH
def from_hash_to_text(hash_value, definition, manifest, fields):
    """
    Récupère des informations spécifiques à partir d'un hash donné dans le manifest Destiny.
    Supporte les chemins imbriqués comme 'displayProperties.name'.

    :param hash_value: Le hash de l'élément à rechercher.
    :param definition: La clé de la définition à utiliser (ex: 'DestinyActivityDefinition').
    :param manifest: Le manifest contenant les informations de Destiny.
    :param fields: Liste des clés à extraire des données récupérées (supporte les chemins imbriqués).
    :return: Un tuple contenant les valeurs demandées, ou None si l'élément n'est pas trouvé.
    """
    destiny_manifest_url = manifest.get('Response', {}).get('jsonWorldComponentContentPaths', {}).get('fr', {}).get(
        definition, None)

    if destiny_manifest_url:
        full_url = BUNGIE_BASE_URL + destiny_manifest_url
        response = requests.get(full_url)

        if response.status_code == 200:
            data = response.json()
            info = data.get(str(hash_value), {})

            if info:
                result = []
                for field in fields:
                    # Supporte les chemins imbriqués
                    keys = field.split('.')  # On découpe les clés par le séparateur '.'
                    value = info
                    for key in keys:
                        value = value.get(key) if isinstance(value, dict) else None
                        if value is None:
                            break
                    result.append(value)

                return tuple(result)

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
                activity_details = from_hash_to_text(activity_hash, Config.MF_ACTIVITY_DEFINITION, manifest, Config.ACTIVITY_FIELDS)
                if activity_details:
                    name, activity_type_hash, originalname, pgcrImage = activity_details

                    # Récupérer les détails du type d'activité
                    activity_type_data = from_hash_to_text(activity_type_hash, Config.MF_ACTIVITY_TYPE_DEFINITION,
                                                           manifest,
                                                           Config.ACTIVITY_TYPE_FIELDS) if activity_type_hash else None
                    activity_type_name = activity_type_data[0] if isinstance(activity_type_data, tuple) and len(
                        activity_type_data) == 1 else activity_type_data

                    # Construire le dictionnaire avec les clés obligatoires
                    new_activity = {
                        'originalname': originalname,
                        'activityName': name,
                        'activityHash': activity_hash,
                        'activityTypeName': activity_type_name,
                        'activityTypeHash': activity_type_hash,
                        'pgcrImage': pgcrImage,
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

