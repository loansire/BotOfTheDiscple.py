import json
import os
import discord
from discord import app_commands
from discord.ui import Select, View


# Fonction unique pour charger les données des vœux depuis un fichier JSON
def load_wishes_riven():
    json_path = 'Ressources/RivenWishes/wishes.json'
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['voeux']


# Fonction unique pour charger une image locale en vérifiant son existence
def load_image_riven(file_name, default_name):
    file_path = os.path.join('Ressources', 'RivenWishes', file_name)
    if os.path.isfile(file_path):
        return discord.File(file_path, filename=file_name)
    return discord.File(os.path.join('Ressources', 'RivenWishes', default_name), filename=default_name)


# Fonction unique pour créer un fichier d'image avec un chemin spécifique
def create_file_riven(path, filename):
    if os.path.isfile(path):
        return discord.File(path, filename=filename)
    return None


# Fonction unique pour créer un embed standard
def create_embed_riven(title, description, image=None, thumbnail=None, footer_icon=None):
    embed = discord.Embed(description=description, color=0x6e00f5)

    if image:
        embed.set_image(url=f"attachment://{image.filename}")

    if thumbnail:
        embed.set_thumbnail(url=f"attachment://{thumbnail.filename}")

    if footer_icon:
        embed.set_footer(text="BotOfTheDisciple", icon_url=f"attachment://{footer_icon.filename}")

    return embed


wishes = load_wishes_riven()


class WishSelect(Select):
    def __init__(self, wishes):
        options = [
            discord.SelectOption(label=wish.get('BoutonName', wish['nom'].split(' - ')[-1]), value=str(i))
            for i, wish in enumerate(wishes)
        ]
        super().__init__(placeholder="Sélectionnez un vœu...", min_values=1, max_values=1, options=options)
        self.wishes = wishes

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        wish = self.wishes[index]

        # Créer l'embed avec les informations du vœu sélectionné
        embed = create_embed_riven(
            title=wish['nom'],
            description="## " + wish['nom'] + "\n" + wish['description'],
            image=load_image_riven(wish['image'], 'Default.webp'),
            thumbnail=create_file_riven(os.path.join('Ressources', 'RivenWishes', 'Lastwish.png'), 'thumbnail.png'),
            footer_icon=create_file_riven(os.path.join('Ressources', 'footer_icon.png'), 'footer_icon.png')
        )

        # Créer les fichiers à attacher
        image_file = load_image_riven(wish['image'], 'Default.webp')
        thumbnail_file = create_file_riven(os.path.join('Ressources', 'RivenWishes', 'Lastwish.png'), 'thumbnail.png')
        footer_icon_file = create_file_riven(os.path.join('Ressources', 'footer_icon.png'), 'footer_icon.png')
        files = [file for file in [image_file, thumbnail_file, footer_icon_file] if file]

        # Modifier le message d'interaction
        await interaction.response.edit_message(embed=embed, attachments=files)
