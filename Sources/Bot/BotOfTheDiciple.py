from discord.app_commands import default_permissions
from discord.ext import tasks

from Sources.Bot.AlertMessageBuilder import load_alert_channels, save_alert_channels, publish_alerts, wait_until_target
from Sources.Bot.MaintenanceUpdater import *
from Sources.Bot.ActivityRandomizer import *
from Sources.Bot.RivenWishes import *
from Sources.Bot.NewsBuilder import *
from Sources.Bot.LostSectorBuilder import *
from Sources.Bot.Common import *


from Sources.LostSector.LostSectorGenerator import *


@bot.event
async def on_ready():
    # Synchronisation des commandes
    await bot.tree.sync()

    # Configuration de la présence du bot
    #activity = discord.Game(name="Tapez /help pour commencer!")
    #await bot.change_presence(status=discord.Status.online, activity=activity)

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
        embed, files, view = maintenance_embed()
        await interaction.response.send_message(embed=embed, files=files, view=view)
    except ValueError:
        await interaction.response.send_message(":x: Il n'y a pas de maintenance de Destiny 2 prévue pour le moment.")
    except discord.DiscordException as e:
        await interaction.response.send_message(f"Erreur lors de la génération de l'activité: `{e}`", ephemeral=True)


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
            await interaction.response.send_message("Je n'ai pas pu trouver de GIF de chat 😿", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("Une erreur est survenue: `{e}` 😿", ephemeral=True)
        print(f"Erreur lors de l'exécution de la commande /cat : {e}")
# endregion


# region LostSectorPublication
@bot.tree.command(name="lost-sector", description="Obtenez les informations du Secteur Oublié du jour")
async def today_lost_sector(interaction: discord.Interaction):
    try:
        embed, files = secteur_oublie_embed()
        await interaction.response.send_message(embed=embed, files=files)
    except discord.DiscordException as e:
        await interaction.response.send_message(f"Erreur lors de la génération de l'activité: `{e}`", ephemeral=True)
        print(f"Erreur: {e}")
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


# region AlertCommand
@bot.tree.command(name="alert", description="Configure des alertes de contenu du jeu.")
@app_commands.describe(alert_type="Type d'alerte (Twid, Patch Note, Maintenance, Secteur Oublié)", action="Ajouter ou retirer ce salon des alertes")
@app_commands.choices(alert_type=[
    app_commands.Choice(name="Twid", value="Twid"),
    app_commands.Choice(name="Secteur Oublié", value="Secteur_Oublie"),
    app_commands.Choice(name="Patch Note", value="Patch_Note"),
    app_commands.Choice(name="Maintenance", value="Maintenance")
])
@app_commands.choices(action=[
    app_commands.Choice(name="Ajouter", value="ajouter"),
    app_commands.Choice(name="Retirer", value="retirer")
])
@default_permissions(administrator=True)
async def alert(interaction: discord.Interaction, alert_type: app_commands.Choice[str], action: app_commands.Choice[str]):
    alert_channels = load_alert_channels(alert_type.value)
    guild_id = str(interaction.guild.id)

    if action.value == 'ajouter':
        if guild_id not in alert_channels:
            alert_channels[guild_id] = []
        if str(interaction.channel.id) not in alert_channels[guild_id]:
            alert_channels[guild_id].append(str(interaction.channel.id))
            save_alert_channels(alert_type.value, alert_channels)
            await interaction.response.send_message(f":white_check_mark: <#{interaction.channel.id}> a été ajouté aux alertes de `{alert_type.name}`.")
        else:
            await interaction.response.send_message(f":x: <#{interaction.channel.id}> est déjà configuré pour les alertes.", ephemeral=True)
    elif action.value == 'retirer':
        if guild_id in alert_channels and str(interaction.channel.id) in alert_channels[guild_id]:
            alert_channels[guild_id].remove(str(interaction.channel.id))
            if not alert_channels[guild_id]:
                del alert_channels[guild_id]
            save_alert_channels(alert_type.value, alert_channels)
            await interaction.response.send_message(f":wastebasket: <#{interaction.channel.id}> a été retiré des alertes de `{alert_type.name}`.")
        else:
            await interaction.response.send_message(f":x: <#{interaction.channel.id}> n'est pas configuré pour les alertes `{alert_type.name}`.", ephemeral=True)
    else:
        await interaction.response.send_message(":x: Action invalide. Utilisez 'ajouter' ou 'retirer'.", ephemeral=True)


@bot.tree.command(name="force-update",
                  description="Force la publication des alertes pour un type donné ou tous les types.")
@app_commands.describe(alert_type="Type d'alerte")
@app_commands.choices(alert_type=[
    app_commands.Choice(name="Secteur Oublié", value="Secteur_Oublie"),
    app_commands.Choice(name="Twid", value="Twid"),
    app_commands.Choice(name="Patch Note", value="Patch_Note"),
    app_commands.Choice(name="Maintenance", value="Maintenance"),
    app_commands.Choice(name="Tous", value="All")
])
@default_permissions(administrator=True)
async def force_update_alert(interaction: discord.Interaction, alert_type: app_commands.Choice[str]):

    allowed_user_id = 222465158075777035

    if interaction.user.id != allowed_user_id:
        print(f"{interaction.user.id} is trying to use the forbidden command")
        await interaction.response.send_message(":thermometer_face: Vous n'avez pas la permission d'utiliser cette commande.",
                                                ephemeral=True)
        return

    try:
        if alert_type.value == "All":
            alert_types = ["Secteur_Oublie", "Twid", "Patch_Note", "Maintenance"]
            for alert_type in alert_types:
                await publish_alerts(alert_type)
            await interaction.response.send_message(":white_check_mark: Les alertes pour tous les types ont été publiées avec succès.",
                                                    ephemeral=True)
        else:
            await publish_alerts(alert_type.value)
            await interaction.response.send_message(f":white_check_mark: Les alertes pour `{alert_type.name}` ont été publiées avec succès.",
                                                    ephemeral=True)
    except discord.DiscordException as e:
        await interaction.response.send_message(
            f":x: Erreur lors de la publication des alertes pour `{alert_type.name}`: `{e}`", ephemeral=True)
        print(f":x: Erreur lors de la commande /force-update pour {alert_type.name}: {e}")


@tasks.loop(hours=24)
async def daily_update():
    await wait_until_target()
    print("Début de la mise à jour quotidienne.")
    try:
        GenerateActivity()
        print("L'activité a été mise à jour.")
        print("Publication en cours ...")
        await publish_alerts("Secteur_Oublie")
        print("Alerte quotidienne publiée !")
    except Exception as e:
        print(f"Erreur lors de la mise à jour quotidienne : {e}")
    print("Fin de la mise à jour quotidienne.")
# endregion


async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')


# Démarrage de l'événement principal
asyncio.run(main())
