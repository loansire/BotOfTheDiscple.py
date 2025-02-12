import json

from Sources.Bot.CurrentActivity.CharacterActivityRequest import get_bungie_character_data
from Sources.Bot.CurrentActivity.Filter_Library import ChallengesFilter


def if_challenges_filter(data):
    """
    Filtre les éléments du JSON qui contiennent un champ spécifique dans une structure donnée.
    :param data: Le JSON sous forme de str.
    :param filter_key: Le chemin vers le champ à filtrer, sous forme de liste de clés.
    :return: Le JSON filtré sous forme de liste d'éléments.
    """
    # Convertir la chaîne JSON en dictionnaire Python
    json_data = json.loads(data)

    # Naviguer dans la structure pour extraire les éléments avec 'challenges'
    filtered_data = []

    # Parcours de l'activité et vérification de la présence de 'challenges'
    for item in json_data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', []):
        if 'challenges' in item:
            filtered_data.append(item)

    return json.dumps(filtered_data, ensure_ascii=False, indent=2)


def remove_filtered_attributes(data, ChallengesFilter):
    """
    Supprime les attributs spécifiés dans ChallengesFilter du noeud
    Response.activities.data.availableActivities.

    :param data: Le JSON sous forme de str.
    :param ChallengesFilter: Liste des clés à supprimer.
    :return: Le JSON modifié sous forme de str.
    """
    # Convertir la chaîne JSON en objet Python
    json_data = json.loads(data)

    # Vérifier si on a une liste directement
    if isinstance(json_data, list):
        activities = json_data  # json_data est déjà une liste filtrée
    else:
        # Récupérer la liste des activités normalement
        activities = json_data.get('Response', {}) \
            .get('activities', {}) \
            .get('data', {}) \
            .get('availableActivities', [])

    # Suppression des clés spécifiées dans chaque activité
    for activity in activities:
        for key in ChallengesFilter:
            activity.pop(key, None)  # Supprime la clé si elle existe

    # Si json_data était une liste, on renvoie directement la liste modifiée
    if isinstance(json_data, list):
        return json.dumps(json_data, indent=2, ensure_ascii=False)

    # Sinon, on met à jour la structure d'origine et on la retourne
    json_data['Response']['activities']['data']['availableActivities'] = activities
    return json.dumps(json_data, indent=2, ensure_ascii=False)


def get_only_challenges_activities(data):
    """
    Fusionne les fonctions if_challenges_filter() & remove_filtered_attributes()

    :param data: Le JSON sous forme de str.
    :return: Le JSON modifié sous forme de str.
    """
    # Applique un filtre pour ne garder que les éléments avec 'challenges'
    data = if_challenges_filter(data)

    # Appliquer un second filtre pour retirer les attributs spécifiques
    data = remove_filtered_attributes(data, ChallengesFilter)

    return data

if __name__ == "__main__":
    MainJson = get_bungie_character_data()

    #MainJson = if_challenges_filter(MainJson)

    #MainJson = remove_filtered_attributes(MainJson, ChallengesFilter)

    MainJson = get_only_challenges_activities(MainJson)

    print(MainJson)