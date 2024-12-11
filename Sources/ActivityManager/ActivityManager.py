from Sources.ActivityExtractor import ActivityExtractor
from Sources.Utils import Config
from Sources.JsonDatabase import JsonDatabase
from Sources.LostSector import LostSectorGenerator

def GetLatestActivities(force_activity_name = Config.NOACTIVITY):

    ActivityExtractor.ExtractActivities(force_activity_name)

    if JsonDatabase.HasBeenUpdated(Config.LOSTSECTOR):
        LostSectorGenerator.Treatment()
