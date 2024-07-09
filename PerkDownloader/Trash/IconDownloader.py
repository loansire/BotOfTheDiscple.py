import csv
import os
import requests
import urllib.parse


# Fonction pour nettoyer les noms de répertoires et de fichiers
def clean_name(name):
    invalid_chars = '\\/:*?"<>|'
    return ''.join([' ' if c in invalid_chars else c for c in name])


# Fonction pour télécharger les images à partir des liens contenus dans le fichier CSV
def download_images(csv_file, output_dir):
    # Créer le répertoire pour les téléchargements en cas d'erreur
    error_dir = "DownloadError"
    os.makedirs(error_dir, exist_ok=True)

    # Ouvrir le fichier CSV
    with open(csv_file, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Ignorer la première ligne (en-tête)

        # Parcourir chaque ligne du fichier CSV à partir de la deuxième ligne
        for idx, row in enumerate(reader, start=2):
            # Extraire les informations de la ligne
            icon_hash, name, item_type_display_name, icon_link = row

            # Construire l'URL de téléchargement en ajoutant le contenu de la colonne Icon à l'URL de base
            download_url = "https://www.bungie.net" + urllib.parse.quote(icon_link, safe=':/')

            # Générer le nom du fichier en remplaçant les caractères interdits par des underscores
            filename = clean_name(f"{name} - [{icon_hash}].jpg")
            directoryname = clean_name(item_type_display_name)

            # Chemin complet pour enregistrer l'image dans le répertoire correspondant à ItemTypeDisplayName
            output_dir_path = os.path.join(output_dir, directoryname)
            os.makedirs(output_dir_path, exist_ok=True)
            save_path = os.path.join(output_dir_path, filename)

            # Vérifier si le fichier existe déjà, si oui, passer à la prochaine itération
            if os.path.exists(save_path):
                print(f"Icon '{filename}' already exists. Skipping...")
                continue

            try:
                # Télécharger l'image
                response = requests.get(download_url)

                # Vérifier si la requête a réussi (code 200)
                if response.status_code == 200:
                    # Enregistrer l'image dans le répertoire de sortie
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    print(f"Image '{filename}' téléchargée avec succès.")
                else:
                    # Si la requête a échoué, déplacer le fichier dans le répertoire d'erreurs
                    error_path = os.path.join(error_dir, filename)
                    with open(error_path, "wb") as f:
                        f.write(response.content)
                    print(f"Failed to download image '{filename}'. Moved to '{error_dir}' directory.")
            except Exception as e:
                # Si une erreur se produit lors du téléchargement, déplacer le fichier dans le répertoire d'erreurs
                error_path = os.path.join(error_dir, filename)
                with open(error_path, "wb") as f:
                    f.write(b"")
                print(f"Error downloading image '{filename}': {str(e)}. Moved to '{error_dir}' directory.")

            print(f"Progress: {idx} images processed.")

# Utilisation de la fonction pour télécharger les images à partir du fichier CSV
download_images("inventory_manifest_info.csv", r"E:\Loan\Desktop\EmotesPerks")
