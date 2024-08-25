import json
import os

from Sources.Utils import Config

def WriteResult(filename, activity_name, activity_description, activity_place, activity_destination, pgcr_image, rewards, modifiers):

    rewards_json = []

    for reward in rewards:
        rewards_json.append({
            "Reward Name" : reward[1],
            "Reward Icon" : reward[2]
            })
    

    modifiers_json = []
    for modifier in modifiers:
        modifiers_json.append({
            "Modifier Name" : modifier[1],
            "Modifier Description" : modifier[2],
            "Modifier Icon" : modifier[3]
            })

    activite = {
    "Activity Name": activity_name,
    "Activity Description": activity_description,
    "Place": activity_place,
    "Destination" : activity_destination,
    "Background image link" : pgcr_image,
    "Rewards" : rewards_json,
    "Modifiers" : modifiers_json
    }

    result_path = Config.RessourcePath("Results\\" + filename + ".json")

    os.makedirs(os.path.dirname(result_path), exist_ok=True)

    with open(result_path, 'w', encoding='utf-8') as file:
        json.dump(activite, file, ensure_ascii=False, indent=4)