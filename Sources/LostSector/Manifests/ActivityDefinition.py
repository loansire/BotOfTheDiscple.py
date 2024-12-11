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
	with open(Config.MF_ACTIVITY_LOST_SECTOR_EXPERT, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	return json_data.get("destinationHash"), json_data.get("placeHash")

def get_activity_pgcr_image():
	with open(Config.MF_ACTIVITY_LOST_SECTOR_EXPERT, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	return json_data.get("pgcrImage")

def get_reward_item():
	with open(Config.MF_ACTIVITY_LOST_SECTOR_EXPERT, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	rewards = []

	rewards_items = json_data.get("rewards")[0].get("rewardItems")

	rewards = [rewards_items[i].get("itemHash") for i in range(len(rewards_items))]

	return rewards

def get_modifiers(search_expert):

	if search_expert:
		with open(Config.MF_ACTIVITY_LOST_SECTOR_EXPERT, "r", encoding='utf-8') as file:
			json_data = json.load(file)
	else:
		with open(Config.MF_ACTIVITY_LOST_SECTOR_MASTER, "r", encoding='utf-8') as file:
			json_data = json.load(file)

	modifiers_items = json_data.get("modifiers")

	modifiers = [modifiers_items[i].get("activityModifierHash") for i in range(len(modifiers_items))]

	return modifiers


