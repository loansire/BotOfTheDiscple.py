import json

from api.BungieAPI import BungieAPI

if __name__ == "__main__":
    api = BungieAPI(lang="fr")

    version = api.download_manifest_definitions()
    print(f"Manifest Destiny2 version: {version}")

    currentActivities = api.get_character_profile()

    # Extraction des hashes
    available_activities_hash = currentActivities.get("activities", {}).get("data", {}).get("availableActivities", [])
    available_interactables_hash = currentActivities.get("activities", {}).get("data", {}).get("availableActivityInteractables", [])

    activity_hashes = [act.get("activityHash") for act in available_activities_hash if act.get("activityHash") is not None]
    interactable_hashes = [inter.get("activityInteractableHash") for inter in available_interactables_hash if inter.get("activityInteractableHash") is not None]

    # Fonction utilitaire pour afficher en tableau avec N éléments par ligne
    def print_table(lst, n=4):
        for i in range(0, len(lst), n):
            print(" | ".join(str(x) for x in lst[i:i+n]))

    print("Available Activities Hashes:")
    print_table(activity_hashes, 4)

    print("\nAvailable Activity Interactables Hashes:")
    print_table(interactable_hashes, 4)

    #test = api.get_definition_entity(
    #    definition="DestinyActivityGraphDefinition",
    #    entity_hash=1733518967
    #)
    #print(json.dumps(test, indent=2, ensure_ascii=False))


