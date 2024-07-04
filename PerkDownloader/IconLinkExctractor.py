import json
import csv

# Fonction pour remplacer les caractères NBSP par des espaces normaux
def replace_nbsp(text):
    return text.replace("\u00A0", " ")

# Fonction pour extraire les informations et les enregistrer dans un fichier CSV
def extract_info_to_csv(json_file, csv_file):
    # Ouvrir le fichier JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Liste pour stocker les informations à écrire dans le CSV
    info_list = []

    # Parcourir chaque entrée dans le fichier JSON
    for key, entry in data.items():
        # Vérifier si l'entrée contient la clé "displayProperties" et "icon"
        if "displayProperties" in entry and "icon" in entry["displayProperties"]:
            # Extraire les informations nécessaires et remplacer les caractères NBSP
            name = replace_nbsp(entry["displayProperties"].get("name", "NoData"))
            icon = entry["displayProperties"]["icon"]
            icon_hash = key  # Le hash principal est la clé de l'entrée
            item_type_display_name = replace_nbsp(entry.get("itemTypeDisplayName", "NoData"))

            # Vérifier si "name" ou "itemTypeDisplayName" est vide
            if not name:
                name = "NoData"
            if not item_type_display_name:
                item_type_display_name = "NoData"

            # Ajouter les informations à la liste
            info_list.append((icon_hash, name, item_type_display_name, icon))

    # Enregistrer les informations dans un fichier CSV avec encodage UTF-8
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Hash", "Name", "Item Type Display Name", "Icon"])  # Écrire l'en-tête du fichier CSV
        for info in info_list:
            writer.writerow(info)

# Utilisation de la fonction pour extraire les informations du fichier JSON et les enregistrer dans un fichier CSV
extract_info_to_csv("DestinyInventoryItemDefinition.json", "inventory_manifest_info.csv")
