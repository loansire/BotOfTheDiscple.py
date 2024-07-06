import Config
import json

def main(modif_hashes_expert, modif_hashes_maitrise):
	print("Treatment of Destination Definition")
	
	with open(Config.MF_MODIFIER_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_modifier_by_hash(json_data, modif_hashes_expert + modif_hashes_maitrise)

	with open(Config.MF_MODIFIER_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)


def filter_modifier_by_hash(data, hashes):
	filtered_modifiers = {}
	for modifiers_hash, modifier_details in data.items():
		if int(modifiers_hash) in hashes:
			filtered_modifiers[modifiers_hash] = modifier_details
	return filtered_modifiers

def get_modifier_name_description_and_icon(hash):
	with open(Config.MF_MODIFIER_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	display_properties = json_data.get(str(hash)).get("displayProperties")

	if("icon" in display_properties):
		return display_properties.get("name"), display_properties.get("description"), display_properties.get("icon")
	else:
		return display_properties.get("name"), display_properties.get("description"), ""

	

