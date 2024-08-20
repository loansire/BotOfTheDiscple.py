import os
import sys
import discord
from bs4 import BeautifulSoup
from discord import app_commands, user
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

    # Start the task to monitor messages
    #await check_messages()

    # Actualisation du Secteur oublié du jour lorsque le bot s'initialise
    GenerateActivity()

    # Démarrer la tâche de mise à jour quotidienne à 19h
    daily_update.start()

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
# Define Pacific Daylight Time timezone
pdt_tz = pytz.timezone('America/Los_Angeles')

def convert_pdt_to_unix(date_str, time_str):
    try:
        # Get the current year
        current_year = datetime.now().year

        # Format the time string
        time_str = format_time(time_str)
        # Combine the date and time strings into a single datetime string, including the current year
        datetime_str = f"{date_str} {current_year} {time_str}"
        # Parse the string into a datetime object, assuming PDT timezone
        dt_pdt = datetime.strptime(datetime_str, "%B %d %Y %I:%M %p")
        # Localize the datetime to PDT timezone
        dt_pdt = pdt_tz.localize(dt_pdt)
        # Convert the datetime to a Unix timestamp
        timestamp = int(dt_pdt.timestamp())
        return timestamp
    except Exception as e:
        print(f"Error converting PDT to Unix timestamp: {e}")
        return None

def format_time(time_str):
    """Format the time string to HH:MM AM/PM format."""
    time_str = time_str.strip()  # Remove any leading/trailing whitespace
    if not time_str:
        return time_str

    parts = time_str.split()

    if len(parts) == 1:
        # Only hour is provided (e.g., '10 AM')
        hour = parts[0]
        return f"{hour}:00"

    if len(parts) == 2:
        # Hour and AM/PM (e.g., '6:45 AM')
        hour_minute = parts[0]
        am_pm = parts[1]

        if ':' not in hour_minute:
            # No minutes specified, add ':00'
            return f"{hour_minute}:00 {am_pm}"

        return f"{hour_minute} {am_pm}"

    return time_str  # Return as-is if the format is unexpected

def clean_text(text):
    """Clean text by replacing HTML entities, removing links, and extra spaces, while preserving line breaks."""
    if text is None:
        return ""
    # Parse the text with BeautifulSoup to handle HTML entities
    soup = BeautifulSoup(text, "html.parser")
    # Remove all links
    for a in soup.findAll('a'):
        a.extract()  # Remove the entire link tag
    # Convert the HTML to plain text, but preserve line breaks
    cleaned_text = soup.get_text(separator='\n')
    # Replace multiple spaces with a single space
    cleaned_text = '\n'.join(' '.join(line.split()) for line in cleaned_text.split('\n'))
    return cleaned_text

async def process_message(message):
    # Identifiez l'auteur du message
    author = message.author
    author_name = author.name
    author_id = author.id
    author_type = "bot" if author.bot else "user"

    # Affichez les informations sur l'auteur
    print("\n*** Un Message a été intercepté ***\n--- Auteur Information ---")
    print(f"Nom: {author_name}")
    print(f"ID: {author_id}")
    print(f"Type: {author_type}")

    if message.author.bot:
        if "twitter.com/BungieHelp" in message.content:
            print("== Contient un tweet de BungieHelp ==")
            for embed in message.embeds:
                # Nettoyage et formatage du titre et de la description
                title = clean_text(embed.title) if embed.title else ""
                description = clean_text(embed.description) if embed.description else ""

                # Vérifiez si le titre ou la description commence par "UPCOMING DESTINY 2 MAINTENANCE"
                if title.startswith("UPCOMING DESTINY 2 MAINTENANCE") or description.startswith(
                        "UPCOMING DESTINY 2 MAINTENANCE"):
                    print("\n--- UPCOMING Maintenance trouvée ---")
                    content = description if description else title
                    lines = content.split('\n')

                    # Vérifiez si la ligne 3 ne contient pas "TIMELINE"
                    if "TIMELINE" in lines[3]:
                        if len(lines) >= 7:
                            # Extract comment
                            comment_line = lines[1].strip()
                            print(f"\nCommentaire: {comment_line}")

                            # Extract date, time_stop, and time_restart
                            date_line = lines[4].replace('❖ ', '').strip()  # 'August 20'
                            time_stop_line = lines[6].replace('❖ Downtime begins: ', '').strip()  # '6:45 AM'
                            time_restart_line = lines[7].replace('❖ Downtime ends: ', '').strip()  # '10 AM'

                            # Format times
                            formatted_time_stop = format_time(time_stop_line)
                            formatted_time_restart = format_time(time_restart_line)

                            print(f"Date: {date_line}")
                            print(f"Arrêt des serveurs: {formatted_time_stop}")
                            print(f"Retour des serveurs: {formatted_time_restart}")

                            # Convert times to Unix timestamps
                            stop_timestamp = convert_pdt_to_unix(date_line, formatted_time_stop)
                            return_timestamp = convert_pdt_to_unix(date_line, formatted_time_restart)

                            if stop_timestamp and return_timestamp:
                                # Save the information to a JSON file
                                maintenance_info = {
                                    "stop_timestamp": stop_timestamp,
                                    "return_timestamp": return_timestamp,
                                    "comment": comment_line
                                }
                                print(f"\nInformations à sauvegarder:")
                                print(f"{json.dumps(maintenance_info, indent=4)}")
                                os.makedirs("Ressources/Maintenance", exist_ok=True)
                                with open("Ressources/Maintenance/maintenance_info.json", "w") as file:
                                    json.dump(maintenance_info, file, indent=4)
                                print("Update des informations de maintenance effectuée")
                            else:
                                print("== Failed to convert dates and times to Unix timestamps ==")
                        else:
                            print("== Pas assez de lignes pour extraire les informations ==")
                    else:
                        print("== Ne contient pas 'TIMELINE' ==")
                    print("-------------------------")
                elif title.startswith("DESTINY 2 MAINTENANCE") or description.startswith(
                        "DESTINY 2 MAINTENANCE"):
                    print("\n--- Maintenance Update trouvée ---")
                    # Vérifiez si le texte contient "Maintenance is complete."
                    if "Maintenance is complete." in description:
                        print("== Maintenance is complete ==")

                        # Supprimez le fichier maintenance_info.json s'il existe
                        maintenance_file = "Ressources/Maintenance/maintenance_info.json"
                        if os.path.exists(maintenance_file):
                            os.remove(maintenance_file)
                            print("== maintenance_info.json a été supprimé ==")
                        else:
                            print("== maintenance_info.json n'existe pas ==")
                    else:
                        # Actualisez le commentaire du JSON avec le contenu du texte sauf les 3 premières et 2 dernières lignes
                        lines = description.split('\n')
                        if len(lines) > 5:
                            # Extraire les lignes du milieu
                            updated_comment = '\n'.join(lines[3:-2]).strip()
                            print(f"== Commentaire actualisé: {updated_comment} ==")

                            maintenance_file = "Ressources/Maintenance/maintenance_info.json"
                            if os.path.exists(maintenance_file):
                                # Charger l'ancien contenu JSON
                                with open(maintenance_file, "r") as file:
                                    maintenance_info = json.load(file)

                                # Mettre à jour le champ 'comment'
                                maintenance_info["comment"] = updated_comment

                                # Sauvegarder le JSON mis à jour
                                with open(maintenance_file, "w") as file:
                                    json.dump(maintenance_info, file, indent=4)

                                print("== maintenance_info.json a été mis à jour ==")
                            else:
                                print("== maintenance_info.json n'existe pas ==")
                        else:
                            print("== Pas assez de lignes pour actualiser le commentaire ==")
                else:
                    print("== Ne contient pas d'info de Maintenance ==")
                    print("-------------------------")
        else:
            print("== Ne contient pas de tweet de BungieHelp ==")
            print("-------------------------")
    else:
        print("== Ce message provient d'un utilisateur, pas d'un bot ==")
        print("-------------------------")

#async def check_messages():
    #channel_id = 1270308084345995345  # Remplacez par l'ID de votre canal
    #channel = bot.get_channel(channel_id)

    #if channel is None:
        #print(f"Channel with ID {channel_id} not found.")
        #return

    #async for message in channel.history(limit=4):
        #await process_message(message)

@bot.event
async def on_message(message):
     #ID du canal spécifique dans lequel vous souhaitez traiter les messages
    target_channel_id = 1270308084345995345

     #Vérifiez si le message provient du canal cible
    if message.channel.id == target_channel_id:
        await process_message(message)

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
        paris_tz = pytz.timezone('Europe/Paris')
        current_year = datetime.now().year
        current_date = datetime.today().strftime("%d/%m/%Y")

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

            embed, files, view = create_maintenance_embed_view()
            await interaction.response.send_message(embed=embed, files=files, view=view)

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

def create_maintenance_embed_view():
    maintenance_info = load_maintenance_info()
    if not maintenance_info:
        raise ValueError("Les informations de maintenance n'ont pas été trouvées.")

    stop_timestamp = maintenance_info["stop_timestamp"]
    return_timestamp = maintenance_info["return_timestamp"]
    maintenance_comment = maintenance_info.get("comment")

    embed = discord.Embed(
        description="## [Infos de Maintenance et Mise à jour](https://x.com/BungieHelp)\n*Voici les dernières informations concernant la maintenance.*",
        colour=0xff0000,
        timestamp=datetime.now()
    )

    if maintenance_comment:
        embed.add_field(
            name="📝 __Commentaire__",
            value="```\n" + maintenance_comment + "\n```",
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

    # Ajouter le bouton pour copier dans le presse-papiers
    view = MaintenanceView(stop_timestamp, return_timestamp)

    return embed, [thumbnail_file, footer_icon_file], view

class MaintenanceView(discord.ui.View):
    def __init__(self, stop_timestamp, return_timestamp):
        super().__init__()
        self.stop_timestamp = stop_timestamp
        self.return_timestamp = return_timestamp

    @discord.ui.button(label="💾 Copier les infos", style=discord.ButtonStyle.primary)
    async def copy_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        message_content = (
            f"__**Maintenance**__ et mise à jour aujourd'hui:\n"
            f"- :x: Stop serveurs <t:{self.stop_timestamp}:t>\n"
            f"- :white_check_mark: Retour serveurs <t:{self.return_timestamp}:t>\n\n"
            f":repeat: Début : __**<t:{self.stop_timestamp}:R>**__"
        )

        await interaction.response.send_message(
            f"Voici le texte formaté, prêt à être copié:\n```\n{message_content}\n```",
            ephemeral=True
        )

@bot.tree.command(name="maintenance", description="Publie un message contenant les dernières informations de maintenance")
async def maintenance(interaction: discord.Interaction):
    try:
        embed, files, view = create_maintenance_embed_view()
        await interaction.response.send_message(embed=embed, files=files, view=view)
    except ValueError:
        await interaction.response.send_message(
            "Les informations de maintenance n'ont pas été configurées. Utilisez la commande /updatemaintenance pour les configurer.",
            ephemeral=True)

@bot.tree.command(name="maintenance-update", description="Met à jour les informations de maintenance")
async def updatemaintenance(interaction: discord.Interaction):
    await interaction.response.send_modal(UpdateMaintenanceModal())

@bot.tree.command(name="maintenance-delete", description="Supprime les informations de maintenance configurées")
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

@bot.tree.command(name="ls-alert", description="Configure les alertes pour ce salon")
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

@bot.tree.command(name="ls-updade", description="Force la publication des alertes pour tous les salons configurés.")
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

@bot.tree.command(name="randomizer-raid", description="Choisir aléatoirement un raid")
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

@bot.tree.command(name="randomizer-dungeon", description="Choisir aléatoirement un donjon")
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

# region PrismaticRandomizer
# Liste des classes valides
classes_valides = ["Arcaniste", "Chasseur", "Titan"]

# Auto-complétion pour la classe
async def classe_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=classe, value=classe)
        for classe in classes_valides if current.lower() in classe.lower()
    ]

# Définir la commande /randomize-prismatic
@bot.tree.command(name="randomize-prismatic", description="Génère un setup de Prismatique aléatoire pour une classe donnée.")
@discord.app_commands.autocomplete(classe=classe_autocomplete)
async def randomize_prismatic(interaction: discord.Interaction, classe: str):
    # Vérification de la classe
    if classe not in classes_valides:
        await interaction.response.send_message("Classe invalide. Choisissez parmi Arcaniste, Chasseur ou Titan.", ephemeral=True)
        return

    # Récupérer l'utilisateur qui a exécuté la commande
    user = interaction.user

    # Créer l'embed
    embed = discord.Embed(
        description=f"## {classe} Prismatique Aléatoire\n{user.mention}, voici ton prochain build aléatoire en Doctrine prismatique !\n\n*Clic sur l'image ci-dessous pour visualiser ton roll.*",
        color=0xf500d8,
        timestamp=datetime.now()
    )

    # Chemins des images
    bg_image_path = f"Ressources/PrismaticRandomizer/{classe}_BG.png"
    thumbnail_image_path = f"Ressources/PrismaticRandomizer/{classe}_prismatique.jpg"

    # Vérification de l'existence des fichiers
    if not os.path.exists(bg_image_path):
        await interaction.response.send_message(f"Erreur: L'image de fond n'existe pas pour la classe {classe}.", ephemeral=True)
        return

    if not os.path.exists(thumbnail_image_path):
        await interaction.response.send_message(f"Erreur: Le thumbnail n'existe pas pour la classe {classe}.", ephemeral=True)
        return

    # Ajouter l'image en tant que thumbnail et l'image principale
    file = discord.File(bg_image_path, filename="bg.png")
    embed.set_image(url="attachment://bg.png")

    thumb_file = discord.File(thumbnail_image_path, filename="thumb.jpg")
    embed.set_thumbnail(url="attachment://thumb.jpg")

    # Envoyer l'embed avec les images
    await interaction.response.send_message(files=[file, thumb_file], embed=embed)
# endregion

async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')

# Démarrage de l'événement principal
asyncio.run(main())
