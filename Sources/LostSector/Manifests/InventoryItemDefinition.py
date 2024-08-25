import json

from Sources.Utils import Config

def main(ii_hashes):
	with open(Config.MF_II_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_ii_by_hash(json_data, ii_hashes)

	with open(Config.MF_II_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)


def filter_ii_by_hash(data, hashes):
	filtered_ii = {}
	for ii_hash, ii_details in data.items():
		if int(ii_hash) in hashes:
			filtered_ii[ii_hash] = ii_details
	return filtered_ii

def get_ii_name_and_icon(hash):
	with open(Config.MF_II_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	display_properties = json_data.get(str(hash)).get("displayProperties")

	return display_properties.get("name"), Config.BASE_URL + display_properties.get("icon")

