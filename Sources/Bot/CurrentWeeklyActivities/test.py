import json

# Ouvrir le fichier JSON et charger son contenu
with open('weekly_activities.json', 'r', encoding='utf-8') as json_file:
    data = json.load(json_file)

# Afficher la phrase introductive
print("Les activités de la semaine sont:")

# Vérifier si la structure du JSON contient les données attendues
if 'Response' in data and 'activities' in data['Response'] and 'data' in data['Response']['activities']:
    available_activities = data['Response']['activities']['data'].get('availableActivities', [])

    # Parcourir les activités et afficher 'activityName' ou 'activityDescription'
    for activity in available_activities:
        if 'activityName' in activity:
            # Vérifier si 'activityName' contient "Nuit Noire"
            if "Nuit noire" in activity['activityName']:
                # Si "Nuit noire" est dans le nom de l'activité, afficher 'activityDescription'
                if 'activitydescription' in activity:
                    print(f"- {activity['activitydescription']}")
                else:
                    print("- Description non disponible")
            else:
                # Sinon, afficher 'activityName'
                print(f"- {activity['activityName']}")
else:
    print("Les données ne sont pas dans le format attendu.")
