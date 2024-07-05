import Config
import json

def main():
	print("Treatment of ActivityDefinition")

	with open(Config.MF_DESTINY_ACTIVITY_FILENAME, "r", encoding='utf-8') as file:
		json_data = json.load(file)

	filtered_activities = filter_activities_by_mode_type(json_data, 87)

	with open(Config.MF_DESTINY_ACTIVITY_FILTERED_FILENAME, 'w', encoding='utf-8') as file:
		json.dump(filtered_activities, file, indent=4, ensure_ascii=False)


def filter_activities_by_mode_type(data, mode_type = 87):
	filtered_activities = {}
	for activity_hash, activity_details in data.items():
		if activity_details.get('directActivityModeType') == mode_type:
			filtered_activities[activity_hash] = activity_details
	return filtered_activities
