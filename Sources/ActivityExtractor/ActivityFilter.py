import json
import os
from Sources.Utils import Download
from Sources.Utils import Config
from Sources.LostSector.Manifests import JsonReader
from Sources.JsonDatabase import JsonDatabase

def FilterActivies():

    print("Filtering activities")
    Download.download_manifest(Config.MAIN_MF_URL, Config.MAIN_MF_OUTPUT_FILE, 3, 1);
    print("Main MF downloaded succesfully")

    ActivityDefinitionPath = JsonReader.GetManifestPathInMainManifest(Config.MF_ACTIVITY_DEFINITION)
    Download.download_manifest(Config.BASE_URL + ActivityDefinitionPath, Config.MF_ACTIVITY_FILENAME)
    print("-------------> MF downloaded : " + ActivityDefinitionPath + "\n")

    GetSpecificsManifests()

    return

def GetSpecificsManifests():

    activities_hash = JsonDatabase.GetActivitiesHash()

    with open(Config.MF_ACTIVITY_FILENAME, "r", encoding='utf-8') as file:
        json_data = json.load(file)

    for activity_hash, activity_detail in json_data.items():
        if activity_hash in activities_hash:
            file_name = "local_definitions/" + activities_hash[activity_hash] + ".json"
            with open(Config.TempPath(file_name), 'w', encoding='utf-8') as file:
                json.dump(activity_detail, file, indent=4, ensure_ascii=False)
                print("Created a new activity file : " + file_name)


    
