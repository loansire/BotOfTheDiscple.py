# -*- coding: utf-8 -*-
#import extern
import os

#import intern
from Sources.Utils import Config
from Sources.Utils import Download
from Sources.Utils import ModifierModif
from Sources.Utils import ActivityInfos
from Sources.JsonDatabase import JsonDatabase
from Sources.JsonDatabase import JsonDbDefines

from Sources.GoogleDocApi import GgdocAPI

from .Manifests import JsonReader
from .Manifests import ActivityDefinition
from .Requests import DestinationDefinition
from .Requests import PlaceDefinition
from .Requests import InventoryItemDefinition
from .Requests import ModifierDefinition
from .Manifests import BreakerDamageType

from .Exceptions import WrongNameException

from .Html import HtmlFiller

def DownloadManifest(path_to_download, path_to_save, download_all = False):
    ManifestPath = JsonReader.GetManifestPathInMainManifest(path_to_download)
    Download.download_manifest(Config.BASE_URL + ManifestPath, path_to_save)
    print("-------------> MF downloaded : " + ManifestPath + "\n")

def Treatment():
    #Variables to fill for the Html page
    #Expert
    E_activity_hash = 0
    E_modifier = []
    E_power = 0
    E_Shields = {}
    E_Champs = {}
    #Maitrise
    M_activity_hash = 0
    M_modifier = []
    M_power = 0
    M_Shields = {}
    M_Champs = {}
    #Common
    C_activity_name = ""
    C_activity_description = ""
    C_destination_hash = 0
    C_destination_name = ""
    C_place_hash = 0
    C_place_name = ""
    C_pgcr_image_link = ""
    C_rewards = []
    C_damange_breaker_type = {}
    C_surcharge1 = "Solaires"
    C_surcharge2 = "Abyssal"
    #JsonDatabase
    C_json_infos = {}

    activity_informations = JsonDatabase.GetInformations(Config.LOSTSECTOR)

    C_activity_name, C_surcharge1, C_surcharge2, E_power, M_power, E_Shields, M_Shields, E_Champs, M_Champs = activity_informations[JsonDbDefines.ACTIVITY_NAME], activity_informations[JsonDbDefines.SURCHARGE1], activity_informations[JsonDbDefines.SURCHARGE2], activity_informations[JsonDbDefines.POWER_EXPERT], activity_informations[JsonDbDefines.POWER_MASTER], activity_informations[JsonDbDefines.SHIELDS_EXPERT], activity_informations[JsonDbDefines.SHIELDS_MASTER], activity_informations[JsonDbDefines.CHAMPS_EXPERT], activity_informations[JsonDbDefines.CHAMPS_MASTER]


    C_destination_hash, C_place_hash = ActivityDefinition.get_activity_destination_and_place_hash()
    C_pgcr_image_link = Config.BASE_URL + ActivityDefinition.get_activity_pgcr_image()
    C_json_infos[JsonDbDefines.IMAGE_LINK] = C_pgcr_image_link 

    #Rewards
    C_rewards = ActivityDefinition.get_reward_item()
    C_json_infos[JsonDbDefines.REWARDS] = C_rewards

    #Modifiers
    E_modifier = ActivityDefinition.get_modifiers(True)
    M_modifier = ActivityDefinition.get_modifiers(False)
    C_json_infos[JsonDbDefines.MODIFIERS] = { JsonDbDefines.EXPERT : E_modifier, JsonDbDefines.MASTER : M_modifier}

    #################################### Destination Definition ######################################
    print("Destination Definition")
    DestinationDefinition.main(C_destination_hash)
    C_destination_name, C_destination_description = DestinationDefinition.get_destination_name_and_description()
    C_json_infos[JsonDbDefines.DESTINATION] = {JsonDbDefines.NAME : C_destination_name, JsonDbDefines.DESCRIPTION : C_destination_description, JsonDbDefines.HASH : C_destination_hash}

    ################################### Place Definition #############################################
    print("Place Definition")
    PlaceDefinition.main(C_place_hash)
    C_place_name = PlaceDefinition.get_place_name()
    C_json_infos[JsonDbDefines.PLACE] = { JsonDbDefines.NAME : C_place_name, JsonDbDefines.HASH : C_place_hash}


    ################################## Item Definition #############################################
    print("Item Definition")
    for i in range(0, len(C_rewards)):
        C_rewards[i] = (C_rewards[i],) + InventoryItemDefinition.get_ii_name_and_icon(C_rewards[i])

    ################################## Modifier Definition #############################################
    print("Modifier Definition")
    for i in range(0, len(E_modifier)):
        E_modifier[i] = (E_modifier[i],) + ModifierDefinition.get_modifier_name_description_and_icon(E_modifier[i])
    for i in range(0, len(M_modifier)):
        M_modifier[i] = (M_modifier[i],) + ModifierDefinition.get_modifier_name_description_and_icon(M_modifier[i])

    C_surcharges_enum = [ModifierModif.TranslateSurcharge(C_surcharge1), ModifierModif.TranslateSurcharge(C_surcharge2)]
    E_modifier = ModifierModif.ClearModifiers(E_modifier, C_surcharges_enum)
    M_modifier = ModifierModif.ClearModifiers(M_modifier, C_surcharges_enum)

    ################################## Damage and Breaker types #######################################
    print("Damage Manifest")
    DownloadManifest(Config.MF_DAMAGE_TYPE, Config.MF_DAMAGE_TYPE_FILENAME)
    print("Breaker Manifest")
    DownloadManifest(Config.MF_BREAKER_TYPE, Config.MF_BREAKER_TYPE_FILENAME)
    BreakerDamageType.main()
    C_damange_breaker_type = BreakerDamageType.GetDamageAndBreakerType()

    ################################### HtmlFiller ####################################
    HtmlFiller.CopyTemplate()
    HtmlFiller.MainInfos(C_activity_name, C_pgcr_image_link, C_place_name, C_destination_name, C_rewards)
    HtmlFiller.SpecificInfos(E_power, E_Shields, E_Champs, C_damange_breaker_type, E_modifier, True)
    HtmlFiller.SpecificInfos(M_power, M_Shields, M_Champs, C_damange_breaker_type, M_modifier, False)
    
    HtmlFiller.ConvertToJpeg()

    #################################### Fill JsonDatabase #############################

    JsonDatabase.AddInfoToActivity(Config.LOSTSECTOR, C_json_infos)
    JsonDatabase.SaveJsonDatabase()

    ###################################################################################


    return
    

############################################### GETTERS #####################################

def GetActivityName():
    return ActivityInfos.GetActivityName()

def GetPower(aExpert):
    return ActivityInfos.GetPower(aExpert)
    
def GetSurcharges():
    return ActivityInfos.GetSurcharges()

def GetShields(aExpert):
    return ActivityInfos.GetShields(aExpert)
    
def GetChamps(aExpert):
    return ActivityInfos.GetChamps(aExpert)