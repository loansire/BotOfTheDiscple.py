import json
from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.Config import ChallengesFilter, DUNGEON_HASH, RAID_HASH


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

def if_DungeonRaid_filter(filtered_data):
    """
    Filtre les activités en ne gardant que celles dont le type d'activité est un donjon (DUNGEON_HASH) ou un raid (RAID_HASH).
    :param filtered_data: La liste des activités à filtrer.
    :return: La liste des activités filtrées qui sont soit un donjon, soit un raid.
    """
    filtered_dungeon_raid = []

    # Parcours des activités filtrées
    for activity in filtered_data:
        activity_type_name = activity.get('activityTypeHash')

        # Vérifier si l'activité correspond à un donjon ou un raid
        if activity_type_name in [DUNGEON_HASH, RAID_HASH]:
            filtered_dungeon_raid.append(activity)

    return filtered_dungeon_raid

def remove_filtered_attributes(data, ChallengesFilter):
    """
    Supprime les attributs spécifiés dans ChallengesFilter du noeud
    Response.activities.data.availableActivities.

    :param data: Le dictionnaire contenant les données.
    :param ChallengesFilter: Liste des clés à supprimer.
    :return: Le dictionnaire modifié.
    """
    # Récupérer la liste des activités normalement
    activities = data.get('Response', {}).get('activities', {}).get('data', {}).get('availableActivities', [])

    # Suppression des clés spécifiées dans chaque activité
    for activity in activities:
        for key in ChallengesFilter:
            activity.pop(key, None)  # Supprime la clé si elle existe

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
    final_data = remove_filtered_attributes({"Response": {"activities": {"data": {"availableActivities": filtered_data}}}}, ChallengesFilter)

    return final_data


if __name__ == "__main__":
    MainJson = get_bungie_character_data()

    # Vérifier si MainJson est une chaîne et la convertir en dictionnaire si nécessaire
    if isinstance(MainJson, str):
        MainJson = json.loads(MainJson)

    MainJson = get_only_challenges_activities(MainJson)

    print(json.dumps(MainJson, indent=2, ensure_ascii=False))