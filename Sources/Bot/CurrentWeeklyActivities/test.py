import json

# Ouvrir le fichier JSON et charger son contenu
with open('merged_activities.json', 'r', encoding='utf-8') as json_file:
    data = json.load(json_file)

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
