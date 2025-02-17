import json

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
