import json

from Sources.Bot.CurrentWeeklyActivities.engine.definitions import RewardItem, ActivityReward, Activity, ActivityInteractable

# ton JSON brut
with open("../data/activities/CharacterActivities.json", "r") as f:
    data = json.load(f)

activities_data = data["activities"]["data"]["availableActivities"]
interactables_data = data["activities"]["data"]["availableActivityInteractables"]

# Transformation en objets Python
activities = []
for act in activities_data:
    rewards = []
    for r in act.get("visibleRewards", []):
        reward_items = [
            RewardItem(item["itemQuantity"]["itemHash"], item["itemQuantity"]["quantity"])
            for item in r.get("rewardItems", [])
        ]
        rewards.append(ActivityReward(reward_items))

    activities.append(Activity(
        activityHash=act["activityHash"],
        isNew=act["isNew"],
        canLead=act["canLead"],
        canJoin=act["canJoin"],
        isCompleted=act["isCompleted"],
        isVisible=act["isVisible"],
        recommendedLight=act.get("recommendedLight"),
        difficultyTier=act.get("difficultyTier"),
        modifierHashes=act.get("modifierHashes", []),
        visibleRewards=rewards
    ))

interactables = [ActivityInteractable(**i) for i in interactables_data]


print("=== Liste des activités disponibles ===")
for act in activities:
    print(f"- Activity {act.activityHash}, Light recommandé: {act.recommendedLight}")
    if act.visibleRewards:
        for reward in act.visibleRewards:
            for item in reward.rewardItems:
                print(f"   → Loot: itemHash={item.itemHash}, quantité={item.quantity}")

print("\n=== Interactables ===")
for inter in interactables:
    print(f"- Interactable {inter.activityInteractableHash} (index {inter.activityInteractableElementIndex})")
