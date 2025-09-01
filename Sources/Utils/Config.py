import sys
import os
#Ici On met toutes les variables, noms de manifest...

#Functions

def InitialiseDirs():
    # Assurez-vous que le répertoire existe
    os.makedirs(os.path.dirname(MAIN_MF_OUTPUT_FILE), exist_ok=True)

def RessourcePath(relative_path):
    base_path = os.path.abspath("Ressources/")

    return os.path.join(base_path, relative_path)

def TempPath(relative_path):
    base_path = os.path.abspath("Temp/")

    return os.path.join(base_path, relative_path)

def OutputPath(relative_path):
    base_path = os.path.abspath("Output/")

    return os.path.join(base_path, relative_path)

#Bungie Url 
BASE_URL = "https://www.bungie.net"

#Folder Temp
TEMP_FOLDER = "Temp"
OUTPUT_FOLDER = "Output"

# URL de l'endpoint pour télécharger le manifeste complet
MAIN_MF_URL = "https://www.bungie.net/Platform/Destiny2/Manifest/"
MAIN_MF_OUTPUT_FILE = TempPath("local_definitions/MainManifest.json")

#Destiny Activity Namings
MF_ACTIVITY_DEFINITION = "DestinyActivityDefinition"
MF_ACTIVITY_LOST_SECTOR_EXPERT = TempPath("local_definitions/LostSector.Expert.json")
MF_ACTIVITY_LOST_SECTOR_MASTER = TempPath("local_definitions/LostSector.Master.json")
MF_ACTIVITY_FILENAME = TempPath("local_definitions/ActivityDefinition.json")
MF_ACTIVITY_FILTERED_FILENAME = TempPath("local_definitions/ActivityDefinitionFiltered.json")
MF_ACTIVITY_FILTERED_GENERAL_FILENAME = TempPath("local_definitions/ActivityDefinitionFilteredGeneral.json")

#Destination Manifest
MF_DESTINATION_DEFINITION = "DestinyDestinationDefinition"
MF_DESTINATION_FILENAME = TempPath("local_definitions/DestinationDefinition.json")
MF_DESTINATION_FILTERED_FILENAME = TempPath("local_definitions/DestinationDefinitionFiltered.json")

#Place Manifest
MF_PLACE_DEFINITION = "DestinyPlaceDefinition"
MF_PLACE_FILENAME = TempPath("local_definitions/PlaceDefinition.json")
MF_PLACE_FILTERED_FILENAME = TempPath("local_definitions/PlaceDefinitionFiltered.json")

#Inventory Item Manifest
MF_II_DEFINITION = "DestinyInventoryItemDefinition"
MF_II_FILENAME = TempPath("local_definitions/IIDefinition.json")
MF_II_FILTERED_FILENAME = TempPath("local_definitions/IIDefinitionFiltered.json")

#Inventory Item Manifest
MF_MODIFIER_DEFINITION = "DestinyActivityModifierDefinition"
MF_MODIFIER_FILENAME = TempPath("local_definitions/ModifierDefinition.json")
MF_MODIFIER_FILTERED_FILENAME = TempPath("local_definitions/ModifierDefinitionFiltered.json")

#Damage and Breaker type manifest
MF_DAMAGE_TYPE = "DestinyDamageTypeDefinition"
MF_DAMAGE_TYPE_FILENAME = TempPath("local_definitions/DamageType.json")
MF_BREAKER_TYPE = "DestinyBreakerTypeDefinition"
MF_BREAKER_TYPE_FILENAME = TempPath("local_definitions/BreakerType.json")

#GGdoc api credentials file
CREDENTIALS_GGDOC = RessourcePath("credentials.json")
TOKEN_GGDOC = RessourcePath("token.json")

#Json Database
JSON_DATABASE = TempPath("JsonDatabase/ActivitiesDatabase.json")

#Activity Types
LOSTSECTOR = "LostSector"
ALLACTIVITIES = "AllActivities"
NOACTIVITY = "NoActivity"
