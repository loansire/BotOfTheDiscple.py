import json

from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.JsonFilter import get_only_challenges_activities, if_DungeonRaid_filter
from Sources.Bot.CurrentWeeklyActivities.enrichJSON import add_activityinfo_data

if __name__ == "__main__":
    print("Starting request for Weekly activities ...")
    # Récupère la liste des activités selectionnables en jeu
    MainJson = get_bungie_character_data()

    # Vérifier si MainJson est une chaîne et la convertir en dictionnaire si nécessaire
    if isinstance(MainJson, str):
        MainJson = json.loads(MainJson)

    # Récupère uniquement les activitées posédant un challenge + clean le résultat
    MainJson = get_only_challenges_activities(MainJson)

    # Ajouter les informations d'activités au MainJson
    updated_json = add_activityinfo_data(MainJson)

    current_weekly_dungeonraid = if_DungeonRaid_filter(updated_json)
    print("Type de updated_json:", type(current_weekly_dungeonraid))

    # Afficher les résultats de manière jolie
    print(json.dumps(current_weekly_dungeonraid, ensure_ascii=False, indent=2))