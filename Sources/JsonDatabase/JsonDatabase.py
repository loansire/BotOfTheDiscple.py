import json
import os
from Sources.Utils import Config
from Sources.JsonDatabase import JsonDbDefines


def LoadJsonDatabase():
	global jsonDatabase

	if not os.path.exists(Config.JSON_DATABASE):
		with open(Config.JSON_DATABASE, 'w', encoding='utf-8') as file:
			json.dump({}, file) 

	with open(Config.JSON_DATABASE, 'r', encoding='utf-8') as file:
		jsonDatabase = json.load(file)

def SaveJsonDatabase():
	with open(Config.JSON_DATABASE, "w", encoding="utf-8") as file:
		json.dump(jsonDatabase, file, indent=4)

def SaveActivity(activityName, infos):
	jsonDatabase[activityName] = infos

def AddInfoToActivity(activity_name, infos_to_add):
	#Infos to add must be a map with the correct name & values for the infos
	if activity_name in jsonDatabase:
		jsonDatabase[activity_name] = jsonDatabase[activity_name] | infos_to_add
	else:
		jsonDatabase[activity_name] = infos_to_add

		
def MustForceUpdate(activityName):
	return not activityName in jsonDatabase

def ForceNotUpdate(activityName):
	jsonDatabase[activityName][JsonDbDefines.UPDATED] = False

def GetActivitiesHash():
	activities_hash = {}
	for activity_name in jsonDatabase:
		if not jsonDatabase[activity_name][JsonDbDefines.UPDATED]:
			continue

		if JsonDbDefines.HASH_EXPERT in jsonDatabase[activity_name]:
			activities_hash[jsonDatabase[activity_name][JsonDbDefines.HASH_EXPERT]] = activity_name + ".Expert"
		if JsonDbDefines.HASH_MASTER in jsonDatabase[activity_name]:
			activities_hash[jsonDatabase[activity_name][JsonDbDefines.HASH_MASTER]] =  activity_name + ".Master"

	return activities_hash

def HasBeenUpdated(activityName):
	return activityName in jsonDatabase and jsonDatabase[activityName][JsonDbDefines.UPDATED]


def GetInformations(activity_name):
	return jsonDatabase[Config.LOSTSECTOR]	