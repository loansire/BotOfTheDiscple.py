from Sources.Utils import RequestAPI
from Sources.Utils.PrettyPrintJson import pretty_print_json
from Sources.Utils import Config

def get_ii_name_and_icon(ii_hash):
    ii_json = RequestAPI.RequestByHash(ii_hash, "DestinyInventoryItemDefinition");

    return ii_json['Response']['displayProperties']['name'], Config.BASE_URL + ii_json['Response']['displayProperties']['icon']