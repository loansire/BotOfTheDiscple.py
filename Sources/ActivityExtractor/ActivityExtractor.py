import json
from Sources.Utils import Config
from Sources.GoogleDocApi import CellDefines
from Sources.GoogleDocApi import GgdocAPI
from Sources.JsonDatabase import JsonDatabase
from Sources.ActivityExtractor import ActivityFilter

def ExtractActivities(force_activity_name = Config.NOACTIVITY):
    print("Extraction began, VRRRRRRRRRRRRRRRRRRRRRRRRRRR")

    print("Opening stuffs")
    GgdocAPI.OpenGGDoc()
    JsonDatabase.LoadJsonDatabase()
    
    Activities = [Config.LOSTSECTOR]

    print("Saving all ggdoc informations")
    for activity_name in Activities:
        mustUpdate, infos = GgdocAPI.GetActivityInformations(activity_name, JsonDatabase.MustForceUpdate(activity_name))
        if force_activity_name == Config.ALLACTIVITIES or force_activity_name == activity_name:
            mustUpdate = True

        if(mustUpdate):
            JsonDatabase.SaveActivity(activity_name, infos)
        else:
            JsonDatabase.ForceNotUpdate(activity_name)

    ActivityFilter.FilterActivies()

    print("Saving DB")
    JsonDatabase.SaveJsonDatabase()

    return