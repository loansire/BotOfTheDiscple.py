import requests
import json
import Sources.Bot.ApiKey as APIKey
from Sources.Bot.CurrentWeeklyActivities.BungieCharacterActivities import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.BungieEntityDefinition import get_entities_info
from Sources.Bot.CurrentWeeklyActivities.FilterActivities import filter_activities

class BungieAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.bungie.net/Platform"
        self.character = {
            "membership_type": 3,
            "membership_id": "4611686018487115429",
            "character_id": "2305843009487014305"
        }

    def get_bungie_character_data(self):
        return get_bungie_character_data(self.api_key, self.base_url, self.character)

    def get_entities_info(self, entity_type, hash_identifier, parameters=None):
        return get_entities_info(self.api_key, self.base_url, entity_type, hash_identifier, parameters)

    def filter_activities(self, data, activity_types, base_value, value_compare, definition_name, parameters):
        return filter_activities(self, data, activity_types, base_value, value_compare, definition_name, parameters)

if __name__ == "__main__":
    bungie_api = BungieAPI(APIKey.bungie_api)
    response, data, _ = bungie_api.get_bungie_character_data()

    definition_name = "DestinyActivityDefinition"
    value_compare = "activityTypeHash"
    base_value = "activityHash"

    # activity_types = [2043403989] # Hash des types "Raid"
    # parameters = ["activityTypeHash", "displayProperties.name", "pgcrImage", "index"]

    # activity_types = [608898761] # Hash des types "Donjon"
    # parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]

    activity_types = [3851289711] # Hash des types "Solo Ops"
    parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]

    # activity_types = [556925641] # Hash des types "Vanguard Ops"
    # parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]

    # activity_types = [1227821118]  # Hash des types "MissionsExotiques"
    # parameters = ["activityTypeHash", "displayProperties.name", "pgcrImage", "index"]

    filtered_activities = bungie_api.filter_activities(
        data, activity_types, base_value, value_compare, definition_name, parameters
    )

    # Sauvegarde dans data.json (écrase le fichier existant)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(filtered_activities, f, indent=2, ensure_ascii=False)

    print("Filtered Activities saved to data.json:")
    print(json.dumps(filtered_activities, indent=2, ensure_ascii=False))
