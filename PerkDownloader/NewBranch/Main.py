#import extern
import logging
import os

#import intern
import Config
import Download
import JsonReader
import HtmlFiller
import ModifierModif
from Manifests import ActivityDefinition
from Manifests import DestinationDefinition
from Manifests import PlaceDefinition
from Manifests import InventoryItemDefinition
from Manifests import ModifierDefinition
from Manifests import BreakerDamageType
from ModifierModif import Surcharge
import Result



def main(lost_sector_name, download_all = False):
    #Variables to fill for the Html page
    #Expert
    E_name = ""
    E_description = ""
    E_modifier = []
    E_power = 2020
    #Maitrise
    M_name = ""
    M_description = ""
    M_modifier = []
    M_power = 2030
    #Common
    C_activity_name = lost_sector_name
    C_activity_description = ""
    C_destination_hash = 0
    C_destination_name = ""
    C_destination_description = ""
    C_place_hash = 0
    C_place_name = ""
    C_pgcr_image_link = ""
    C_rewards = []
    C_damange_breaker_type = {}

    # Configuration de la journalisation
    logging.basicConfig(filename='manifest_download.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')
    
    #################################### Main MF ######################################
    print("Main MF")
    if(os.path.exists( Config.MAIN_MF_OUTPUT_FILE) and not download_all):
        print("Main Manifest already downloaded")
    else:
        Download.download_manifest(Config.MAIN_MF_URL, Config.MAIN_MF_OUTPUT_FILE, 3, 1);
        print("Main Manifest downloaded")

    #################################### Activity Definition ######################################
    print("Activition Definition")
    DownloadManifest(Config.MF_ACTIVITY_DEFINITION, Config.MF_ACTIVITY_FILENAME, download_all)
    #Make Acitivty definition Treatment
    ActivityDefinition.main(lost_sector_name)

    E_name, E_description = ActivityDefinition.get_activity_name_description(True)
    M_name, M_description = ActivityDefinition.get_activity_name_description(False)
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

    E_modifier = ModifierModif.ClearModifiers(E_modifier, [Surcharge.Cryo, Surcharge.Solaire])
    M_modifier = ModifierModif.ClearModifiers(M_modifier, [Surcharge.Cryo, Surcharge.Solaire])
        
    ################################## Damage and Breaker types #######################################
    print("Damage and Breaker type")
    DownloadManifest(Config.MF_DAMAGE_TYPE, Config.MF_DAMAGE_TYPE_FILENAME, download_all)
    DownloadManifest(Config.MF_BREAKER_TYPE, Config.MF_BREAKER_TYPE_FILENAME, download_all)
    BreakerDamageType.main()
    C_damange_breaker_type = BreakerDamageType.GetDamageAndBreakerType()

    #################################### Print ######################################
    """             
    print("New expert sector : " + E_name + " with description : " + E_description)
    print("New maitrise sector : " + M_name + " with description : " + M_description)
    print("Destination hash is : " + str(C_destination_hash) + " with name : " + C_destination_name + " and description : " + C_destination_description)
    print("Place hash is : " + str(C_place_hash) + " with name : " + C_place_name)
    print("Pgcr Image link is : " + C_pgcr_image_link)
    for i in range(0, len(C_rewards)):
        print("New reward with hash : " + str(C_rewards[i][0]) + ", and name : " + C_rewards[i][1] + ", and icon : " + C_rewards[i][2])
    
    for i in range(0, len(E_modifier)):
        print("New Expert modifier with hash : " + str(E_modifier[i][0]) + ", and name : " + E_modifier[i][1] + " , and description : " + E_modifier[i][2] + ", and icon : " + E_modifier[i][3])
    for i in range(0, len(M_modifier)):
        print("New Maitrise modifier with hash : " + str(M_modifier[i][0]) + ", and name : " + M_modifier[i][1] + " , and description : " + M_modifier[i][2] + ", and icon : " + M_modifier[i][3])
    """

    ################################### HtmlFiller ####################################
    HtmlFiller.CopyTemplate()
    HtmlFiller.MainInfos(C_activity_name, C_pgcr_image_link, C_place_name, C_destination_name, C_rewards)
    HtmlFiller.ExpertInfos(E_power, E_description, C_damange_breaker_type, E_modifier)
    HtmlFiller.MaitriseInfos(M_power, M_description, C_damange_breaker_type, M_modifier)

    #################################### Result Viewer ###################################
    Result.WriteResult("Expert", C_activity_name, C_activity_description, C_place_name, C_destination_name, C_pgcr_image_link, C_rewards, E_modifier)
    Result.WriteResult("Maitrise", C_activity_name, C_activity_description, C_place_name, C_destination_name, C_pgcr_image_link, C_rewards, M_modifier)

def DownloadManifest(path_to_download, path_to_save, download_all = False):
    if(os.path.exists(path_to_save) and not download_all):
        print(" MF already downloaded")
    else:
        ActivityDefinitionPath = JsonReader.GetManifestPathInMainManifest(path_to_download)
        Download.download_manifest(Config.BASE_URL + ActivityDefinitionPath, path_to_save)
        print("MF downloaded : " + ActivityDefinitionPath)

    

if __name__ == "__main__":
    main("Jardin de l'Exode 2A", False)