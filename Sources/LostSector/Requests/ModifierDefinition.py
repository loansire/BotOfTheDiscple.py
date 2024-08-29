from Sources.Utils import RequestAPI
from Sources.Utils import Config

def get_modifier_name_description_and_icon(modif_hash):
    modif_json = RequestAPI.RequestByHash(modif_hash, "DestinyActivityModifierDefinition");

    display_properties = modif_json['Response']['displayProperties']
    if("icon" in display_properties):
        return display_properties['name'], display_properties['description'], Config.BASE_URL + display_properties['icon']
    else:
        return display_properties['name'], display_properties['description'], ""

