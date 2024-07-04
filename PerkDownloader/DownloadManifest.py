import requests
import os
import json
import time
import logging

# Configuration de la journalisation
logging.basicConfig(filename='manifest_download.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Fonction pour télécharger le manifeste complet
def download_manifest(manifest_url, output_file, max_retries=3, backoff_factor=1):
    """
    Fonction pour télécharger le manifeste complet de Destiny 2.

    Args:
        manifest_url (str): URL de l'endpoint pour télécharger le manifeste.
        output_file (str): Chemin du fichier pour enregistrer le manifeste.
        max_retries (int): Nombre maximum de tentatives en cas d'erreur serveur.
        backoff_factor (int): Facteur de backoff pour le délai entre les tentatives.
    """
    for attempt in range(max_retries):
        try:
            # Faire la requête GET pour télécharger le manifeste complet
            response = requests.get(manifest_url)

            # Vérifier si la requête a réussi (code 200)
            if response.status_code == 200:
                # Extraire le contenu JSON du manifeste
                manifest_data = response.json()["Response"]

                # Parcourir le manifeste pour simplifier le contenu
                simplify_manifest(manifest_data)

                # Enregistrer le manifeste simplifié dans un fichier JSON
                with open(output_file, "w") as f:
                    json.dump(manifest_data, f, indent=4)

                print("Manifeste téléchargé avec succès.")
                return

            else:
                print(f"Échec de la requête pour télécharger le manifeste. Code d'erreur : {response.status_code}")
                logging.error(f"Échec de la requête pour télécharger le manifeste. Code d'erreur : {response.status_code}")

                if response.status_code >= 500:
                    print(f"Tentative {attempt + 1} de {max_retries} échouée. Réessayer...")
                    time.sleep(backoff_factor * (attempt + 1))
                else:
                    break

        except requests.RequestException as e:
            error_msg = f"Erreur lors de la requête : {str(e)}"
            print(error_msg)
            logging.error(error_msg)

            if attempt < max_retries - 1:
                print(f"Tentative {attempt + 1} de {max_retries} échouée. Réessayer...")
                time.sleep(backoff_factor * (attempt + 1))
            else:
                print("Max retries reached. Aborting.")
                break

    print("Échec du téléchargement du manifeste après plusieurs tentatives.")

# Fonction pour simplifier le manifeste en ne gardant que les noeuds avec la clé "fr" s'ils existent
def simplify_manifest(manifest_data):
    """
    Simplifie le manifeste en ne gardant que les noeuds avec la clé "fr" s'ils existent.
    Modifie le manifeste directement.

    Args:
        manifest_data (dict): Données du manifeste à simplifier.
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


# URL de l'endpoint pour télécharger le manifeste complet
manifest_url = "https://www.bungie.net/Platform/Destiny2/Manifest/"

# Chemin du fichier pour enregistrer le manifeste
output_file = "manifest.json"

# Utiliser la fonction pour télécharger le manifeste complet
download_manifest(manifest_url, output_file)
