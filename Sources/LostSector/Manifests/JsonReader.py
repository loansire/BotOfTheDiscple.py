import json

from Utils import Config


def GetManifestPathInMainManifest(manifest_name):
	with open(Config.MAIN_MF_OUTPUT_FILE, 'r', encoding='utf-8') as file:
		data = json.load(file)

	# Extraire le chemin correspondant à DestinyActivityDefinition
	destiny_activity_definition_path = data['jsonWorldComponentContentPaths']['fr'][manifest_name]

	return destiny_activity_definition_path
