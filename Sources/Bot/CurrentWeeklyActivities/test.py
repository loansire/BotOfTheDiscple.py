import json

# Ouvrir le fichier JSON et charger son contenu
with open('weekly_activities.json', 'r', encoding='utf-8') as json_file:
    data = json.load(json_file)

# Afficher la phrase introductive
print("Les activités de la semaine sont:")

# Vérifier si la structure du JSON contient les données attendues
if 'Response' in data and 'activities' in data['Response'] and 'data' in data['Response']['activities']:
    available_activities = data['Response']['activities']['data'].get('availableActivities', [])

    # Parcourir les activités et afficher 'activityName' avec un tiret devant
    for activity in available_activities:
        if 'activityName' in activity:
            print(f"- {activity['activityName']}")
else:
    print("Les données ne sont pas dans le format attendu.")
