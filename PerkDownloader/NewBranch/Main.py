#import extern
import logging
from turtle import down

#import intern
import Config
import Download
import JsonReader
import ActivityDefinition
import os


def main(download_all = False):
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
    if(os.path.exists(Config.MF_DESTINY_ACTIVITY_FILENAME) and not download_all ):
        print("Activity Definition MF already downloaded")
    else:
        ActivityDefinitionPath = JsonReader.GetManifestPathInMainManifest(Config.MF_DESTINY_ACTIVITY_DEFINITION)
        Download.download_manifest(Config.BASE_URL + ActivityDefinitionPath, Config.MF_DESTINY_ACTIVITY_FILENAME)
        print("Activity definition manifest downloaded : " + ActivityDefinitionPath)

    #Make Acitivty definition Treatment
    ActivityDefinition.main()

    

if __name__ == "__main__":
    main(False)