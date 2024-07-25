import Config
import json

def main(destination_hash):
	with open(Config.MF_DESTINATION_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_destination_by_hash(json_data, destination_hash)

	with open(Config.MF_DESTINATION_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)


def filter_destination_by_hash(data, destination_hash_searched):
	filtered_destination = {}
	for destination_hash, destination_details in data.items():
		if int(destination_hash) == destination_hash_searched:
			filtered_destination[destination_hash] = destination_details
	return filtered_destination

def get_destination_name_and_description():
	with open(Config.MF_DESTINATION_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	display_properties = json_data[list(json_data.keys())[0]].get("displayProperties")

	return display_properties.get("name"), display_properties.get("description")

