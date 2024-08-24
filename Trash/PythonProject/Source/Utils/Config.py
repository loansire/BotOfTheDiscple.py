import sys
import os
#Ici On met toutes les variables, noms de manifest...

#Functions

def InitialiseDirs():
    # Assurez-vous que le répertoire existe
    os.makedirs(os.path.dirname(MAIN_MF_OUTPUT_FILE), exist_ok=True)

def RessourcePath(relative_path):
    try:
        # PyInstaller crée une variable temporaire dans sys._MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath("../BotOfTheDisciple/")

    return os.path.join(base_path, relative_path)

#Bungie Url 
BASE_URL = "https://www.bungie.net"


# URL de l'endpoint pour télécharger le manifeste complet
MAIN_MF_URL = "https://www.bungie.net/Platform/Destiny2/Manifest/"
MAIN_MF_OUTPUT_FILE = RessourcePath("Manifests\MainManifest.json")

#Destiny Activity Namings
MF_ACTIVITY_DEFINITION = "DestinyActivityDefinition"
MF_ACTIVITY_FILENAME = RessourcePath("Manifests\ActivityDefinition.json")
MF_ACTIVITY_FILTERED_FILENAME = RessourcePath("Manifests\ActivityDefinitionFiltered.json")
MF_ACTIVITY_FILTERED_GENERAL_FILENAME = RessourcePath("Manifests\ActivityDefinitionFilteredGeneral.json")

#Destination Manifest
MF_DESTINATION_DEFINITION = "DestinyDestinationDefinition"
MF_DESTINATION_FILENAME = RessourcePath("Manifests\DestinationDefinition.json")
MF_DESTINATION_FILTERED_FILENAME = RessourcePath("Manifests\DestinationDefinitionFiltered.json")

#Place Manifest
MF_PLACE_DEFINITION = "DestinyPlaceDefinition"
MF_PLACE_FILENAME = RessourcePath("Manifests\PlaceDefinition.json")
MF_PLACE_FILTERED_FILENAME = RessourcePath("Manifests\PlaceDefinitionFiltered.json")

#Inventory Item Manifest
MF_II_DEFINITION = "DestinyInventoryItemDefinition"
MF_II_FILENAME = RessourcePath("Manifests\IIDefinition.json")
MF_II_FILTERED_FILENAME = RessourcePath("Manifests\IIDefinitionFiltered.json")

#Inventory Item Manifest
MF_MODIFIER_DEFINITION = "DestinyActivityModifierDefinition"
MF_MODIFIER_FILENAME = RessourcePath("Manifests\ModifierDefinition.json")
MF_MODIFIER_FILTERED_FILENAME = RessourcePath("Manifests\ModifierDefinitionFiltered.json")

#Damage and Breaker type manifest
MF_DAMAGE_TYPE = "DestinyDamageTypeDefinition"
MF_DAMAGE_TYPE_FILENAME = RessourcePath("Manifests\DamageType.json")
MF_BREAKER_TYPE = "DestinyBreakerTypeDefinition"
MF_BREAKER_TYPE_FILENAME = RessourcePath("Manifests\BreakerType.json")

#GGdoc api credentials file
CREDENTIALS_GGDOC = RessourcePath(r"Ressources\credentials.json")
TOKEN_GGDOC = RessourcePath(r"Ressources\token.json")
