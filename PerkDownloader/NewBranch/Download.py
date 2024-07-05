import requests
import json
import time
import logging
import Config

# Fonction pour télécharger le manifeste complet
def download_manifest(url_to_download, output_file, max_retries=3, backoff_factor=1, must_simplify = False):
    """
    Fonction pour dl le manifeste complet de Destiny 2.

    Args:
        manifest_url (str): URL de l'endpoint pour dl le manifeste.
        output_file (str): Chemin du fichier pour enregistrer le manifeste.
        max_retries (int): Nombre maximum de tentatives en cas d'erreur serveur.
        backoff_factor (int): Facteur de backoff pour le delai entre les tentatives.
    """
    for attempt in range(max_retries):
        try:
            # Faire la requête GET pour télécharger le manifeste complet
            response = requests.get(url_to_download)

            # Vérifier si la requête a réussi (code 200)
            if response.status_code == 200:
                # Extraire le contenu JSON du 
                if output_file == Config.MAIN_MF_OUTPUT_FILE:
                    manifest_data = response.json()["Response"]
                else:
                    manifest_data = response.json()

                # Parcourir le manifeste pour simplifier le contenu
                if must_simplify:
                   simplify_manifest(manifest_data)

                # Enregistrer le manifeste simplifié dans un fichier JSON
                with open(output_file, "w") as f:
                    json.dump(manifest_data, f, indent=4)

                print("Manifest correctly downloaded")
                return

            else:
                print(f"Request for the download of the manifest Failed. Error code : {response.status_code}")
                logging.error(f"Request for the download of the manifest Failed. Error code : {response.status_code}")

                if response.status_code >= 500:
                    print(f"Attempt {attempt + 1} on {max_retries} failed. retry...")
                    time.sleep(backoff_factor * (attempt + 1))
                else:
                    break

        except requests.RequestException as e:
            error_msg = f"Error during request : {str(e)}"
            print(error_msg)
            logging.error(error_msg)

            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} on {max_retries} failed. retry...")
                time.sleep(backoff_factor * (attempt + 1))
            else:
                print("Max retries reached. Aborting.")
                break

    print("Manifest failed to download after" + max_retries + " tries")

# Fonction pour simplifier le manifeste en ne gardant que les noeuds avec la clé "fr" s'ils existent
def simplify_manifest(manifest_data):
    """
    Keep only "fr" nodes. In Place

    Args:
        manifest_data (dict): Manifest data to simplify.
    """
    # Vérifier si la clé 'fr' existe dans le dictionnaire manifest_data
    if 'fr' in manifest_data:
        # Créer un nouveau dictionnaire avec seulement la clé 'fr'
        new_manifest = {"fr": manifest_data["fr"]}
        manifest_data.clear()  # Effacer le contenu actuel du manifeste
        manifest_data.update(new_manifest)  # Mettre à jour le manifeste avec 'fr'
    else:
        # Si 'fr' n'existe pas, parcourir les autres clés et récursivement simplifier
        for key, value in list(manifest_data.items()):
            if isinstance(value, dict):
                simplify_manifest(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        simplify_manifest(item)