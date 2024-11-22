import json

from Sources.Utils import Config
from ..Exceptions import WrongNameException
from ..Exceptions import WrongHashException
from Sources.Utils import RequestAPI


def main(hash_expert, hash_mastery):
	with open(Config.MF_ACTIVITY_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)
		
	filtered_activity_expert = filter_activity_by_hash(json_data, hash_expert)
	filtered_activity_master = filter_activity_by_hash(json_data, hash_mastery)

	if filtered_activity_expert == {}:
		raise WrongHashException.WrongHashException
	
	if filtered_activity_master == {}:
		raise WrongHashException.WrongHashException

	with open(Config.MF_ACTIVITY_LOST_SECTOR_EXPERT, 'w', encoding='utf-8') as file:
		json.dump(filtered_activity_expert, file, indent=4, ensure_ascii=False)
		
	with open(Config.MF_ACTIVITY_LOST_SECTOR_MASTER, 'w', encoding='utf-8') as file:
		json.dump(filtered_activity_master, file, indent=4, ensure_ascii=False)
	

def filter_activity_by_hash(data, hash):
	filtered_activity = ""
	for activity_hash, activity_detail in data.items():
		if(activity_hash == hash):
			filtered_activity = activity_detail
	return filtered_activity	

def get_activity_name_description(search_expert):
	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)
	to_search = ""
	if search_expert:
		to_search = "Expert"
	else:
		to_search = "Maîtrise"

	for activity_hash, activity_details in json_data.items():
		if to_search in activity_details.get('displayProperties').get("name"):
			return activity_details.get('displayProperties').get("name"), activity_details.get('displayProperties').get("description")
	return "", ""
		
def get_activity_destination_and_place_hash():
	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	return json_data[list(json_data.keys())[0]].get("destinationHash"), json_data[list(json_data.keys())[0]].get("placeHash")

def get_activity_pgcr_image():
	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	return json_data[list(json_data.keys())[0]].get("pgcrImage")

def get_reward_item():
	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	rewards = []

	id = 0 #Same rewards for expert and mastery
	rewards_items = json_data[list(json_data.keys())[id]].get("rewards")[0].get("rewardItems")

	for i in range(0, len(rewards_items)):
		rewards.append(rewards_items[i].get("itemHash"))

	return rewards

def get_modifiers(search_expert):
	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	modifiers = []
	if search_expert:
		id = 0
	else:
		id = 1
	modifiers_items = json_data[list(json_data.keys())[id]].get("modifiers")

	for i in range(0, len(modifiers_items)):
		modifiers.append(modifiers_items[i].get("activityModifierHash"))

	return modifiers


