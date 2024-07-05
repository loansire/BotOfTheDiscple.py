import Config
import json

def main(sector_name):
	print("Treatment of Destination Definition")
	
	with open(Config.MF_ACTIVITY_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_activities_by_mode_type(json_data, sector_name, 87)

	with open(Config.MF_ACTIVITY_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)


def filter_activities_by_mode_type(data, sector_name, mode_type = 87):
	filtered_activities = {}
	description = ""
	for activity_hash, activity_details in data.items():
		if sector_name in activity_details.get('displayProperties').get("name"):
			if "Expert" in activity_details.get('displayProperties').get("description") and description == "":
				description = activity_details.get('displayProperties').get("description")
				filtered_activities[activity_hash] = activity_details
			elif  activity_details.get('displayProperties').get("description") == description:
				filtered_activities[activity_hash] = activity_details
	return filtered_activities

