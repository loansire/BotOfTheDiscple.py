import json

from Utils import Config


def main():
	#To make stuff readable in json
	with open(Config.MF_DAMAGE_TYPE_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	with open(Config.MF_DAMAGE_TYPE_FILENAME, "w", encoding='utf-8') as file:
		json_data = json.dump(json_data, file, indent=4, ensure_ascii=False)

	with open(Config.MF_BREAKER_TYPE_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	with open(Config.MF_BREAKER_TYPE_FILENAME, "w", encoding='utf-8') as file:
		json_data = json.dump(json_data, file, indent=4, ensure_ascii=False)

def GetDamageAndBreakerType():
	damage_and_breaker_type = {}

	with open(Config.MF_DAMAGE_TYPE_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	for hash, value in json_data.items():
		damage_and_breaker_type[value.get("displayProperties").get("name")] = Config.BASE_URL + str(value.get("displayProperties").get("icon"))

	with open(Config.MF_BREAKER_TYPE_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	for hash, value in json_data.items():
		damage_and_breaker_type[value.get("displayProperties").get("name")] = Config.BASE_URL + str(value.get("displayProperties").get("icon"))

	return damage_and_breaker_type

