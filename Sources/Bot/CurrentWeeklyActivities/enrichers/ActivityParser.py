# enrichers/ActivityParser.py

import os
import json

class ActivityParser:
    """
    Classe permettant de filtrer et enrichir les données
    provenant de BungieAPI (currentActivities).
    """

    def __init__(self, current_activities: dict, definitions_dir="data/definitions"):
        """
        Parameters
        ----------
        current_activities : dict
            Les données brutes venant de BungieAPI.get_character_profile()
        definitions_dir : str
            Chemin vers le dossier contenant les définitions JSON.
        """
        self.current_activities = current_activities
        self.definitions_dir = definitions_dir

    def _load_definition(self, definition_name: str) -> dict:
        """Charge une définition locale par nom."""
        file_path = os.path.join(self.definitions_dir, f"{definition_name}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def filter_available_activities(self):
        """Retourne uniquement les activityHash des activités disponibles."""
        return [
            act.get("activityHash")
            for act in self.current_activities.get("activities", {}).get("data", {}).get("availableActivities", [])
            if act.get("activityHash") is not None
        ]

    def filter_available_interactables(self):
        """Retourne uniquement les activityInteractableHash disponibles."""
        return [
            inter.get("activityInteractableHash")
            for inter in self.current_activities.get("activities", {}).get("data", {}).get("availableActivityInteractables", [])
            if inter.get("activityInteractableHash") is not None
        ]

    def enrich_activities(self):
        """
        Enrichit les availableActivities avec leurs définitions.
        Retourne une liste de dicts lisibles (nom + description + hash).
        """
        activity_defs = self._load_definition("DestinyActivityDefinition")
        activities = self.current_activities.get("activities", {}).get("data", {}).get("availableActivities", [])

        enriched = []
        for act in activities:
            h = str(act.get("activityHash"))
            defn = activity_defs.get(h, {})
            enriched.append({
                "hash": h,
                "name": defn.get("displayProperties", {}).get("name"),
                "description": defn.get("displayProperties", {}).get("description"),
            })
        return enriched
