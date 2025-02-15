import json

from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.JsonFilter import get_only_challenges_activities, if_weekly_filter
from Sources.Bot.CurrentWeeklyActivities.enrichJSON import add_activityinfo_data

if __name__ == "__main__":
    print("Starting request for Weekly activities ...")
    # Récupère la liste des activités selectionnables en jeu
    MainJson = get_bungie_character_data()

    # Vérifier si MainJson est une chaîne et la convertir en dictionnaire si nécessaire
    if isinstance(MainJson, str):
        MainJson = json.loads(MainJson)

    MainJson = if_weekly_filter(MainJson)

    # clean le résultat
    MainJson = get_only_challenges_activities(MainJson)

    # Ajouter les informations d'activités au MainJson
    current_weekly_activity = add_activityinfo_data(MainJson)

    # Créer le fichier JSON et y écrire les résultats
    with open('weekly_activities.json', 'w', encoding='utf-8') as json_file:
        json.dump(current_weekly_activity, json_file, ensure_ascii=False, indent=2)

    print("Le fichier weekly_activities.json a été créé avec succès.")