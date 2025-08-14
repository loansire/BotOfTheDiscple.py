from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def simplify_keys(data):
    """
    Simplifie les clés d'un dictionnaire en ne gardant que le dernier terme du chemin.
    Exemple: {"originalDisplayProperties.name": "value"} → {"name": "value"}
    """
    simplified = {}
    for key, value in data.items():
        if isinstance(key, str) and '.' in key:
            new_key = key.split('.')[-1]
            simplified[new_key] = value
        else:
            simplified[key] = value
    return simplified

def filter_activities(bungie_api, data, activity_types, base_value, value_compare, definition_name, parameters):
    if data is None:
        return {}

    activity_types = set(activity_types)
    activity_hashes = [str(activity.get(base_value)) for activity in data if activity.get(base_value)]
    filtered_activities = {}
    total_activities = len(activity_hashes)

    def fetch_entity(hash):
        return hash, bungie_api.get_entities_info(definition_name, hash, parameters)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_entity, hash): hash for hash in activity_hashes}

        for future in tqdm(as_completed(futures), total=total_activities, desc="Processing activities"):
            activity_hash, entity_info = future.result()
            if entity_info and entity_info.get(value_compare) in activity_types:
                activity = next(a for a in data if str(a.get(base_value)) == activity_hash)
                # Simplifier et fusionner les données
                simplified_entity_info = simplify_keys(entity_info)
                activity.update(simplified_entity_info)
                filtered_activities[activity_hash] = activity

    print(f"\nProcessing complete. Filtered {len(filtered_activities)} activities.")
    return filtered_activities
