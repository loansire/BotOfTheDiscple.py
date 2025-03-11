import hashlib
import sqlite3
import json
import requests
import zipfile
import os
from io import BytesIO
from Sources.Bot import ApiKey

# Liste des à garder
MANIFEST_TO_USE = [
    "DestinyActivityDefinition",
    "DestinyActivityTypeDefinition",
    "DestinyActivityModifierDefinition",
    "DestinyObjectiveDefinition",
    "DestinyDestinationDefinition",
    "DestinyPlaceDefinition",
    #"DestinyInventoryItemDefinition",
    #"DestinyItemCategoryDefinition",
    "DestinyDamageTypeDefinition",
    "DestinyBreakerTypeDefinition",
    #"DestinyVendorDefinition",
    #"DestinyVendorGroupDefinition",
]

# Configuration des correspondances pour les propriétés du JSON
BreakerTypeCONFIG = {
    "displayProperties.name": "name",
    "displayProperties.description": "description",
    "displayProperties.icon": "icon"
}

ActivityCONFIG = {
    "displayProperties.name": "name",
    "displayProperties.description": "description",
    "pgcrImage": "pgcr_image",
    "activityTypeHash": "activityTypeHash",


    "originalDisplayProperties.name": "original_name",
    "originalDisplayProperties.description": "original_description",

    "destinationHash": "destination_hash",
    "placeHash": "place_hash",

    # Pour extraire la liste des rewards s'il y en a
    #"rewards": "rewards_json",
    #"modifiers": "modifiers_json"  # Optionnel si tu veux garder toute la liste en JSON
}


# Fonction pour télécharger le manifest
def download_manifest():
    manifest_url = "https://www.bungie.net/platform/Destiny2/Manifest"
    headers = {'X-API-Key': ApiKey.bungie_api}

    response = requests.get(manifest_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur lors du téléchargement du manifest: {response.status_code}")
        return None


# Fonction pour télécharger et décompresser le fichier content
def download_and_extract_content(path):
    url = f"https://www.bungie.net{path}"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
            zip_ref.extractall()
            print("Manifest extrait.")

            new_file = "Destiny2_Manifest.sqlite"
            # Supprimer le fichier existant s'il est présent
            if os.path.exists(new_file):
                os.remove(new_file)
                print(f"Ancien fichier {new_file} supprimé.")

            # Renommer le fichier extrait
            for file in os.listdir():
                if file.endswith('.content'):
                    os.rename(file, new_file)
                    print(f"Fichier renommé en: {new_file}")
                    return new_file
    else:
        print(f"Erreur lors du téléchargement de {path}: {response.status_code}")
        return None


# Fonction pour supprimer les tables qui ne sont pas dans MANIFEST_TO_USE
def delete_unwanted_tables(conn, manifest_to_use):
    cursor = conn.cursor()

    # Obtenir la liste des tables dans la base de données
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    all_tables = cursor.fetchall()

    # Identifier les tables à supprimer (celles qui ne sont pas dans MANIFEST_TO_USE)
    tables_to_delete = [table[0] for table in all_tables if table[0] not in manifest_to_use]

    # Supprimer les tables non désirées
    for table in tables_to_delete:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
            print(f"Table supprimée: {table}")
        except sqlite3.Error as e:
            print(f"Erreur lors de la suppression de la table {table}: {e}")

    # Valider les changements dans la base de données
    conn.commit()


# Fonction pour ajouter une colonne pour le 'converted_id' et mettre à jour avec la conversion
def update_id_column_with_converted_value(conn, table_name):
    cursor = conn.cursor()

    try:
        # Renommer la colonne 'id' en 'hash'
        cursor.execute(f"ALTER TABLE {table_name} RENAME COLUMN id TO hash;")
        print(f"Colonne 'id' renommée en 'hash' dans la table {table_name}.")
    except sqlite3.OperationalError as e:
        print(f"Erreur lors du renommage de la colonne dans la table {table_name}: {e}")

    try:
        # Mettre à jour les valeurs de la colonne 'hash' en appliquant la conversion des IDs négatifs
        cursor.execute(f"""
            UPDATE {table_name}
            SET hash = CASE WHEN hash < 0 THEN hash + 4294967296 ELSE hash END;
        """)
        conn.commit()
        print(f"Colonne 'hash' mise à jour avec les valeurs converties pour la table {table_name}.")
    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour de la colonne 'hash' dans la table {table_name}: {e}")


def add_columns_based_on_config(conn, table_name, config):
    cursor = conn.cursor()

    for json_key, column_name in config.items():
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT;")
            print(f"Colonne '{column_name}' ajoutée à la table '{table_name}'.")
        except sqlite3.OperationalError:
            print(f"Colonne '{column_name}' existe déjà dans la table '{table_name}'.")


def extract_value(json_data, key_path):
    """Extrait une valeur depuis un chemin de clé comme 'displayProperties.description'."""
    keys = key_path.split('.')
    for key in keys:
        if isinstance(json_data, dict):
            json_data = json_data.get(key, None)
        else:
            return None
    return json_data

def populate_columns_with_json(conn, table_name, config):
    cursor = conn.cursor()

    # Sélectionner les données JSON existantes
    cursor.execute(f"SELECT hash, json FROM {table_name};")
    rows = cursor.fetchall()

    for row in rows:
        hash_value = row[0]
        json_data = json.loads(row[1])

        # Construire les données pour chaque colonne basée sur le JSON
        update_values = {}
        for json_key, column_name in config.items():
            value = extract_value(json_data, json_key)
            update_values[column_name] = value

        # Générer la requête SQL de mise à jour
        set_clause = ", ".join([f"{column} = ?" for column in update_values.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE hash = ?;"

        # Exécuter la requête avec les valeurs extraites
        cursor.execute(sql, (*update_values.values(), hash_value))

    conn.commit()
    print(f"Données mises à jour dans la table '{table_name}'.")


# Exemple d'utilisation avec la table DestinyBreakerTypeDefinition
def process_table_with_config(conn, table_name, config):
    add_columns_based_on_config(conn, table_name, config)
    populate_columns_with_json(conn, table_name, config)


# Exemple d'utilisation
manifest_data = download_manifest()
if manifest_data:
    content_path = manifest_data['Response']['mobileWorldContentPaths']['fr']
    manifest_file = download_and_extract_content(content_path)

    # Connexion à la base de données SQLite renommée
    if manifest_file:
        conn = sqlite3.connect(manifest_file)


        # Supprimer les tables non désirées
        delete_unwanted_tables(conn, MANIFEST_TO_USE)


        # Ajouter et mettre à jour la colonne 'converted_id' pour chaque table
        for table in MANIFEST_TO_USE:
            update_id_column_with_converted_value(conn, table)

        # Appliquer le traitement pour chaque table souhaitée avec la configuration spécifique
        print(f"Test de peuplement de la table: 'DestinyActivityDefinition'")
        process_table_with_config(conn, "DestinyActivityDefinition", ActivityCONFIG)

        conn.close()
        print(f"Déconnexion de la base de données: {manifest_file}")