from Sources.Utils import RequestAPI
from Sources.Utils.PrettyPrintJson import pretty_print_json

destination_data = ""

def main(place_hash):
    place_json = RequestAPI.RequestByHash(place_hash, "DestinyPlaceDefinition");

    if place_json == None:
        print("Destination hasn't be found with hash")
        return
        
    global destination_data
    destination_data = place_json['Response']
    
    
def get_place_name():
    return destination_data['displayProperties']['name']
    