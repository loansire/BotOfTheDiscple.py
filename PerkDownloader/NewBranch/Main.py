#import extern
import logging
import os

#import intern
import Config
import Download
import JsonReader
from Manifests import ActivityDefinition
from Manifests import DestinationDefinition


def main(lost_sector_name, download_all = False):
    #Variables to fill for the Html page
    #Expert
    E_name = ""
    E_description = ""
    #Maitrise
    M_name = ""
    M_description = ""
    #Common
    C_destination_hash = ""

    # Configuration de la journalisation
    logging.basicConfig(filename='manifest_download.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')
    
    #Récupérer le manifest principal
    if(os.path.exists( Config.MAIN_MF_OUTPUT_FILE) and not download_all):
        print("Main Manifest already downloaded")
    else:
        Download.download_manifest(Config.MAIN_MF_URL, Config.MAIN_MF_OUTPUT_FILE, 3, 1, True);
        print("Main Manifest downloaded")

    #Récuperer le manifest Activity Definition
    DownloadManifest(Config.MF_ACTIVITY_DEFINITION, Config.MF_ACTIVITY_FILENAME, download_all)
    #Make Acitivty definition Treatment
    ActivityDefinition.main(lost_sector_name)

    #Get Destination Definition Manifest
    DownloadManifest(Config.MF_DESTINATION_DEFINITION, Config.MF_DESTINATION_FILENAME, download_all)



    E_name, E_description = ActivityDefinition.get_activity_name_description(True)
    M_name, M_description = ActivityDefinition.get_activity_name_description(False)
    C_destination_hash = ActivityDefinition.get_activity_destination_hash()

    print("New expert sector : " + E_name + " with description : " + E_description)
    print("New maitrise sector : " + M_name + " with description : " + M_description)
    print("Destination hash is :" + str(C_destination_hash))



def DownloadManifest(path_to_download, path_to_save, download_all = False):
    if(os.path.exists(path_to_save) and not download_all):
        print("Destination Definition MF already downloaded")
    else:
        ActivityDefinitionPath = JsonReader.GetManifestPathInMainManifest(path_to_download)
        Download.download_manifest(Config.BASE_URL + ActivityDefinitionPath, path_to_save)
        print("Destination definition manifest downloaded : " + ActivityDefinitionPath)

    

if __name__ == "__main__":
    main("Jardin de l'Exode 2A", False)