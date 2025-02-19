import json

from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.JsonFilter import get_only_challenges_activities, if_weekly_filter
from Sources.Bot.CurrentWeeklyActivities.SimilareActivityMerge import merge_nightfall, merge_dungeon_raid, \
    merge_exotic_missions
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

    with open('weekly_activities.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Appliquer la fonction merge_nightfall
    merged_nightfall = merge_nightfall(data)

    # Appliquer la fonction merge_dungeon_raid
    merged_dungeon_raid = merge_dungeon_raid(data)

    # Appliquer la fonction merge_exotic_missions
    merged_exotic_missions = merge_exotic_missions(data)

    # Fusionner les deux structures : ajouter merged_nightfall dans la liste merged_dungeon_raid
    merged_activities = merged_dungeon_raid + [merged_nightfall] + [merged_exotic_missions]

    # Sauvegarder les résultats dans un nouveau fichier
    with open('merged_activities.json', 'w', encoding='utf-8') as outfile:
        json.dump(merged_activities, outfile, indent=2, ensure_ascii=False)

    print("Les activités ont été fusionnées et enregistrées dans 'merged_activities.json'.")

    # Ouvrir le fichier JSON et charger son contenu
    with open('merged_activities.json', 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # Afficher la phrase introductive
    print("Les activités de la semaine sont:")

    # Vérifier que la structure du JSON contient les données attendues
    if isinstance(data, list):  # Les activités sont directement dans une liste
        # Créer un dictionnaire pour regrouper les 'activityName' par 'activityTypeName'
        activities_by_type = {}

        # Parcourir les activités
        for activity in data:
            activity_name = activity.get('activityName')
            activity_type = activity.get('activityTypeName')

            # Vérifier si les deux clés existent
            if activity_name and activity_type:
                if activity_type not in activities_by_type:
                    activities_by_type[activity_type] = []

                activities_by_type[activity_type].append(activity_name)

        # Afficher les activités regroupées par 'activityTypeName'
        for activity_type, activity_names in activities_by_type.items():
            print(f"{activity_type} :")
            for name in activity_names:
                print(f"- {name}")
    else:
        print("Les données ne sont pas dans le format attendu.")