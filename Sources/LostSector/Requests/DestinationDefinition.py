from Sources.Utils import RequestAPI
from Sources.Utils.PrettyPrintJson import pretty_print_json

destination_data = ""

def main(destination_hash):
    destination_json = RequestAPI.RequestByHash(destination_hash, "DestinyDestinationDefinition");

    if destination_json == None:
        print("Destination hasn't be found with hash")
        return
    
    
    global destination_data
    destination_data = destination_json['Response']
    
    
def get_destination_name_and_description():
    return destination_data['displayProperties']['name'], destination_data['displayProperties']['description']
    