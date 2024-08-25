from discord.app_commands import default_permissions
from discord.ext import commands, tasks
from datetime import timedelta


from Sources.Bot.MaintenanceUpdater import *
from Sources.Bot.ActivityRandomizer import *
from Sources.Bot.RivenWishes import *
from Sources.Bot.NewsBuilder import *


from Sources.LostSector.LostSectorGenerator import *


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
    # await check_messages()

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
# async def check_messages():
#     channel_id = 1270308084345995345  # Remplacez par l'ID de votre canal
#     channel = bot.get_channel(channel_id)
#
#     if channel is None:
#         print(f"Channel with ID {channel_id} not found.")
#         return
#
#     async for message in channel.history(limit=1):
#         await process_message(message)


@bot.event
async def on_message(message):
     #ID du canal spécifique dans lequel vous souhaitez traiter les messages
    target_channel_id = 1270308084345995345

     #Vérifiez si le message provient du canal cible
    if message.channel.id == target_channel_id:
        await process_message(message)

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
@default_permissions(administrator=True)
async def updatemaintenance(interaction: discord.Interaction):
    await interaction.response.send_modal(UpdateMaintenanceModal())

@bot.tree.command(name="maintenance-delete", description="Supprime les informations de maintenance configurées")
@default_permissions(administrator=True)
async def deletmaintenance(interaction: discord.Interaction):
    if os.path.exists("Ressources/Maintenance/maintenance_info.json"):
        os.remove("Ressources/Maintenance/maintenance_info.json")
        await interaction.response.send_message(":wastebasket: Les informations de maintenance ont été supprimées.")
    else:
        await interaction.response.send_message(":x: Aucune information de maintenance trouvée.", ephemeral=True)
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
JSON_FILE_PATH = 'Ressources/alert_channels.json'
# Constants
FOOTER_ICON_PATH = "Ressources/footer_icon.png"
LOST_SECTOR_IMAGE_PATH = "Output/Output.png"
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

@bot.tree.command(name="ls-alert", description="Configure les alertes pour ce salon")
@app_commands.describe(action="Ajouter ou retirer ce salon des alertes")
@app_commands.choices(action=[
    app_commands.Choice(name="Ajouter", value="ajouter"),
    app_commands.Choice(name="Retirer", value="retirer")
])
@default_permissions(administrator=True)
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
            await interaction.response.send_message(f":white_check_mark: Ce salon ({interaction.channel.name}) a été ajouté aux alertes.")
        else:
            await interaction.response.send_message(":x: Ce salon est déjà configuré pour les alertes.")
    elif action.value == 'retirer':
        if guild_id in alert_channels and str(interaction.channel.id) in alert_channels[guild_id]:
            alert_channels[guild_id].remove(str(interaction.channel.id))
            if not alert_channels[guild_id]:  # Supprimer l'entrée si la liste est vide
                del alert_channels[guild_id]
            save_alert_channels(alert_channels)
            await interaction.response.send_message(f":wastebasket: Ce salon ({interaction.channel.name}) a été retiré des alertes.")
        else:
            await interaction.response.send_message(":x: Ce salon n'est pas configuré pour les alertes.")
    else:
        await interaction.response.send_message(":x: Action invalide. Utilisez 'ajouter' ou 'retirer'.")

@bot.tree.command(name="ls-updade", description="Force la publication des alertes pour tous les salons configurés.")
@default_permissions(administrator=True)
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


# region ActivityRandomizer
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
    # Appeler la fonction générique pour traiter la commande de raid
    await random_pick(interaction, [raid1, raid2, raid3, raid4, raid5, raid6], raid_data, "Raid", "Raid")

@bot.tree.command(name="randomizer-dungeon", description="Choisir aléatoirement un donjon")
@app_commands.describe(
    donjon1="Premier choix de donjon",
    donjon2="Deuxième choix de donjon",
    donjon3="Troisième choix de donjon"
)
@app_commands.autocomplete(donjon1=dungeon_autocomplete, donjon2=dungeon_autocomplete, donjon3=dungeon_autocomplete)
async def random_dungeonpick(interaction: discord.Interaction, donjon1: str = None, donjon2: str = None, donjon3: str = None):
    # Appeler la fonction générique pour traiter la commande de donjon
    await random_pick(interaction, [donjon1, donjon2, donjon3], dungeon_data, "Donjon", "Donjon")
# endregion


# region RivenWishes
@bot.tree.command(name="wish-wall", description="Affiche un embed interactif avec plusieurs vœux.")
async def wishwall(interaction: discord.Interaction):
    # Chemin d'image par défaut local
    default_image = load_image_riven('Default.webp', 'Default.webp')
    thumbnail_file = create_file_riven(os.path.join('Ressources', 'RivenWishes', 'Lastwish.png'), 'thumbnail.png')
    footer_icon_file = create_file_riven(os.path.join('Ressources', 'footer_icon.png'), 'footer_icon.png')

    # Créer l'embed initial avec l'image par défaut
    embed = create_embed_riven(
        title="Wishwall",
        description="## Wishwall\nSélectionnez un vœu dans le menu déroulant pour voir les détails.",
        image=default_image,
        thumbnail=thumbnail_file,
        footer_icon=footer_icon_file
    )

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


# region News-info
@bot.tree.command(name='twid', description="Affiche la TWID la plus récente.")
@app_commands.describe(language="Langue de l'article")
@app_commands.choices(language=[
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr")
])
async def twid(interaction: discord.Interaction, language: str):
    await news_article_command(
        interaction=interaction,
        language=language,
        keyword='twid',
        no_article_message="Aucun article TWID/TWAB trouvé."
    )

@bot.tree.command(name='twab', description="Affiche la TWAB la plus récente. Rien que pour Nexus o7")
@app_commands.describe(language="Langue de l'article")
@app_commands.choices(language=[
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr")
])
async def twab(interaction: discord.Interaction, language: str):
    await news_article_command(
        interaction=interaction,
        language=language,
        keyword='twid',  # Utiliser le même mot-clé 'twid' pour la recherche
        no_article_message="Aucun article TWID/TWAB trouvé."
    )

@bot.tree.command(name='patch-note', description="Affiche le dernier patch note Destiny 2.")
@app_commands.describe(language="Langue de l'article")
@app_commands.choices(language=[
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr")
])
async def patch_note(interaction: discord.Interaction, language: str):
    await news_article_command(
        interaction=interaction,
        language=language,
        keyword='destiny_2_update',
        no_article_message="Aucun article de patch note trouvé."
    )
# endregion


async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')


# Démarrage de l'événement principal
asyncio.run(main())
