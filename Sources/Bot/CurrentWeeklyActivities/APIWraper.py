import requests
import json
import Sources.Bot.ApiKey as APIKey
from Sources.Bot.CurrentWeeklyActivities.BungieCharacterActivities import get_bungie_character_data
from Sources.Bot.CurrentWeeklyActivities.BungieEntityDefinition import get_entities_info
from Sources.Bot.CurrentWeeklyActivities.FilterActivities import get_SoloOps, get_PinnacleOps, get_Raids, get_Dungeons, get_ExoticMission, get_LostSector

class BungieAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.bungie.net/Platform"
        self.character = APIKey.character

    def get_bungie_character_data(self):
        return get_bungie_character_data(self.api_key, self.base_url, self.character)

    def get_entities_info(self, entity_type, hash_identifier, parameters=None):
        return get_entities_info(self.api_key, self.base_url, entity_type, hash_identifier, parameters)

    def get_SoloOps(self, data):
        activity_types = [3851289711]  # Hash des types "Solo Ops"
        parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]
        return get_SoloOps(self, data, activity_types, parameters)

    def get_PinnacleOps(self, data):
        activity_types = [1227821118]  # Hash des types "MissionsExotiques"
        parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]
        return get_PinnacleOps(self, data, activity_types, parameters)

    def get_Raid(self, data):
        activity_types = [2043403989] # Hash des types "Raid"
        parameters = ["activityTypeHash", "displayProperties.name", "pgcrImage", "index"]
        return get_Raids(self, data, activity_types, parameters)

    def get_Dungeon(self, data):
        activity_types = [608898761] # Hash des types "Donjon"
        parameters = ["activityTypeHash", "displayProperties.name", "pgcrImage", "index"]
        return get_Dungeons(self, data, activity_types, parameters)

    def get_ExoticMission(self, data):
        activity_types = [1686739444] # Hash des types "Story"
        parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]
        return get_ExoticMission(self, data, activity_types, parameters)

    def get_LostSector(self, data):
        activity_types = [103143560] # Hash des types "Story"
        parameters = ["activityTypeHash", "originalDisplayProperties.name","destinationHash", "placeHash", "pgcrImage", "index"]
        return get_LostSector(self, data, activity_types, parameters)

if __name__ == "__main__":
    bungie_api = BungieAPI(APIKey.bungie_api)
    response, character_activities, character_interactables = bungie_api.get_bungie_character_data()

    # activity_types = [3851289711, 556925641] # Hash des types "Vanguard Ops"
    # parameters = ["activityTypeHash", "originalDisplayProperties.name", "pgcrImage", "index"]

    # Récupération des activités
    SoloOps = bungie_api.get_SoloOps(character_activities)
    PinnacleOps = bungie_api.get_PinnacleOps(character_activities)
    Raids = bungie_api.get_Raid(character_activities)
    Dungeons = bungie_api.get_Dungeon(character_activities)
    ExoticMissions = bungie_api.get_ExoticMission(character_activities)
    LostSectors = bungie_api.get_LostSector(character_interactables)

    # Dictionnaire pour gérer facilement les sauvegardes
    data_dict = {
        "SoloOps": SoloOps,
        "PinnacleOps": PinnacleOps,
        "Raids": Raids,
        "Dungeons": Dungeons,
        "ExoticMissions": ExoticMissions,
        "LostSectors": LostSectors
    }

    # Sauvegarde chaque variable dans un fichier JSON séparé
    for name, data in data_dict.items():
        filename = f"data/{name}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"{name} saved to {filename}")
