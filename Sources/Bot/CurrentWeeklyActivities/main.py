import json

from Sources.Bot.CurrentWeeklyActivities.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.JsonFilter import get_only_challenges_activities, if_weekly_filter
from Sources.Bot.CurrentWeeklyActivities.SimilareActivityMerge import merge_nightfall, merge_dungeon_raid, merge_exotic_missions
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

    if isinstance(data, list):
        activities_by_type = {}
        surcharges = set()

        for activity in data:
            activity_name = activity.get('activityName')
            activity_type = activity.get('activityTypeName')

            if activity_name and activity_type:
                activities_by_type.setdefault(activity_type, []).append(activity_name)

            # Recherche des surcharges dans les Nuit noire
            if activity_type == "Nuit noire":
                modifier_details = activity.get('modifierDetails', {})
                for key, mod_list in modifier_details.items():
                    if isinstance(mod_list, list):
                        for item in mod_list:
                            name = item.get('name', '')
                            if name.lower().startswith("surcharge "):
                                surcharge_name = name[len("surcharge "):].strip()
                                surcharges.add(surcharge_name)

        # Affichage des activités
        for activity_type, names in activities_by_type.items():
            print(f"{activity_type} :")
            for name in names:
                print(f"- {name}")

        # Affichage des surcharges
        if surcharges:
            print("\nLes surcharges de la semaine sont :")
            for s in sorted(surcharges):
                print(f"- {s}")
    else:
        print("Les données ne sont pas dans le format attendu.")