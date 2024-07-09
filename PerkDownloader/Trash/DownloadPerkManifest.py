import requests
import os
import json

# Fonction pour ouvrir et parcourir le fichier manifest.json
def find_destiny_inventory_item_definition(manifest_file, definition_key="DestinyInventoryItemDefinition"):
    try:
        # Ouvrir et lire le fichier manifest.json
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        # Accéder au noeud jsonWorldComponentContentPaths.fr.DestinyInventoryItemDefinition
        definition_path = manifest_data["jsonWorldComponentContentPaths"]["fr"].get(definition_key)

        if definition_path:
            print(f"Chemin trouvé pour {definition_key} : {definition_path}")
            return definition_path
        else:
            print(f"{definition_key} n'a pas été trouvé dans le manifest.")
            return None
    except Exception as e:
        print(f"Erreur lors de la lecture du manifest : {str(e)}")
        return None

# Fonction pour télécharger le fichier JSON à partir de l'URL spécifiée
def download_json(url, filename):
    try:
        # Faire la requête GET pour télécharger le fichier JSON
        response = requests.get(url)

        # Vérifier si la requête a réussi (code 200)
        if response.status_code == 200:
            # Extraire le contenu JSON de la réponse
            json_data = response.json()

            # Enregistrer le contenu JSON dans un fichier
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4)

            print("Fichier JSON téléchargé avec succès.")
        else:
            print(f"Échec de la requête pour télécharger le fichier JSON. Code d'erreur : {response.status_code}")
    except Exception as e:
        print(f"Erreur lors du téléchargement du fichier JSON : {str(e)}")

# Nom du fichier manifest
manifest_filename = "manifest.json"

# Trouver le chemin pour DestinyInventoryItemDefinition dans le manifest
definition_path = find_destiny_inventory_item_definition(manifest_filename)

if definition_path:
    # Construire l'URL complète pour télécharger le fichier JSON
    base_url = "https://www.bungie.net"
    json_url = base_url + definition_path

    # Nom du fichier de destination
    json_filename = "DestinyInventoryItemDefinition.json"

    # Utiliser la fonction pour télécharger le fichier JSON
    download_json(json_url, json_filename)
