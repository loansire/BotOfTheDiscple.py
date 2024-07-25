import Config
import json

def main(place_hash):
	with open(Config.MF_PLACE_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_place_by_hash(json_data, place_hash)

	with open(Config.MF_PLACE_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)


def filter_place_by_hash(data, place_hash_searched):
	filtered_place = {}
	for place_hash, place_details in data.items():
		if int(place_hash) == place_hash_searched:
			filtered_place[place_hash] = place_details
	return filtered_place

def get_destination_name():
	with open(Config.MF_PLACE_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	display_properties = json_data[list(json_data.keys())[0]].get("displayProperties")

	return display_properties.get("name")

