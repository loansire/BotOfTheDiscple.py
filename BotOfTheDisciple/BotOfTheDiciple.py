import os
import sys
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, date, time as dt_time, timedelta
import random
import pytz
import asyncio
import requests
from collections import Counter
import json
from discord.ui import Button, View, Select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../PythonProject/Source')))
from PythonProject.Source.LostSectorGenerator import *

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    # Synchronisation des commandes
    await bot.tree.sync()

    # Configuration de la présence du bot
    ##activity = discord.Game(name="Tapez /help pour commencer!")
    ##await bot.change_presence(status=discord.Status.online, activity=activity)

    print(f'Bot is ready. Logged in as {bot.user}')

    # Debug pour vérifier les commandes enregistrées
    for command in bot.tree.get_commands():
        print(f'Command: {command.name}, Description: {command.description}')

    # Actualisation du Secteur oublié du jour lorsque le bot s'initialise
    #GenerateActivity()

    # Démarrer la tâche de mise à jour quotidienne à 19h
    #daily_update.start()

# Enregistrement des commandes slash
@bot.tree.command(name="help", description="Liste des commandes disponibles")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="__Listes des Commandes__",
        description="",
        colour=0x00f1f5,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url="https://cdn.icon-icons.com/icons2/272/PNG/512/Settings_30027.png")

    commands_list = ""
    for command in bot.tree.get_commands():
        commands_list += f"**/{command.name}** ```{command.description}```\n"

    embed.description = commands_list
    total_commands = len(bot.tree.get_commands())
    embed.set_footer(text=f"{total_commands} commande(s) disponibles")
    await interaction.response.send_message(embed=embed)

# region MaintenanceCommands
# Variables globales pour stocker les informations de maintenance
stop_timestamp = None
return_timestamp = None

class UpdateMaintenanceModal(discord.ui.Modal, title="Mise à jour des informations de maintenance"):
    comment = discord.ui.TextInput(
        label="Commentaire (facultatif)",
        style=discord.TextStyle.long,
        placeholder="Ajoutez un commentaire sur la maintenance...",
        required=False
    )
    stop_time = discord.ui.TextInput(
        label="Arrêt des serveurs (DD/MM/YYYY HH:MM)",
        style=discord.TextStyle.short,
        placeholder="exemple: 15:45 | 25/12 15H45 | 25/12/2024 15h45"
    )
    return_time = discord.ui.TextInput(
        label="Retour des serveurs (DD/MM/YYYY HH:MM)",
        style=discord.TextStyle.short,
        placeholder="exemple: 19:00 | 25/12 19H00 | 25/12/2024 19h00"
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Fuseau horaire de Paris
        paris_tz = pytz.timezone('Europe/Paris')
        current_year = datetime.now().year
        current_date = date.today().strftime("%d/%m/%Y")

        def normalize_datetime_input(input_str):
            input_str = input_str.replace('-', '/').replace('h', ':').replace('H', ':').replace(',', ' ')
            input_str = ' '.join(input_str.split())

            if ':' not in input_str.split()[-1]:
                input_str += ":00"
            elif input_str.endswith(':'):
                input_str += "00"

            if len(input_str.split()) == 1 and ':' in input_str:
                input_str = f"{current_date} {input_str}"

            elif len(input_str.split()) == 2 and '/' in input_str.split()[0]:
                day_month, time_part = input_str.split()
                if len(day_month.split('/')) == 2:
                    input_str = f"{day_month}/{current_year} {time_part}"

            return input_str

        def validate_datetime_input(input_str):
            parts = input_str.split()
            if len(parts) == 1 and '/' in parts[0]:
                return False
            return True

        try:
            stop_input = normalize_datetime_input(self.stop_time.value)
            if not validate_datetime_input(stop_input):
                raise ValueError("L'entrée contient seulement la date sans l'heure.")

            stop_dt = datetime.strptime(stop_input, "%d/%m/%Y %H:%M")
            stop_dt = paris_tz.localize(stop_dt)
            stop_timestamp = int(stop_dt.timestamp())

            return_input = normalize_datetime_input(self.return_time.value)
            if not validate_datetime_input(return_input):
                raise ValueError("L'entrée contient seulement la date sans l'heure.")

            return_dt = datetime.strptime(return_input, "%d/%m/%Y %H:%M")
            return_dt = paris_tz.localize(return_dt)
            return_timestamp = int(return_dt.timestamp())

            maintenance_comment = self.comment.value.strip() if self.comment.value else None

            # Sauvegarder les informations dans un fichier JSON
            self.save_maintenance_info(stop_timestamp, return_timestamp, maintenance_comment)

            embed, files = create_maintenance_embed()
            await interaction.response.send_message(embed=embed, files=files)

        except ValueError as e:
            await interaction.response.send_message(
                f"Erreur dans la conversion des dates et heures: *{e}*",
                ephemeral=True
            )

    def save_maintenance_info(self, stop_timestamp, return_timestamp, maintenance_comment):
        maintenance_info = {
            "stop_timestamp": stop_timestamp,
            "return_timestamp": return_timestamp,
            "comment": maintenance_comment
        }

        os.makedirs("Ressources", exist_ok=True)
        with open("Ressources/Maintenance/maintenance_info.json", "w") as file:
            json.dump(maintenance_info, file)

def load_maintenance_info():
    try:
        with open("Ressources/Maintenance/maintenance_info.json", "r", encoding='utf-8') as file:
            maintenance_info = json.load(file)
        return maintenance_info
    except FileNotFoundError:
        return None

def create_maintenance_embed():
    maintenance_info = load_maintenance_info()
    if not maintenance_info:
        raise ValueError("Les informations de maintenance n'ont pas été trouvées.")

    stop_timestamp = maintenance_info["stop_timestamp"]
    return_timestamp = maintenance_info["return_timestamp"]
    maintenance_comment = maintenance_info.get("comment")

    embed = discord.Embed(
        title="Informations de Maintenance et Mise à jour",
        description="*Voici les dernières informations concernant la maintenance.*",
        url="https://x.com/BungieHelp",
        colour=0xff0000,
        timestamp=datetime.now()
    )

    if maintenance_comment:
        embed.add_field(
            name="📝 __Commentaire__",
            value=maintenance_comment,
            inline=False
        )

    embed.add_field(
        name=":x: __Stop serveurs__",
        value=f"<t:{stop_timestamp}:F>",
        inline=True
    )
    embed.add_field(
        name=":white_check_mark: __Retour serveurs__",
        value=f"<t:{return_timestamp}:F>",
        inline=True
    )
    embed.add_field(
        name=":repeat: __Débute__",
        value=f"**<t:{stop_timestamp}:R>**",
        inline=False
    )

    random_thumbnail_number = random.randint(1, 11)
    thumbnail_path = f"Ressources/Maintenance/thumbnail_maintenance_{random_thumbnail_number}.png"
    footer_icon_path = "Ressources/footer_icon.png"

    thumbnail_file = discord.File(thumbnail_path, filename=f"thumbnail_maintenance_{random_thumbnail_number}.png")
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    embed.set_thumbnail(url=f"attachment://thumbnail_maintenance_{random_thumbnail_number}.png")
    embed.set_footer(
        text="BotOfTheDisciple",
        icon_url="attachment://footer_icon.png"
    )

    return embed, [thumbnail_file, footer_icon_file]

@bot.tree.command(name="maintenance", description="Publie un message contenant les dernières informations de maintenance")
async def maintenance(interaction: discord.Interaction):
    try:
        embed, files = create_maintenance_embed()
        await interaction.response.send_message(embed=embed, files=files)
    except ValueError:
        await interaction.response.send_message(
            "Les informations de maintenance n'ont pas été configurées. Utilisez la commande /updatemaintenance pour les configurer.",
            ephemeral=True)

@bot.tree.command(name="update-maintenance", description="Met à jour les informations de maintenance")
async def updatemaintenance(interaction: discord.Interaction):
    await interaction.response.send_modal(UpdateMaintenanceModal())


@bot.tree.command(name="delet-maintenance", description="Supprime les informations de maintenance configurées")
async def deletmaintenance(interaction: discord.Interaction):
    if os.path.exists("Ressources/Maintenance/maintenance_info.json"):
        os.remove("Ressources/Maintenance/maintenance_info.json")
        await interaction.response.send_message("Les informations de maintenance ont été supprimées.")
    else:
        await interaction.response.send_message("Aucune information de maintenance trouvée.", ephemeral=True)

# endregion

# region CatGifGenerator
# Giphy cat generator
GIPHY_API_KEY = "xfn2RLhVSMwCP3uQombbvz1r0muPPpDp"
GIPHY_ENDPOINT = "https://api.giphy.com/v1/gifs/search"

@bot.tree.command(name="cat", description="Envoie un GIF de chat aléatoire")
async def chatgif(interaction: discord.Interaction):
    try:
        params = {
            "api_key": GIPHY_API_KEY,
            "q": "cat",
            "limit": 20,
            "offset": random.randint(0, 50),
            "rating": "G",
            "lang": "en"
        }

        response = requests.get(GIPHY_ENDPOINT, params=params)
        data = response.json()

        if data["data"]:
            gif_url = random.choice(data["data"])["url"]
            await interaction.response.send_message(gif_url)
        else:
            await interaction.response.send_message("Je n'ai pas pu trouver de GIF de chat 😿")
    except Exception as e:
        await interaction.response.send_message("Une erreur est survenue 😿")
        print(f"Erreur lors de l'exécution de la commande /cat : {e}")
# endregion

# region LostSectorPublication
# Chemin vers le fichier JSON pour stocker les salons d'alerte
JSON_FILE_PATH = 'Ressources/alertls_channels.json'
# Constants
FOOTER_ICON_PATH = "Ressources/footer_icon.png"
LOST_SECTOR_IMAGE_PATH = "Ressources/Output.jpeg"
TARGET_HOUR = 19
TARGET_MINUTE = 00

def load_alert_channels():
    """Charger les salons d'alerte depuis le fichier JSON"""
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_alert_channels(alert_channels):
    """Sauvegarder les salons d'alerte dans le fichier JSON"""
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(alert_channels, f, indent=4)

# Mapping dictionaries
EMOJI_MAP = {
    "Cryo": "<:Cryo:1270715011781627904>",
    "Abyssale": "<:Abyssale:1270715025660711023>",
    "Solaire": "<:Solaire:1270714993553178624>",
    "Solaires": "<:Solaire:1270714993553178624>",
    "Abyssaux": "<:Abyssale:1270715025660711023>",
    "Cryo-électriques": "<:Cryo:1270715011781627904>",
    "Brise-bouclier": "<:Bloqueur:1270042102033678388>",
    "Perturbation": "<:Surcharge:1270042140944236619>",
    "Chancellement": "<:Implacable:1270042120857849877>"
}

def format_field(data, title):
    if not data:
        return ""
    lines = [title]
    for item, count in data.items():
        lines.append(f"> {EMOJI_MAP.get(item, item)} {count}")
    return "\n".join(lines)

def create_embed() -> discord.Embed:
    # Gestion des surcharges
    surcharges = [EMOJI_MAP.get(surcharge, surcharge) for surcharge in GetSurcharges()]

    # Boucliers et Champions Expert
    expert_shields = GetShields(True)
    expert_champs = GetChamps(True)

    # Boucliers et Champions Maitrise
    maitrise_shields = GetShields(False)
    maitrise_champs = GetChamps(False)

    # Création de l'embed
    embed = discord.Embed(
        description="## " + GetActivityName() + "\n**Récompenses**\n<:Engramme_Exo:1270719580322660425> | <:Lengendaire:1270719601646374954> | <:Matrice:1270042340324544604>",
        colour=0xff7300,
        timestamp=datetime.now()
    )

    embed.set_author(
        name="Secteur oublié du jour",
        icon_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png"
    )

    # Ajout des champs pour Expert et Maitrise
    expert_field_value = format_field(expert_shields, "Boucliers") + "\n" + format_field(expert_champs, "Champions")
    maitrise_field_value = format_field(maitrise_shields, "Boucliers") + "\n" + format_field(maitrise_champs, "Champions")

    if expert_field_value.strip():
        embed.add_field(name=f"Expert ({GetPower(True)})", value=expert_field_value.strip(), inline=True)

    if maitrise_field_value.strip():
        embed.add_field(name=f"Maitrise ({GetPower(False)})", value=maitrise_field_value.strip(), inline=True)

    embed.add_field(name="Surcharges", value=" | ".join(surcharges) if surcharges else "Aucune surcharge définie", inline=False)

    embed.set_image(url="attachment://Output.jpeg")
    embed.set_thumbnail(url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png")
    embed.set_footer(text="BotOfTheDisciple", icon_url="attachment://footer_icon.png")

    return embed

@bot.tree.command(name="ls", description="Obtenez les informations du Secteur Oublié du jour")
async def today_lost_sector(interaction: discord.Interaction):
    try:
        embed = create_embed()

        # Créer les objets discord.File pour les images
        footer_icon_file = discord.File(FOOTER_ICON_PATH, filename="footer_icon.png")
        lost_sector_image_file = discord.File(LOST_SECTOR_IMAGE_PATH, filename="Output.jpeg")

        # Envoyer le message avec l'embed et les fichiers d'icône et d'image
        await interaction.response.send_message(embed=embed, files=[footer_icon_file, lost_sector_image_file])

    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la génération de l'activité: {e}", ephemeral=True)
        print(f"Erreur: {e}")

async def wait_until_target():
    # Obtenir l'heure actuelle en fuseau horaire de Paris
    paris_tz = pytz.timezone('Europe/Paris')
    now = datetime.now(paris_tz)

    # Définir la date et l'heure spécifiques
    target_datetime = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)

    # Si l'heure actuelle est après l'heure cible, ajuster pour le jour suivant
    if now > target_datetime:
        target_datetime += timedelta(days=1)

    # Calculer le nombre de secondes à attendre
    wait_seconds = (target_datetime - now).total_seconds()

    # Affichage des informations pour débogage
    print(f"Heure actuelle à Paris : {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Heure cible : {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Différence brute (jours, heures, minutes, secondes) : {target_datetime - now}")
    print(f"Différence en secondes : {wait_seconds:.2f} secondes")
    print(f"Différence en minutes : {(wait_seconds / 60):.2f} minutes")
    print(f"Différence en heures : {(wait_seconds / 3600):.2f} heures")

    # Attendre jusqu'à l'heure cible
    await asyncio.sleep(max(wait_seconds, 0))

async def publish_alerts():
    """Publier les alertes dans tous les salons configurés"""
    alert_channels = load_alert_channels()
    for guild_id, channels in alert_channels.items():
        guild = bot.get_guild(int(guild_id))
        if guild:
            for channel_id in channels:
                channel = guild.get_channel(int(channel_id))
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        embed = create_embed()

                        # Créer les objets discord.File pour les images
                        footer_icon_file = discord.File(FOOTER_ICON_PATH, filename="footer_icon.png")
                        lost_sector_image_file = discord.File(LOST_SECTOR_IMAGE_PATH, filename="Output.jpeg")

                        # Envoyer le message avec l'embed et les fichiers d'icône et d'image
                        await channel.send(embed=embed, files=[footer_icon_file, lost_sector_image_file])
                    except Exception as e:
                        print(f"Erreur lors de l'envoi de l'alerte dans le salon {channel_id} : {e}")

@bot.tree.command(name="alerte-ls", description="Configure les alertes pour ce salon")
@app_commands.describe(action="Ajouter ou retirer ce salon des alertes")
@app_commands.choices(action=[
    app_commands.Choice(name="Ajouter", value="ajouter"),
    app_commands.Choice(name="Retirer", value="retirer")
])
async def alerte_ls(interaction: discord.Interaction, action: app_commands.Choice[str]):
    """Commandes pour ajouter ou retirer des salons de la liste d'alertes"""
    alert_channels = load_alert_channels()
    guild_id = str(interaction.guild.id)

    if action.value == 'ajouter':
        if guild_id not in alert_channels:
            alert_channels[guild_id] = []
        if str(interaction.channel.id) not in alert_channels[guild_id]:
            alert_channels[guild_id].append(str(interaction.channel.id))
            save_alert_channels(alert_channels)
            await interaction.response.send_message(f"Ce salon ({interaction.channel.name}) a été ajouté aux alertes.")
        else:
            await interaction.response.send_message("Ce salon est déjà configuré pour les alertes.")
    elif action.value == 'retirer':
        if guild_id in alert_channels and str(interaction.channel.id) in alert_channels[guild_id]:
            alert_channels[guild_id].remove(str(interaction.channel.id))
            if not alert_channels[guild_id]:  # Supprimer l'entrée si la liste est vide
                del alert_channels[guild_id]
            save_alert_channels(alert_channels)
            await interaction.response.send_message(f"Ce salon ({interaction.channel.name}) a été retiré des alertes.")
        else:
            await interaction.response.send_message("Ce salon n'est pas configuré pour les alertes.")
    else:
        await interaction.response.send_message("Action invalide. Utilisez 'ajouter' ou 'retirer'.")

@bot.tree.command(name="update-ls", description="Force la publication des alertes pour tous les salons configurés.")
async def force_update_ls(interaction: discord.Interaction):
    """Force la mise à jour et la publication des alertes des Secteurs Oubliés."""
    try:
        await publish_alerts()
        await interaction.response.send_message("Les alertes ont été publiées avec succès.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la publication des alertes: {e}", ephemeral=True)
        print(f"Erreur lors de la commande /forceupdate-ls: {e}")

@tasks.loop(hours=24)
async def daily_update():
    await wait_until_target()
    print("Début de la mise à jour quotidienne.")

    try:
        GenerateActivity()
        print("L'activité a été mise à jour.")
        print("Publication en cours ...")
        await publish_alerts()
        print("Alerte quotidienne publiée !")
    except Exception as e:
        print(f"Erreur lors de la mise à jour quotidienne : {e}")

    print("Fin de la mise à jour quotidienne.")
# endregion

# region RAIDRandomizer
# Charger les données des raids depuis le fichier JSON
with open('Ressources/RaidRandomizer/raid_data.json', 'r', encoding='utf-8') as f:
    raid_data = json.load(f)

# Liste des raids disponibles (extraits des clés du dictionnaire)
all_raids = list(raid_data.keys())

# Autocomplétion pour les raids
async def raid_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=raid, value=raid)
        for raid in all_raids if current.lower() in raid.lower()
    ][:25]  # Limiter à 25 résultats

@bot.tree.command(name="raid-randomizer", description="Choisir aléatoirement un raid")
@app_commands.describe(
    raid1="Premier choix de raid",
    raid2="Deuxième choix de raid",
    raid3="Troisième choix de raid",
    raid4="Quatrième choix de raid",
    raid5="Cinquième choix de raid",
    raid6="Sixième choix de raid"
)
@app_commands.autocomplete(raid1=raid_autocomplete, raid2=raid_autocomplete, raid3=raid_autocomplete,
                           raid4=raid_autocomplete, raid5=raid_autocomplete, raid6=raid_autocomplete)
async def random_raidpick(interaction: discord.Interaction, raid1: str = None, raid2: str = None, raid3: str = None,
                          raid4: str = None, raid5: str = None, raid6: str = None):
    # Créer la liste des raids sélectionnés, éliminer les None
    selected_raids = [raid for raid in [raid1, raid2, raid3, raid4, raid5, raid6] if raid]

    # Si aucun raid n'est sélectionné, choisir parmi tous les raids disponibles
    if not selected_raids:
        selected_raids = all_raids

    # Compter la fréquence des raids sélectionnés
    raid_counts = Counter(selected_raids)

    # Calculer les poids pour chaque raid basé sur leur fréquence
    weighted_raids = []
    for raid, count in raid_counts.items():
        weighted_raids.extend([raid] * count)

    # Choisir aléatoirement un raid parmi les raids pondérés
    chosen_raid = random.choice(weighted_raids)

    # Création de l'embed
    embed = discord.Embed(
        title="Raid Aléatoire Sélectionné",
        colour=0xffae00,
        timestamp=datetime.now()
    )

    # Générer la liste des raids avec les emojis
    raid_text = "\n".join(f"> {raid_data[raid]['emoji']} {raid} (x{count})" for raid, count in raid_counts.items())
    embed.add_field(name="Liste des Raids choisis", value=raid_text, inline=True)
    embed.add_field(name="Raid tiré au sort", value=chosen_raid, inline=False)

    # Ajouter les images en attachement
    raid_image_path = raid_data[chosen_raid]["image"]
    if raid_image_path and os.path.isfile(raid_image_path):
        image_path = discord.File(raid_image_path, filename="raid_image.png")
        embed.set_image(url="attachment://raid_image.png")
    else:
        embed.set_footer(text="Image non trouvée")

    # Associer la miniature
    thumbnail_path = raid_data[chosen_raid]["thumbnail"]
    if thumbnail_path and os.path.isfile(thumbnail_path):
        thumbnail_file = discord.File(thumbnail_path, filename="raid_thumbnail.png")
        embed.set_thumbnail(url="attachment://raid_thumbnail.png")

    # Ajouter le footer
    footer_icon_path = "Ressources/footer_icon.png"
    if os.path.isfile(footer_icon_path):
        footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")
        embed.set_footer(text="BotOfTheDisciple", icon_url="attachment://footer_icon.png")

    # Envoyer le message avec l'embed et les fichiers attachés
    files = [file for file in [image_path, thumbnail_file, footer_icon_file] if file]
    await interaction.response.send_message(embed=embed, files=files)
# endregion

# region DungeonRandomizer
# Charger les données des donjons depuis le fichier JSON en UTF-8
with open('Ressources/DungeonRandomizer/dungeon_data.json', 'r', encoding='utf-8') as f:
    dungeon_data = json.load(f)

# Liste des donjons disponibles (extraits des clés du dictionnaire)
all_dungeons = list(dungeon_data.keys())

# Autocomplétion pour les donjons
async def dungeon_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=dungeon, value=dungeon)
        for dungeon in all_dungeons if current.lower() in dungeon.lower()
    ][:25]  # Limiter à 25 résultats

@bot.tree.command(name="dungeon-randomizer", description="Choisir aléatoirement un donjon")
@app_commands.describe(
    donjon1="Premier choix de donjon",
    donjon2="Deuxième choix de donjon",
    donjon3="Troisième choix de donjon"
)
@app_commands.autocomplete(donjon1=dungeon_autocomplete, donjon2=dungeon_autocomplete, donjon3=dungeon_autocomplete)
async def random_dungeonpick(interaction: discord.Interaction, donjon1: str = None, donjon2: str = None, donjon3: str = None):
    # Créer la liste des donjons sélectionnés, éliminer les None
    selected_dungeons = [dungeon for dungeon in [donjon1, donjon2, donjon3] if dungeon]

    # Si aucun donjon n'est sélectionné, choisir parmi tous les donjons disponibles
    if not selected_dungeons:
        selected_dungeons = all_dungeons

    # Compter la fréquence des donjons sélectionnés
    dungeon_counts = Counter(selected_dungeons)

    # Calculer les poids pour chaque donjon basé sur leur fréquence
    weighted_dungeons = []
    for dungeon, count in dungeon_counts.items():
        weighted_dungeons.extend([dungeon] * count)

    # Choisir aléatoirement un donjon parmi les donjons pondérés
    chosen_dungeon = random.choice(weighted_dungeons)

    # Création de l'embed
    embed = discord.Embed(
        title="Donjon Aléatoire Sélectionné",
        colour=0xffae00,
        timestamp=datetime.now()
    )

    # Générer la liste des donjons avec les emojis
    dungeon_text = "\n".join(f"> {dungeon_data[dungeon]['emoji']} {dungeon} (x{count})" for dungeon, count in dungeon_counts.items())
    embed.add_field(name="Liste des Donjons choisis", value=dungeon_text, inline=True)
    embed.add_field(name="Donjon tiré au sort", value=chosen_dungeon, inline=False)

    # Ajouter les images en attachement
    dungeon_image_path = dungeon_data[chosen_dungeon]["image"]
    if dungeon_image_path and os.path.isfile(dungeon_image_path):
        image_path = discord.File(dungeon_image_path, filename="dungeon_image.png")
        embed.set_image(url="attachment://dungeon_image.png")
    else:
        embed.set_footer(text="Image non trouvée")

    # Associer la miniature
    thumbnail_path = dungeon_data[chosen_dungeon]["thumbnail"]
    if thumbnail_path and os.path.isfile(thumbnail_path):
        thumbnail_file = discord.File(thumbnail_path, filename="dungeon_thumbnail.png")
        embed.set_thumbnail(url="attachment://dungeon_thumbnail.png")

    # Ajouter le footer
    footer_icon_path = "Ressources/footer_icon.png"
    if os.path.isfile(footer_icon_path):
        footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")
        embed.set_footer(text="BotOfTheDisciple", icon_url="attachment://footer_icon.png")

    # Envoyer le message avec l'embed et les fichiers attachés
    files = [file for file in [image_path, thumbnail_file, footer_icon_file] if file]
    await interaction.response.send_message(embed=embed, files=files)
# endregion

# region RivenWishes
# Charger les données du fichier JSON
def load_wishes():
    json_path = 'Ressources/RivenWishes/wishes.json'
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['voeux']

wishes = load_wishes()

class WishSelect(Select):
    def __init__(self, wishes):
        options = [discord.SelectOption(label=wish.get('BoutonName', wish['nom'].split(' - ')[-1]), value=str(i)) for
                   i, wish in enumerate(wishes)]
        super().__init__(placeholder="Sélectionnez un vœu...", min_values=1, max_values=1, options=options)
        self.wishes = wishes

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        wish = self.wishes[index]

        embed = discord.Embed(
            description="## " + wish['nom'] + "\n" + wish['description'],
            color=0x6e00f5
        )

        # Ajouter l'image locale correspondante
        image_path = os.path.join('Ressources', 'RivenWishes', wish['image'])
        image_path = image_path if os.path.isfile(image_path) else os.path.join('Ressources', 'RivenWishes',
                                                                                'Default.webp')

        image_file = discord.File(image_path, filename='image.webp')
        embed.set_image(url='attachment://image.webp')

        # Ajouter une vignette
        thumbnail_path = os.path.join('Ressources', 'RivenWishes', 'Lastwish.png')
        thumbnail_file = discord.File(thumbnail_path, filename='thumbnail.png')
        embed.set_thumbnail(url='attachment://thumbnail.png')

        # Ajouter un pied de page
        footer_icon_path = os.path.join('Ressources', 'footer_icon.png')
        footer_icon_file = discord.File(footer_icon_path, filename='footer_icon.png')
        embed.set_footer(text="BotOfTheDisciple", icon_url='attachment://footer_icon.png')

        await interaction.response.edit_message(embed=embed, attachments=[image_file, thumbnail_file, footer_icon_file])

@bot.tree.command(name="wish-wall", description="Affiche un embed interactif avec plusieurs vœux.")
async def wishwall(interaction: discord.Interaction):
    # Chemin d'image par défaut local
    default_image_path = os.path.join('Ressources', 'RivenWishes', 'Default.webp')

    # Créer l'embed initial avec l'image par défaut
    embed = discord.Embed(
        description="## Wishwall\nSélectionnez un vœu dans le menu déroulant pour voir les détails.",
        color=0x6e00f5
    )

    # Attacher l'image locale
    default_image = discord.File(default_image_path, filename='default.webp')
    embed.set_image(url='attachment://default.webp')

    # Ajouter une vignette
    thumbnail_path = os.path.join('Ressources', 'RivenWishes', 'Lastwish.png')
    thumbnail_file = discord.File(thumbnail_path, filename='thumbnail.png')
    embed.set_thumbnail(url='attachment://thumbnail.png')

    # Ajouter un pied de page
    footer_icon_path = os.path.join('Ressources', 'footer_icon.png')
    footer_icon_file = discord.File(footer_icon_path, filename='footer_icon.png')
    embed.set_footer(text="BotOfTheDisciple", icon_url='attachment://footer_icon.png')

    # Vue avec le menu déroulant
    view = View()
    view.add_item(WishSelect(wishes))

    # Envoi du message initial avec le menu déroulant et l'image par défaut
    await interaction.response.send_message(embed=embed, view=view,
                                            files=[default_image, thumbnail_file, footer_icon_file])
# endregion

async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')

# Démarrage de l'événement principal
asyncio.run(main())
