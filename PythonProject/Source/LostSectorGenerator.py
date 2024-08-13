#import extern
import os

#import intern
from Utils import Config
from Utils import Download
from Utils import GgdocAPI
from Utils import Result
from Utils import ModifierModif
from Utils import ActivityInfos

from Manifests import JsonReader
from Manifests import ActivityDefinition
from Manifests import DestinationDefinition
from Manifests import PlaceDefinition
from Manifests import InventoryItemDefinition
from Manifests import ModifierDefinition
from Manifests import BreakerDamageType

from Html import HtmlFiller

def GenerateActivity():
    main(True)

def main(download_all = False):
    #Variables to fill for the Html page
    #Expert
    E_modifier = []
    E_power = 0
    E_Shields = {}
    E_Champs = {}
    #Maitrise
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
    
    print("Beginning of the programm")
    Config.InitialiseDirs()
    ################################## GGDOC acces PARSING ###################################
    C_activity_name = "Extraction"

    C_activity_name, C_surcharge1, C_surcharge2,E_power, M_power, E_shields, M_Shields, E_Champs, M_Champs = GgdocAPI.main()

    """
    C_activity_name, C_surcharge1, C_surcharge2 = CsvReader.ReadGGDocActivity()
    E_power = CsvReader.GetExpertPower()
    M_power = CsvReader.GetMaitrisePower()
    E_Shields = CsvReader.GetInfosTypes(True, True)
    M_Shields = CsvReader.GetInfosTypes(False, True)
    E_Champs = CsvReader.GetInfosTypes(True, False)
    M_Champs = CsvReader.GetInfosTypes(False, False)"""

    #################################### Main MF ######################################
    print("Main MF")
    print(os.getcwd())
    if(os.path.exists( Config.MAIN_MF_OUTPUT_FILE) and not download_all):
        DownloadManifest(Config.MAIN_MF_URL, Config.MAIN_MF_OUTPUT_FILE, download_all)
        print("Main Manifest already downloaded")
    else:
        Download.download_manifest(Config.MAIN_MF_URL, Config.MAIN_MF_OUTPUT_FILE, 3, 1);
        print("Main Manifest downloaded")

    #################################### Activity Definition ######################################
    print("Activition Definition")
    DownloadManifest(Config.MF_ACTIVITY_DEFINITION, Config.MF_ACTIVITY_FILENAME, download_all)
    #Make Acitivty definition Treatment
    ActivityDefinition.main(C_activity_name)

    C_destination_hash, C_place_hash = ActivityDefinition.get_activity_destination_and_place_hash()
    C_pgcr_image_link = Config.BASE_URL + ActivityDefinition.get_activity_pgcr_image()
    
    #Rewards
    C_rewards = ActivityDefinition.get_reward_item()

    #Modifiers
    E_modifier = ActivityDefinition.get_modifiers(True)
    M_modifier = ActivityDefinition.get_modifiers(False)

    #################################### Destination Definition ######################################
    print("Destination Definition")
    DownloadManifest(Config.MF_DESTINATION_DEFINITION, Config.MF_DESTINATION_FILENAME, download_all)
    DestinationDefinition.main(C_destination_hash)
    C_destination_name, C_destination_description = DestinationDefinition.get_destination_name_and_description()

    ################################### Place Definition #############################################
    print("Place Definition")
    DownloadManifest(Config.MF_PLACE_DEFINITION, Config.MF_PLACE_FILENAME, download_all)
    PlaceDefinition.main(C_place_hash)
    C_place_name = PlaceDefinition.get_destination_name()

    ################################## Item Definition #############################################
    print("Item Definition")
    DownloadManifest(Config.MF_II_DEFINITION, Config.MF_II_FILENAME, download_all)
    InventoryItemDefinition.main(C_rewards)
    for i in range(0, len(C_rewards)):
        C_rewards[i] = (C_rewards[i],) + InventoryItemDefinition.get_ii_name_and_icon(C_rewards[i])

    ################################## Modifier Definition #############################################
    print("Modifier Definition")
    DownloadManifest(Config.MF_MODIFIER_DEFINITION, Config.MF_MODIFIER_FILENAME, download_all)
    ModifierDefinition.main(E_modifier, M_modifier)
    for i in range(0, len(E_modifier)):
        E_modifier[i] = (E_modifier[i],) + ModifierDefinition.get_modifier_name_description_and_icon(E_modifier[i])
    for i in range(0, len(M_modifier)):
        M_modifier[i] = (M_modifier[i],) + ModifierDefinition.get_modifier_name_description_and_icon(M_modifier[i])

    C_surcharges_enum = [ModifierModif.TranslateSurcharge(C_surcharge1), ModifierModif.TranslateSurcharge(C_surcharge2)]
    E_modifier = ModifierModif.ClearModifiers(E_modifier, C_surcharges_enum)
    M_modifier = ModifierModif.ClearModifiers(M_modifier, C_surcharges_enum)

    ################################## Damage and Breaker types #######################################
    print("Damage Manifest")
    DownloadManifest(Config.MF_DAMAGE_TYPE, Config.MF_DAMAGE_TYPE_FILENAME, download_all)
    print("Breaker Manifest")
    DownloadManifest(Config.MF_BREAKER_TYPE, Config.MF_BREAKER_TYPE_FILENAME, download_all)
    BreakerDamageType.main()
    C_damange_breaker_type = BreakerDamageType.GetDamageAndBreakerType()

    ################################### HtmlFiller ####################################
    HtmlFiller.CopyTemplate()
    HtmlFiller.MainInfos(C_activity_name, C_pgcr_image_link, C_place_name, C_destination_name, C_rewards)
    HtmlFiller.SpecificInfos(E_power, E_Shields, E_Champs, C_damange_breaker_type, E_modifier, True)
    HtmlFiller.SpecificInfos(M_power, M_Shields, M_Champs, C_damange_breaker_type, M_modifier, False)
    
    HtmlFiller.ConvertToJpeg()
    
    #################################### Result Viewer ###################################
    Result.WriteResult("Expert", C_activity_name, C_activity_description, C_place_name, C_destination_name, C_pgcr_image_link, C_rewards, E_modifier)
    Result.WriteResult("Maitrise", C_activity_name, C_activity_description, C_place_name, C_destination_name, C_pgcr_image_link, C_rewards, M_modifier)
    
    ################################### Save Infos for Bot ###############################
    
    ActivityInfos.SetActivityName(C_activity_name)
    ActivityInfos.SetPower(True, E_power)
    ActivityInfos.SetPower(False, M_power)
    ActivityInfos.SetSurcharges({C_surcharge1, C_surcharge2})
    ActivityInfos.SetShields(True, E_Shields)
    ActivityInfos.SetShields(False, M_Shields)
    ActivityInfos.SetChamps(True, E_Champs)
    ActivityInfos.SetChamps(False, M_Champs)
    
    #########################################################################################

def DownloadManifest(path_to_download, path_to_save, download_all = False):
    if(os.path.exists(path_to_save) and not download_all):
        print("------> MF already downloaded" + "\n")
    else:
        ActivityDefinitionPath = JsonReader.GetManifestPathInMainManifest(path_to_download)
        Download.download_manifest(Config.BASE_URL + ActivityDefinitionPath, path_to_save)
        print("-------------> MF downloaded : " + ActivityDefinitionPath + "\n")

    

if __name__ == "__main__":
    main(True)
    

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