import json
from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.Config import FIELDTODELET, DUNGEON_TYPE_HASH, RAID_TYPE_HASH


def if_challenges_filter(data):
    """
    Filtre les éléments du dictionnaire qui contiennent un champ spécifique dans une structure donnée.
    :param data: Le dictionnaire contenant les données.
    :return: Le dictionnaire filtré avec seulement les activités contenant 'challenges'.
    """
    filtered_data = []

    # Parcours de l'activité et vérification de la présence de 'challenges'
    for item in data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', []):
        if 'challenges' in item:
            filtered_data.append(item)

    return filtered_data


def remove_filtered_attributes(data, challenges_filter):
    """
    Supprime les attributs spécifiés dans challenges_filter du noeud
    Response.activities.data.availableActivities, en gérant les clés imbriquées avec '.'

    :param data: Le dictionnaire contenant les données.
    :param challenges_filter: Liste des clés à supprimer.
    :return: Le dictionnaire modifié.
    """

    def remove_nested_key(d, key_path):
        """Supprime une clé imbriquée dans un dictionnaire ou une liste donné un chemin en liste."""
        keys = key_path.split('.')
        if isinstance(d, list):
            for item in d:
                remove_nested_key(item, key_path)
        elif isinstance(d, dict):
            if len(keys) == 1:
                d.pop(keys[0], None)
            else:
                next_key = keys[0]
                if next_key in d:
                    remove_nested_key(d[next_key], '.'.join(keys[1:]))

    # Récupérer la liste des activités normalement
    activities = data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', [])

    # Suppression des clés imbriquées spécifiées dans chaque activité
    for activity in activities:
        for key in challenges_filter:
            remove_nested_key(activity, key)

    # Mise à jour de la structure des données
    data['Response']['activities']['data']['availableActivities'] = activities
    return data


def get_only_challenges_activities(data):
    """
    Fusionne les fonctions if_challenges_filter() & remove_filtered_attributes() & if_DungeonRaid_filter()

    :param data: Le dictionnaire contenant les données.
    :return: Le dictionnaire modifié.
    """
    print("filter 'challenge' weekly")
    # Applique un filtre pour ne garder que les éléments avec 'challenges'
    filtered_data = if_challenges_filter(data)

    print("delete miscellaneous attributes")
    # Appliquer un second filtre pour retirer les attributs spécifiques
    final_data = remove_filtered_attributes({"Response": {"activities": {"data": {"availableActivities": filtered_data}}}}, FIELDTODELET)

    return final_data


def if_DungeonRaid_filter(filtered_data):
    """
    Filtre les activités en ne gardant que celles dont le type d'activité est un donjon (DUNGEON_TYPE_HASH) ou un raid (RAID_TYPE_HASH).
    :param filtered_data: Un dictionnaire contenant les activités.
    :return: Une liste des activités filtrées qui sont soit un donjon, soit un raid.
    """
    filtered_dungeon_raid = []

    # Vérifier si les clés nécessaires sont présentes
    activities = filtered_data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', [])

    filtered_dungeon_raid = [activity for activity in activities if
                             str(activity.get('activityTypeHash', '')) in [str(DUNGEON_TYPE_HASH), str(RAID_TYPE_HASH)]]

    return filtered_dungeon_raid


if __name__ == "__main__":
    MainJson = get_bungie_character_data()

    # Vérifier si MainJson est une chaîne et la convertir en dictionnaire si nécessaire
    if isinstance(MainJson, str):
        MainJson = json.loads(MainJson)

    MainJson = get_only_challenges_activities(MainJson)
    #MainJson = if_challenges_filter(MainJson)

    print(json.dumps(MainJson, indent=2, ensure_ascii=False))