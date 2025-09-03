# enrichers/ActivityService.py
from enrichers.EnrichmentEngine import EnrichmentEngine

class ActivityService(EnrichmentEngine):
    def __init__(self, current_activities, definitions_dir="data/definitions"):
        super().__init__(definitions_dir)
        self.activities = current_activities.get("activities", {}).get("data", {}).get("availableActivities", [])

    def enrich(self):
        """Enrichit chaque activité avec les définitions liées (Activity, Modifiers, Items...)."""
        enriched = []
        for act in self.activities:
            e = self.enrich_object(act)

            # Exemple : enrichir visibleRewards -> rewardItems -> itemHash
            if "visibleRewards" in act:
                e["visibleRewards_def"] = []
                for reward in act["visibleRewards"]:
                    enriched_rewards = []
                    for reward_item in reward.get("rewardItems", []):
                        enriched_rewards.append(self.enrich_object(reward_item.get("itemQuantity", {})))
                    e["visibleRewards_def"].append(enriched_rewards)

            enriched.append(e)

        return enriched
