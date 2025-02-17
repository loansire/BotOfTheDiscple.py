# Fusion des infos des originalname Nuit noire
import json


def merge_nightfall(json):
    # Dictionnaire de base avec l'activityName
    merged_activity = {
        "activityName": "",  # Nom de l'activité
    }

    # Liste pour stocker les difficultés trouvées
    difficulties = []

    # Parcourir les activités disponibles
    for activity in json["Response"]["activities"]["data"]["availableActivities"]:
        if activity["originalname"] == "Nuit noire":
            # Extraire le nom de l'activité et en séparer la difficulté
            activity_name_parts = activity["activityName"].split(": ")
            difficulty = activity_name_parts[1] if len(activity_name_parts) > 1 else None
            activity_name = activity["activitydescription"]

            # Initialiser l'activityName si ce n'est pas déjà fait
            if not merged_activity["activityName"]:
                merged_activity["activityName"] = activity_name

            # Ajouter la difficulté à la liste si elle n'est pas déjà présente
            if difficulty and difficulty not in difficulties:
                difficulties.append(difficulty)

    # Ajouter les autres informations après les difficulties
    for activity in json["Response"]["activities"]["data"]["availableActivities"]:
        if activity["originalname"] == "Nuit noire":
            merged_activity["activityTypeName"] = activity["activityTypeName"]
            merged_activity["pgcrImage"] = activity["pgcrImage"]

    # Maintenant, ajouter les modificateurs après pgcrImage
    merged_activity["modifierDetails"] = {}

    # Index pour nommer les modificateurs
    modifier_index = 1

    # Ajouter dynamiquement les modificateurs en les numérotant
    for difficulty in difficulties:
        for activity in json["Response"]["activities"]["data"]["availableActivities"]:
            if activity["originalname"] == "Nuit noire":
                activity_name_parts = activity["activityName"].split(": ")
                activity_difficulty = activity_name_parts[1] if len(activity_name_parts) > 1 else None

                if activity_difficulty == difficulty:
                    # Créer une clé numérotée pour chaque set de modificateurs
                    modifier_key = f"modifier_{modifier_index}_Details"
                    modifier_index += 1

                    # Ajouter les modificateurs associés
                    merged_activity["modifierDetails"][modifier_key] = []

                    # Ajouter les modificateurs sans les hash
                    for modifier in activity["modifierDetails"]:
                        filtered_modifier = {
                            key: value for key, value in modifier.items() if key != "hash"
                        }
                        merged_activity["modifierDetails"][modifier_key].append(filtered_modifier)

    # Retourner l'objet fusionné
    return merged_activity


def merge_dungeon_raid(json):
    merged_activities = []

    # Parcourir les activités disponibles
    for activity in json["Response"]["activities"]["data"]["availableActivities"]:
        activity_type = activity.get("activityTypeName")
        if activity_type in ["Donjon", "Raid"]:
            original_name = activity["originalname"]
            activity_name_parts = activity["activityName"].split(": ")
            difficulty = activity_name_parts[1] if len(activity_name_parts) > 1 else None

            # Vérifier si l'activité avec ce original_name a déjà été fusionnée
            existing_activity = next(
                (act for act in merged_activities if act["activityName"] == original_name and act["activityTypeName"] == activity_type),
                None
            )

            # Si l'activité existe déjà, on ajoute simplement les modificateurs
            if existing_activity:
                # Vérifier si cette activité a des modificateurs
                if "modifierDetails" in activity and activity["modifierDetails"]:
                    modifier_index = len(existing_activity["modifierDetails"]) + 1
                    modifier_key = f"modifier_{modifier_index}_Details"
                    existing_activity["modifierDetails"][modifier_key] = [
                        {k: v for k, v in mod.items() if k != "hash"}
                        for mod in activity["modifierDetails"]
                    ]
                else:
                    # Si l'activité n'a pas de modificateurs, ajouter un modificateur vide
                    modifier_index = len(existing_activity["modifierDetails"]) + 1
                    modifier_key = f"modifier_{modifier_index}_Details"
                    existing_activity["modifierDetails"][modifier_key] = {}

            else:
                # Si l'activité n'existe pas encore, on la crée et on l'ajoute
                merged_activity = {
                    "activityName": original_name,
                    "activityTypeName": activity_type,
                    "pgcrImage": activity["pgcrImage"],
                    "modifierDetails": {}
                }

                # Vérifier si cette activité a des modificateurs
                if "modifierDetails" in activity and activity["modifierDetails"]:
                    modifier_index = 1
                    modifier_key = f"modifier_{modifier_index}_Details"
                    merged_activity["modifierDetails"][modifier_key] = [
                        {k: v for k, v in mod.items() if k != "hash"}
                        for mod in activity["modifierDetails"]
                    ]
                else:
                    # Si l'activité n'a pas de modificateurs, ajouter un modificateur vide
                    merged_activity["modifierDetails"]["modifier_1_Details"] = {}

                # Ajouter la nouvelle activité à la liste fusionnée
                merged_activities.append(merged_activity)

    return merged_activities


def merge_exotic_missions(json):
    merged_activity = {
        "activityName": "",  # On va mettre le originalname ici
        "activityTypeName": "Mission Exotique",  # Toujours "Mission Exotique"
        "pgcrImage": "",  # L'image sera la même pour tous les éléments
        "modifierDetails": {}  # Dictionnaire pour les modificateurs
    }

    modifier_index = 1  # Compteur pour les modificateurs

    # Parcourir les activités disponibles
    for activity in json["Response"]["activities"]["data"]["availableActivities"]:
        activity_type = activity.get("activityTypeName")

        if activity_type == "Histoire":
            # Extraire le originalname et initialiser activityName
            original_name = activity["originalname"]
            if not merged_activity["activityName"]:  # Si pas déjà initialisé
                merged_activity["activityName"] = original_name
                merged_activity["pgcrImage"] = activity["pgcrImage"]  # Prendre la pgcrImage du 1er élément trouvé

            # Ajouter les modificateurs à modifierDetails
            if "modifierDetails" in activity and activity["modifierDetails"]:
                modifier_key = f"modifier_{modifier_index}_Details"
                merged_activity["modifierDetails"][modifier_key] = [
                    {k: v for k, v in mod.items() if k != "hash"}
                    for mod in activity["modifierDetails"]
                ]
                modifier_index += 1  # Incrémenter l'index des modificateurs

    # Retourner le dictionnaire fusionné
    return merged_activity


if __name__ == "__main__":
    # Charger le fichier JSON
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



