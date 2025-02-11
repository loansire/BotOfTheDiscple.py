import json
from Sources.JsonDatabase import JsonDbDefines
from Sources.Utils import RequestAPI

def GetWeaponsInformations(weapon_hash):
    
    weapon_json = RequestAPI.RequestByHash(weapon_hash, "DestinyInventoryItemDefinition")['Response']

    return { JsonDbDefines.HASH : weapon_hash, JsonDbDefines.NAME : weapon_json['displayProperties']['name']
            , JsonDbDefines.WEAPON_TYPE : weapon_json['itemSubType'], JsonDbDefines.MUNITIONS_TYPE : weapon_json['equippingBlock']['ammoType']
            , JsonDbDefines.DAMAGE_TYPE : weapon_json['defaultDamageType']}