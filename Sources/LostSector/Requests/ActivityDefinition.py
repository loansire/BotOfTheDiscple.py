import json
from pydoc import describe

from Sources.Utils import RequestAPI

E_activity_data = ""
M_activity_data = ""


def main(lost_sector_name):
	E_activity_hash = ""
	M_activity_hash = ""
	activity_name_json = RequestAPI.RequestByName(lost_sector_name, "DestinyActivityDefinition");

	if activity_name_json == None:
		print("Activity hasn't be found with name")
		return
	
	for result in activity_name_json['Response']['results']['results']:
		
		if 'Expert' in result['displayProperties']['description']:
			if 'Expert' in result['displayProperties']['name']:
				E_activity_hash = result['hash']
			else:
				M_activity_hash = result['hash']
				
	getActivityByHash(E_activity_hash)
	getActivityByHash(M_activity_hash, False)
	

	
def getActivityByHash(hash, is_expert = True):
	data = RequestAPI.RequestByHash(hash, "DestinyActivityDefinition")
	if data == None:
		print("Activity hasn't be found with hash")
		
	if is_expert:
		global E_activity_data
		E_activity_data = data['Response']
	else:
		global M_activity_data
		M_activity_data = data['Response']
		
################################# Getters and Setters

def get_activity_name_description(search_expert):
	if(search_expert):
		data = E_activity_data
	else:
		data = M_activity_data
		
	return data['displayProperties']['name'], data['displayProperties']['description']

def get_activity_destination_and_place_hash():
	return E_activity_data['destinationHash'], E_activity_data['placeHash']

def get_activity_pgcr_image():
	return E_activity_data['pgcrImage']

def get_reward_item():
	rewards = []

	id = 0 #Same rewards for expert and mastery
	rewards_items = E_activity_data['rewards'][0]['rewardItems']
	
	for item_data in rewards_items:
		rewards.append(item_data['itemHash'])

	return rewards

def get_modifiers(search_expert):
	if(search_expert):
		data = E_activity_data
	else:
		data = M_activity_data
		
	modifiers_data = data['modifiers']
	modifiers = []
	
	for modif_data in modifiers_data:
		modifiers.append(modif_data['activityModifierHash'])
		
	return modifiers






		
		

