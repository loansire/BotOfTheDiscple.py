import json
import os
import random
from collections import Counter
import discord
from discord import app_commands
from datetime import datetime

# Fonction pour charger les données à partir d'un fichier JSON
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Fonction pour créer une fonction d'autocomplétion
def create_autocomplete(data_list):
    async def autocomplete(interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=item, value=item)
            for item in data_list if current.lower() in item.lower()
        ][:25]  # Limiter à 25 résultats pour l'autocomplétion
    return autocomplete

# Fonction pour gérer la sélection aléatoire et la création de l'embed
async def random_pick(interaction, choices, data, title, item_type):
    # Filtrer les choix pour enlever les valeurs None
    selected_items = [choice for choice in choices if choice]

    # Si aucun item n'est sélectionné, choisir parmi tous les items disponibles
    if not selected_items:
        selected_items = list(data.keys())

    # Compter la fréquence des items sélectionnés
    item_counts = Counter(selected_items)

    # Créer une liste pondérée pour la sélection aléatoire
    weighted_items = []
    for item, count in item_counts.items():
        weighted_items.extend([item] * count)

    # Choisir aléatoirement un item dans la liste pondérée
    chosen_item = random.choice(weighted_items)

    # Créer l'embed pour le message Discord
    embed = discord.Embed(
        title=f"{title} Aléatoire Sélectionné",
        colour=0xffae00,
        timestamp=datetime.now()
    )

    # Générer la liste des items sélectionnés avec les émojis
    item_text = "\n".join(f"> {data[item]['emoji']} {item} (x{count})" for item, count in item_counts.items())
    embed.add_field(name=f"Liste des {item_type} choisis", value=item_text, inline=True)
    embed.add_field(name=f"{item_type} tiré au sort", value=chosen_item, inline=False)

    # Attacher une image si disponible
    image_path = data[chosen_item]["image"]
    if image_path and os.path.isfile(image_path):
        image_file = discord.File(image_path, filename=f"{item_type.lower()}_image.png")
        embed.set_image(url=f"attachment://{item_type.lower()}_image.png")
    else:
        embed.set_footer(text="Image non trouvée")

    # Attacher une miniature si disponible
    thumbnail_path = data[chosen_item]["thumbnail"]
    if thumbnail_path and os.path.isfile(thumbnail_path):
        thumbnail_file = discord.File(thumbnail_path, filename=f"{item_type.lower()}_thumbnail.png")
        embed.set_thumbnail(url=f"attachment://{item_type.lower()}_thumbnail.png")

    # Ajouter une icône de pied de page
    footer_icon_path = "Ressources/footer_icon.png"
    if os.path.isfile(footer_icon_path):
        footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")
        embed.set_footer(text="BotOfTheDisciple", icon_url="attachment://footer_icon.png")

    # Envoyer le message avec l'embed et les fichiers attachés
    files = [file for file in [image_file, thumbnail_file, footer_icon_file] if file]
    await interaction.response.send_message(embed=embed, files=files)

# Charger les données pour les raids et les donjons
raid_data = load_data('Ressources/RaidRandomizer/raid_data.json')
dungeon_data = load_data('Ressources/DungeonRandomizer/dungeon_data.json')

# Créer des fonctions d'autocomplétion pour les raids et les donjons
raid_autocomplete = create_autocomplete(list(raid_data.keys()))
dungeon_autocomplete = create_autocomplete(list(dungeon_data.keys()))