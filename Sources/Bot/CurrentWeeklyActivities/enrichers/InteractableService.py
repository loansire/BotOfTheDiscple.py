# enrichers/InteractableService.py
from enrichers.EnrichmentEngine import EnrichmentEngine

class InteractableService(EnrichmentEngine):
    def __init__(self, current_activities, definitions_dir="data/definitions"):
        super().__init__(definitions_dir)
        self.interactables = current_activities.get("activities", {}).get("data", {}).get("availableActivityInteractables", [])

    def enrich(self):
        """Enrichit chaque interactable récursivement."""
        enriched = []
        for inter in self.interactables:
            e = self.enrich_object(inter)

            # Exemple : si l’interactable contient une activityHash dans sa définition
            inter_def = e.get("activityInteractableHash_def", {})
            if "entries" in inter_def:
                e["entries_def"] = [
                    self.enrich_object({"activityHash": entry["activityHash"]})
                    for entry in inter_def["entries"]
                ]

            enriched.append(e)
        return enriched
