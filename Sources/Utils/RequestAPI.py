import requests
import json

api_key = "95d66cb52e4d443ea72e729779de4263"
headers = {
        "X-API-Key": api_key
}

params = {
    "lc": "fr"  # Langue française
}


def RequestByName(search_term, type, iteration_max = 3):
    url = BuildURLName(search_term, type)
    
    headers = {
        "X-API-Key": api_key
    }

    params = {
        "lc": "fr"  # Langue française
    }
    
    iteration = 0
    while(iteration < iteration_max):
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        iteration += 1
        
    return None

def RequestByHash(hash, type, iteration_max = 3):
    url = BuildURLHash(hash, type)
    headers = {
        "X-API-Key": api_key
    }

    params = {
        "lc": "fr"  # Langue française
    }
    
    iteration = 0
    while(iteration < iteration_max):
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        iteration += 1
        
    return None

    

def BuildURLName(search_term, type):
    return f"https://www.bungie.net/Platform/Destiny2/Armory/Search/{type}/{search_term}/"

def BuildURLHash(hash, type):
    return f"https://www.bungie.net/Platform/Destiny2/Manifest/{type}/{hash}/"
