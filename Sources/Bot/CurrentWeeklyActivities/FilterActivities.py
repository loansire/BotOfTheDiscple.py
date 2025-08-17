from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from Sources.Bot.CurrentWeeklyActivities import Legends_exoMissions


def enrich_rewards(bungie_api, activity):
    if "visibleRewards" not in activity:
        return activity

    rewards = []
    for reward_set in activity["visibleRewards"]:
        for reward_item in reward_set.get("rewardItems", []):
            item_hash = reward_item.get("itemQuantity", {}).get("itemHash")
            quantity = reward_item.get("itemQuantity", {}).get("quantity")
            hasConditionalVisibility = reward_item.get("itemQuantity", {}).get("hasConditionalVisibility")
            if item_hash:
                item_info = bungie_api.get_entities_info(
                    "DestinyInventoryItemDefinition",
                    str(item_hash),
                    ["displayProperties.name", "displayProperties.icon"]
                )
                if item_info:
                    rewards.append({
                        "itemHash": item_hash,
                        "rewardName": item_info.get("name"),
                        "icon": item_info.get("icon"),
                        "quantity": quantity,
                        "hasConditionalVisibility": hasConditionalVisibility
                    })
    del activity["visibleRewards"]
    if rewards:
        activity["rewards"] = rewards
    return activity

def enrich_activityType(bungie_api, activity):
    if "activityTypeHash" not in activity:
        return activity

    activity_type_hash = activity["activityTypeHash"]
    activity_type_info = bungie_api.get_entities_info(
        "DestinyActivityTypeDefinition",
        str(activity_type_hash),
        ["displayProperties.name"]
    )
    if isinstance(activity_type_info, dict) and "name" in activity_type_info:
        activity["activityTypeName"] = activity_type_info["name"]
    return activity

def simplify_activity(activity):
    """Ne garde que les champs essentiels + weapon si applicable"""
    activity_hash = str(activity.get("activityHash"))

    # Construire le mapping {activityHash : weapon, activityHash_expert : weapon}
    EXOTIC_WEAPONS = {}
    for act in Legends_exoMissions.activities:
        if act.get("activityHash"):
            EXOTIC_WEAPONS[str(act["activityHash"])] = act["weapon"]
        if act.get("activityHash_expert"):
            EXOTIC_WEAPONS[str(act["activityHash_expert"])] = act["weapon"]

    weapon = EXOTIC_WEAPONS.get(activity_hash)  # récupère l'arme si le hash correspond

    return {
        "activityHash": activity.get("activityHash"),
        "activityTypeHash": activity.get("activityTypeHash"),
        "name": activity.get("name"),
        "activityTypeName": activity.get("activityTypeName"),
        "pgcrImage": activity.get("pgcrImage"),
        "index": activity.get("index"),
        "rewards": activity.get("rewards", []),
        "weapon": weapon,  # None si pas trouvé
    }

def get_SoloOps(bungie_api, data, activity_types, parameters):
    if data is None:
        return []

    activity_types = set(activity_types)
    activity_hashes = [str(activity.get("activityHash")) for activity in data if activity.get("activityHash")]
    filtered_activities = []
    total_activities = len(activity_hashes)

    def fetch_entity(hash):
        return hash, bungie_api.get_entities_info("DestinyActivityDefinition", hash, parameters)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_entity, hash): hash for hash in activity_hashes}
        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get("activityTypeHash") in activity_types:
                activity = next(a for a in data if str(a.get("activityHash")) == activity_hash)
                activity.update(entity_info)

                # Enrichir le type d'activité
                activity = enrich_activityType(bungie_api, activity)

                # Enrichir les récompenses
                activity = enrich_rewards(bungie_api, activity)

                # Ajouter uniquement les champs souhaités
                filtered_activities.append(simplify_activity(activity))

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities

def get_PinnacleOps(bungie_api, data, activity_types, parameters):
    if data is None:
        return []

    activity_types = set(activity_types)
    activity_hashes = [str(activity.get("activityHash")) for activity in data if activity.get("activityHash")]
    filtered_activities = []
    total_activities = len(activity_hashes)

    def fetch_entity(hash):
        return hash, bungie_api.get_entities_info("DestinyActivityDefinition", hash, parameters)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_entity, hash): hash for hash in activity_hashes}
        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get("activityTypeHash") in activity_types:
                activity = next(a for a in data if str(a.get("activityHash")) == activity_hash)
                activity.update(entity_info)

                # Enrichir le type d'activité
                activity = enrich_activityType(bungie_api, activity)

                # Enrichir les récompenses
                activity = enrich_rewards(bungie_api, activity)

                # Ajouter uniquement les champs souhaités
                filtered_activities.append(simplify_activity(activity))

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities

def get_Raids(bungie_api, data, activity_types, parameters):
    if data is None:
        return []

    activity_types = set(activity_types)
    activity_hashes = [str(activity.get("activityHash")) for activity in data if activity.get("activityHash")]
    filtered_activities = []
    total_activities = len(activity_hashes)

    def fetch_entity(hash):
        return hash, bungie_api.get_entities_info("DestinyActivityDefinition", hash, parameters)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_entity, hash): hash for hash in activity_hashes}
        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get("activityTypeHash") in activity_types:
                activity = next(a for a in data if str(a.get("activityHash")) == activity_hash)
                activity.update(entity_info)

                # Enrichir le type d'activité
                activity = enrich_activityType(bungie_api, activity)

                # Enrichir les récompenses
                activity = enrich_rewards(bungie_api, activity)

                # Ajouter uniquement les champs souhaités
                filtered_activities.append(simplify_activity(activity))

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities

def get_Dungeons(bungie_api, data, activity_types, parameters):
    if data is None:
        return []

    activity_types = set(activity_types)
    activity_hashes = [str(activity.get("activityHash")) for activity in data if activity.get("activityHash")]
    filtered_activities = []
    total_activities = len(activity_hashes)

    def fetch_entity(hash):
        return hash, bungie_api.get_entities_info("DestinyActivityDefinition", hash, parameters)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_entity, hash): hash for hash in activity_hashes}
        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get("activityTypeHash") in activity_types:
                activity = next(a for a in data if str(a.get("activityHash")) == activity_hash)
                activity.update(entity_info)

                # Enrichir le type d'activité
                activity = enrich_activityType(bungie_api, activity)

                # Enrichir les récompenses
                activity = enrich_rewards(bungie_api, activity)

                # Ajouter uniquement les champs souhaités
                filtered_activities.append(simplify_activity(activity))

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities

def get_ExoticMission(bungie_api, data, activity_types, parameters):
    if data is None:
        return []

    exotimissions = Legends_exoMissions.activities

    # Construire un set de tous les hash exotiques (normal + expert)
    exotic_hashes = {
        str(act["activityHash"]) for act in exotimissions if act.get("activityHash")
    } | {
        str(act["activityHash_expert"]) for act in exotimissions if act.get("activityHash_expert")
    }

    activity_types = set(activity_types)

    # On ne garde que les activityHash qui sont dans data ET dans exoticmissions
    activity_hashes = [
        str(activity.get("activityHash"))
        for activity in data
        if activity.get("activityHash") and str(activity.get("activityHash")) in exotic_hashes
    ]

    filtered_activities = []
    total_activities = len(activity_hashes)

    def fetch_entity(hash):
        return hash, bungie_api.get_entities_info("DestinyActivityDefinition", hash, parameters)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_entity, hash): hash for hash in activity_hashes}

        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get("activityTypeHash") in activity_types:
                activity = next(a for a in data if str(a.get("activityHash")) == activity_hash)
                activity.update(entity_info)

                # Enrichir le type d'activité
                activity = enrich_activityType(bungie_api, activity)

                # Enrichir les récompenses
                activity = enrich_rewards(bungie_api, activity)

                simplified = simplify_activity(activity)

                # --- Debug : voir si une mission correspond ---
                mission = next(
                    (exo for exo in exotimissions if str(exo.get("activityHash")) == activity_hash
                     or str(exo.get("activityHash_expert")) == activity_hash),
                    None
                )

                if not mission:
                    print(f"[DEBUG] Pas trouvé mission pour activité {activity_hash}")
                elif "weapon" not in mission:
                    print(f"[DEBUG] Mission {activity_hash} n’a pas de clé 'weapon'")
                else:
                    weapon = mission["weapon"]
                    weapon_hash = str(weapon.get("hash"))
                    print(f"[DEBUG] Mission {activity_hash} -> Weapon hash = {weapon_hash}")

                    if weapon_hash:
                        parameters_icon = ["displayProperties.icon"]

                        weapon_info = bungie_api.get_entities_info("DestinyInventoryItemDefinition", weapon_hash, parameters_icon)
                        if weapon_info:
                            icon = weapon_info.get("icon")
                            print(f"[DEBUG] Weapon info récupéré pour {weapon_hash} : icon={icon}")
                            simplified["weapon"] = {**weapon, "icon": icon}
                        else:
                            print(f"[DEBUG] get_entities_info a renvoyé None pour weapon {weapon_hash}")

                filtered_activities.append(simplified)

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities

def get_LostSector(bungie_api, data, activity_types, parameters):
    if data is None:
        return []

    activity_types = set(activity_types)
    activity_hashes = []

    # Étape 1 : récupérer les activityHash depuis DestinyActivityInteractableDefinition
    activity_hashes = set()  # utiliser un set directement

    def fetch_interactable(interactable_hash):
        return interactable_hash, bungie_api.get_entities_info(
            "DestinyActivityInteractableDefinition", interactable_hash, parameters=["entries"]
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_interactable, item["activityInteractableHash"]): item for item in data}
        for future in tqdm(as_completed(futures), total=len(data), desc="Processing interactables"):
            interactable_hash, entity_info = future.result()
            if entity_info and entity_info.get("entries"):
                for entry in entity_info.get("entries", []):
                    ah = entry.get("activityHash")
                    if ah:
                        # si c'est une liste, prendre le premier élément
                        if isinstance(ah, list):
                            activity_hashes.add(str(ah[0]))
                        else:
                            activity_hashes.add(str(ah))
                        break  # sortir de la boucle après le premier trouvé

    # Étape 2 : traiter les activityHash comme d'habitude
    filtered_activities = []
    total_activities = len(activity_hashes)

    def fetch_activity(hash):
        return hash, bungie_api.get_entities_info("DestinyActivityDefinition", hash, parameters)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_activity, hash): hash for hash in activity_hashes}
        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get("activityTypeHash") in activity_types:
                activity = {"activityHash": activity_hash}
                activity.update(entity_info)

                # Enrichir le type d'activité
                activity = enrich_activityType(bungie_api, activity)

                # Enrichir les récompenses
                activity = enrich_rewards(bungie_api, activity)

                # Ajouter uniquement les champs souhaités
                filtered_activities.append(simplify_activity(activity))

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities






