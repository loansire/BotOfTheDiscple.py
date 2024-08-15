import json

from Utils import Config
from Exceptions import WrongNameException


def main(sector_name):
	with open(Config.MF_ACTIVITY_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_lost_sector(json_data)
	with open(Config.MF_ACTIVITY_FILTERED_GENERAL_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)
		
	filtered_activities = filter_activities_by_name(filtered_activities, sector_name)

	if filtered_activities == {}:
		raise WrongNameException.WrongNameException

	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)

def filter_lost_sector(data):
	filtered_activities = {}
	description = ""
	for activity_hash, activity_details in data.items():
		if activity_details.get("directActivityModeType") == 87:
			filtered_activities[activity_hash] = activity_details
	return filtered_activities

def filter_activities_by_name(data, sector_name):
	filtered_activities = {}
	description = ""
	sector_name_rectified = sector_name.replace(" ", " ")
	for activity_hash, activity_details in data.items():
		if sector_name in activity_details.get('displayProperties').get("name") or sector_name_rectified in activity_details.get('displayProperties').get("name"):
			if "Expert" in activity_details.get('displayProperties').get("description") and description == "":
				description = activity_details.get('displayProperties').get("description")
				filtered_activities[activity_hash] = activity_details
			elif  activity_details.get('displayProperties').get("description") == description:
				filtered_activities[activity_hash] = activity_details
	return filtered_activities		

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


