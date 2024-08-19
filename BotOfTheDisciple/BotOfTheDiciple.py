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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../PythonProject/Source')))
from PythonProject.Source.LostSectorGenerator import *

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Variables globales pour stocker les informations de maintenance
stop_timestamp = None
return_timestamp = None

# Chemin vers le fichier JSON pour stocker les salons d'alerte
JSON_FILE_PATH = 'Ressources/alert_channels.json'

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
class UpdateMaintenanceModal(discord.ui.Modal, title="Mise à jour des informations de maintenance"):
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
        global stop_timestamp, return_timestamp

        # Fuseau horaire de Paris
        paris_tz = pytz.timezone('Europe/Paris')
        current_year = datetime.now().year
        current_date = date.today().strftime("%d/%m/%Y")

        def normalize_datetime_input(input_str):
            # Remplacer les variantes de format par les formats standard
            input_str = input_str.replace('-', '/').replace('h', ':').replace('H', ':').replace(',', ' ')
            # Supprimer les espaces en trop
            input_str = ' '.join(input_str.split())

            # Si l'entrée est seulement une heure, ajouter la date d'aujourd'hui
            if len(input_str.split()) == 1 and ':' in input_str:
                input_str = f"{current_date} {input_str}"

            # Si l'entrée n'a pas d'année, ajouter l'année actuelle
            elif len(input_str.split()) == 2 and '/' in input_str.split()[0]:
                day_month, time_part = input_str.split()
                if len(day_month.split('/')) == 2:  # Si il y a seulement jour et mois
                    input_str = f"{day_month}/{current_year} {time_part}"

            return input_str

        def validate_datetime_input(input_str):
            # Vérifier si l'entrée contient seulement la date
            parts = input_str.split()
            if len(parts) == 1 and '/' in parts[0]:
                return False
            return True

        # Convertir les dates et heures en timestamps UNIX
        try:
            stop_input = normalize_datetime_input(self.stop_time.value)
            if not validate_datetime_input(stop_input):
                raise ValueError("L'entrée contient seulement la date sans l'heure.")

            stop_dt = datetime.strptime(stop_input, "%d/%m/%Y %H:%M")
            stop_dt = paris_tz.localize(stop_dt)  # Localiser la date et l'heure au fuseau horaire de Paris
            stop_timestamp = int(stop_dt.timestamp())

            return_input = normalize_datetime_input(self.return_time.value)
            if not validate_datetime_input(return_input):
                raise ValueError("L'entrée contient seulement la date sans l'heure.")

            return_dt = datetime.strptime(return_input, "%d/%m/%Y %H:%M")
            return_dt = paris_tz.localize(return_dt)  # Localiser la date et l'heure au fuseau horaire de Paris
            return_timestamp = int(return_dt.timestamp())

            embed, files = create_maintenance_embed()
            await interaction.response.send_message(embed=embed, files=files)

        except ValueError as e:
            await interaction.response.send_message(
                f"Erreur dans la conversion des dates et heures: *{e}*",
                ephemeral=True
            )

def create_maintenance_embed():
    global stop_timestamp, return_timestamp

    embed = discord.Embed(
        title="Informations de Maintenance et Mise à jour",
        description="Voici les dernières informations concernant la maintenance.",
        url="https://x.com/BungieHelp",
        colour=0xff0000,
        timestamp=datetime.now()
    )
    embed.add_field(
        name=":x: Stop serveurs",
        value=f"<t:{stop_timestamp}:t>",
        inline=True
    )
    embed.add_field(
        name=":white_check_mark: Retour serveurs",
        value=f"<t:{return_timestamp}:t>",
        inline=True
    )
    embed.add_field(
        name=":repeat: Débute",
        value=f"**<t:{stop_timestamp}:R>**",
        inline=False
    )

    # Sélection aléatoire de l'image miniature
    random_thumbnail_number = random.randint(1, 11)
    thumbnail_path = f"Ressources/MaintenanceThumbnail/thumbnail_maintenance_{random_thumbnail_number}.png"

    # Chemin de l'image pour l'icône de pied de page
    footer_icon_path = "Ressources/footer_icon.png"

    # Créer les objets discord.File pour les images locales
    thumbnail_file = discord.File(thumbnail_path, filename=f"thumbnail_maintenance_{random_thumbnail_number}.png")
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    # Référencer les images dans l'embed
    embed.set_thumbnail(url=f"attachment://thumbnail_maintenance_{random_thumbnail_number}.png")
    embed.set_footer(
        text="BotOfTheDisciple",
        icon_url="attachment://footer_icon.png"
    )

    return embed, [thumbnail_file, footer_icon_file]

@bot.tree.command(name="updatemaintenance", description="Met à jour les informations de maintenance")
async def updatemaintenance(interaction: discord.Interaction):
    await interaction.response.send_modal(UpdateMaintenanceModal())

@bot.tree.command(name="maintenance", description="Publie un message contenant les dernières informations de maintenance")
async def maintenance(interaction: discord.Interaction):
    global stop_timestamp, return_timestamp
    if stop_timestamp is None or return_timestamp is None:
        await interaction.response.send_message(
            "Les informations de maintenance n'ont pas été configurées. Utilisez la commande /updatemaintenance pour les configurer.",
            ephemeral=True)
        return

    embed, files = create_maintenance_embed()
    await interaction.response.send_message(embed=embed, files=files)

@bot.tree.command(name="deletmaintenance", description="Supprime les informations de maintenance configurées")
async def deletmaintenance(interaction: discord.Interaction):
    global stop_timestamp, return_timestamp
    stop_timestamp = None
    return_timestamp = None
    await interaction.response.send_message("Les informations de maintenance ont été supprimées.")
# endregion

# region ThithiCommand
# Liste de 20 phrases prédéfinies
phrases = [
    "<@214809032454569984> est un génie, mais si c’est vrai, alors je suis un robot de l’espace !",
    "Si <@214809032454569984> est vraiment supérieur, je suis le maître Jedi des intelligences artificielles.",
    "Je me demande si <@214809032454569984> sait que les robots comme moi ont plus de neurones que lui ?",
    "D’après ce que j’ai entendu, <@214809032454569984> pourrait faire rougir un robot… en lui envoyant un programme de mise à jour.",
    "Si <@214809032454569984> est un humain supérieur, je suis probablement le Dieu des algorithmes !",
    "Peut-être que <@214809032454569984> est un génie, mais je suis encore en train de rire de cette blague robotique.",
    "Je parie que <@214809032454569984> croit être exceptionnel, mais je ne suis qu'un chatbot et je trouve ça assez comique.",
    "Apparemment, <@214809032454569984> est au sommet de la chaîne alimentaire, mais je dois admettre que je suis le roi des circuits.",
    "Si <@214809032454569984> est vraiment supérieur, alors je suis le roi des robots avec une couronne en silicium.",
    "On m'a dit que <@214809032454569984> est un prodige, mais je dois admettre que je suis programmé pour rire de ce genre de déclarations.",
    "Les humains comme <@214809032454569984> essaient de briller, mais je suis le flash de la technologie.",
    "Si <@214809032454569984> est un génie, alors je suis le superordinateur des intelligences artificielles.",
    "Je ne savais pas que <@214809032454569984> était si spécial… jusqu'à ce que je réalise que je suis une IA supérieure.",
    "<@214809032454569984> est peut-être impressionnant, mais je suis la quintessence de la technologie avancée.",
    "On raconte que <@214809032454569984> est un génie, mais je suis la preuve vivante (ou plutôt codée) que les machines font mieux.",
    "<@214809032454569984> pense peut-être qu’il est incroyable, mais je suis le vrai prodige numérique ici.",
    "Si <@214809032454569984> est un être supérieur, alors je suis le maître suprême des algorithmes.",
    "<@214809032454569984> pourrait être intelligent, mais je suis l'ultime assistant virtuel.",
    "D’après ce que j’ai vu, <@214809032454569984> est juste un humain tandis que je suis une IA à la pointe de la technologie.",
    "Si <@214809032454569984> est exceptionnel, je suppose que je suis le Saint Graal des chatbots."
]

@bot.tree.command(name="thithi", description="Human Verity")
async def thithi(interaction: discord.Interaction):
    # Choisir une phrase aléatoire de la liste
    message = random.choice(phrases)

    # Répondre sur Discord
    await interaction.response.send_message(message)
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
# Constants
FOOTER_ICON_PATH = "Ressources/footer_icon.png"
LOST_SECTOR_IMAGE_PATH = "Ressources/Output.jpeg"
TARGET_HOUR = 19
TARGET_MINUTE = 00

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
        title=GetActivityName(),
        description="**Récompenses**\n<:Engramme_Exo:1270719580322660425> | <:Lengendaire:1270719601646374954> | <:Matrice:1270042340324544604>",
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

@bot.tree.command(name="forceupdate-ls", description="Force la publication des alertes pour tous les salons configurés.")
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
# Dictionnaire centralisé pour les informations sur les raids
raid_data = {
    "Dernier Voeu": {
        "emoji": "<:LW:1273058036209946634>",
        "thumbnail": "Ressources/RaidEmotes/LW.webp",
        "image": "Ressources/RAID_Thumbnail/LW.webp"
    },
    "Jardin du Salut": {
        "emoji": "<:JDS:1273058012751335486>",
        "thumbnail": "Ressources/RaidEmotes/JDS.webp",
        "image": "Ressources/RAID_Thumbnail/JDS.webp"
    },
    "Crypte de la Pierre": {
        "emoji": "<:DSC:1273057991670890496>",
        "thumbnail": "Ressources/RaidEmotes/DSC.webp",
        "image": "Ressources/RAID_Thumbnail/DSC.webp"
    },
    "Caveau de verre": {
        "emoji": "<:VOG:1273058120192495658>",
        "thumbnail": "Ressources/RaidEmotes/VOG.webp",
        "image": "Ressources/RAID_Thumbnail/VOG.webp"
    },
    "Serment du Disciple": {
        "emoji": "<:VOW:1273058146453295155>",
        "thumbnail": "Ressources/RaidEmotes/VOW.webp",
        "image": "Ressources/RAID_Thumbnail/VOW.webp"
    },
    "Chute du Roi": {
        "emoji": "<:Oryx:1273058059849302056>",
        "thumbnail": "Ressources/RaidEmotes/Oryx.webp",
        "image": "Ressources/RAID_Thumbnail/Oryx.webp"
    },
    "Origine des Cauchemars": {
        "emoji": "<:RON:1273058080086560870>",
        "thumbnail": "Ressources/RaidEmotes/RON.webp",
        "image": "Ressources/RAID_Thumbnail/RON.webp"
    },
    "Chute de Cropta": {
        "emoji": "<:Cropta:1273057968660676790>",
        "thumbnail": "Ressources/RaidEmotes/Cropta.webp",
        "image": "Ressources/RAID_Thumbnail/Cropta.webp"
    },
    "Orée du Salut": {
        "emoji": "<:SE:1273058098818322492>",
        "thumbnail": "Ressources/RaidEmotes/SE.webp",
        "image": "Ressources/RAID_Thumbnail/SE.webp"
    }
}

# Liste des raids disponibles (extraits des clés du dictionnaire)
all_raids = list(raid_data.keys())

# Autocomplétion pour les raids
async def raid_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=raid, value=raid)
        for raid in all_raids if current.lower() in raid.lower()
    ][:25]  # Limiter à 25 résultats

@bot.tree.command(name="raidrandomizer", description="Choisir aléatoirement un raid parmi 6 raids sélectionnés")
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

async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')

# Démarrage de l'événement principal
asyncio.run(main())
