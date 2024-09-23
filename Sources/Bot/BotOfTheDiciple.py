import asyncio

from discord.app_commands import default_permissions
from discord.ext import tasks

from Sources.Bot.AlertMessageBuilder import load_alert_channels, save_alert_channels, wait_until_target, publish_alerts
from Sources.Bot.MaintenanceUpdater import *
from Sources.Bot.ActivityRandomizer import *
from Sources.Bot.RivenWishes import *
from Sources.Bot.NewsBuilder import news_article_embed
from Sources.Bot.LostSectorBuilder import *
from Sources.Bot.Common import *
from Sources.Bot.NewArticleNotification import NewArticleTest


from Sources.LostSector.LostSectorGenerator import *


@bot.event
async def on_ready():
    # Synchronisation des commandes
    await bot.tree.sync()

    # Configuration de la présence du bot
    # activity = discord.Game(name="Tapez /help pour commencer!")
    # await bot.change_presence(status=discord.Status.online, activity=activity)

    print(f'Bot is ready. Logged in as {bot.user}\n')

    # Debug pour vérifier les commandes enregistrées
    for command in bot.tree.get_commands():
        print(f'Command: {command.name}, Description: {command.description}')
    print(f'\n')

    # Start the task to monitor messages
    # await check_messages()

    try:
        # Actualisation du Secteur oublié du jour lorsque le bot s'initialise
        GenerateActivity()
        # Démarrer la tâche de mise à jour quotidienne à 19h si GenerateActivity() réussit
        daily_update.start()
    except Exception as e:
        print(f'Une erreur est survenue lors de l\'exécution de GenerateActivity: {e}')

    # Tester toutes les 10 minutes si de nouveaux articles sont sortis
    recurring_update.start()


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

    # Liste des commandes à exclure
    excluded_commands = {"maintenance-update", "maintenance-delete", "force-update"}

    commands_list = ""
    for command in bot.tree.get_commands():
        if command.name not in excluded_commands:
            commands_list += f"**__/{command.name}__**\n> {command.description}\n\n"

    embed.description = commands_list
    total_commands = len([cmd for cmd in bot.tree.get_commands() if cmd.name not in excluded_commands])
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


@bot.tree.command(name="maintenance-update", description="🔒 [DEVTOOL]")
@default_permissions(administrator=True)
async def updatemaintenance(interaction: discord.Interaction):
    allowed_user_id = 222465158075777035  # Remplacez par l'ID utilisateur autorisé

    if interaction.user.id != allowed_user_id:
        print(f"{interaction.user.id} is trying to use the forbidden command\n")
        await interaction.response.send_message(":thermometer_face: Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    await interaction.response.send_modal(UpdateMaintenanceModal())


@bot.tree.command(name="maintenance-delete", description="🔒 [DEVTOOL]")
@default_permissions(administrator=True)
async def deletmaintenance(interaction: discord.Interaction):
    allowed_user_id = 222465158075777035  # Remplacez par l'ID utilisateur autorisé

    if interaction.user.id != allowed_user_id:
        print(f"{interaction.user.id} is trying to use the forbidden command\n")
        await interaction.response.send_message(":thermometer_face: Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

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
        print(f"Erreur lors de l'exécution de la commande /cat : {e}\n")
# endregion


# region LostSectorPublication
@bot.tree.command(name="secteur-oublie", description="Obtenez les informations du Secteur Oublié du jour")
async def today_lost_sector(interaction: discord.Interaction):
    try:
        embed, files = secteur_oublie_embed()
        await interaction.response.send_message(embed=embed, files=files)
    except discord.DiscordException as e:
        await interaction.response.send_message(f"Erreur lors de la génération de l'activité: `{e}`", ephemeral=True)
        print(f"Erreur lors de l'exécution de la commande /secteur-oublie : {e}\n")
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

# endregion


# region News-info
@bot.tree.command(name='twid', description="Affiche la TWID la plus récente.")
@app_commands.describe(language="Langue de l'article")
@app_commands.choices(language=[
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr")
])
async def twid(interaction: discord.Interaction, language: str):
    try:
        # Appel à la fonction news_article_command pour obtenir l'embed, la vue et le message additionnel
        embed, view, message_content = await news_article_embed(
            interaction=interaction,
            language=language,
            keyword='twid',
            no_article_message="Aucun article TWID/TWAB trouvé."
        )

        if embed is None and view is None:
            # Cas où aucun article n'a été trouvé
            await interaction.response.send_message(message_content, ephemeral=True)
        else:
            # Cas où un article est trouvé
            await interaction.response.send_message(embed=embed, view=view)
            if message_content:
                # Envoie le message additionnel si nécessaire (par exemple, pour un article en français non encore publié)
                await interaction.followup.send(content=message_content, ephemeral=True)

    except discord.DiscordException as e:
        # Gestion des exceptions Discord
        await interaction.response.send_message(f"Erreur lors de la génération de l'article: `{e}`", ephemeral=True)


@bot.tree.command(name='twab', description="Affiche la TWAB la plus récente. Rien que pour Nexus o7")
@app_commands.describe(language="Langue de l'article")
@app_commands.choices(language=[
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr")
])
async def twab(interaction: discord.Interaction, language: str):
    try:
        # Appel à la fonction news_article_command pour obtenir l'embed, la vue et le message additionnel
        embed, view, message_content = await news_article_embed(
            interaction=interaction,
            language=language,
            keyword='twid',
            no_article_message="Aucun article TWID/TWAB trouvé."
        )

        if embed is None and view is None:
            # Cas où aucun article n'a été trouvé
            await interaction.response.send_message(message_content, ephemeral=True)
        else:
            # Cas où un article est trouvé
            await interaction.response.send_message(embed=embed, view=view)
            if message_content:
                # Envoie le message additionnel si nécessaire (par exemple, pour un article en français non encore publié)
                await interaction.followup.send(content=message_content, ephemeral=True)

    except discord.DiscordException as e:
        # Gestion des exceptions Discord
        await interaction.response.send_message(f"Erreur lors de la génération de l'article: `{e}`", ephemeral=True)


@bot.tree.command(name='patch-note', description="Affiche le dernier patch note Destiny 2.")
@app_commands.describe(language="Langue de l'article")
@app_commands.choices(language=[
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr")
])
async def patch_note(interaction: discord.Interaction, language: str):
    try:
        # Appel à la fonction news_article_command pour obtenir l'embed, la vue et le message additionnel
        embed, view, message_content = await news_article_embed(
            interaction=interaction,
            language=language,
            keyword='destiny_2_update',
            no_article_message="Aucun article de patch note trouvé."
        )

        if embed is None and view is None:
            # Cas où aucun article n'a été trouvé
            await interaction.response.send_message(message_content, ephemeral=True)
        else:
            # Cas où un article est trouvé
            await interaction.response.send_message(embed=embed, view=view)
            if message_content:
                # Envoie le message additionnel si nécessaire (par exemple, pour un article en français non encore publié)
                await interaction.followup.send(content=message_content, ephemeral=True)

    except discord.DiscordException as e:
        # Gestion des exceptions Discord
        await interaction.response.send_message(f"Erreur lors de la génération de l'article: `{e}`", ephemeral=True)
# endregion


# region AlertCommand
@bot.tree.command(name="alert", description="Configure des alertes de contenu du jeu.")
@app_commands.describe(alert_type="Type d'alerte (Twid, Patch Note, Maintenance, Secteur Oublié)", action="Ajouter ou retirer ce salon des alertes")
@app_commands.choices(alert_type=[
    app_commands.Choice(name="Twid", value="twid"),
    app_commands.Choice(name="Secteur Oublié", value="secteur_oublie"),
    app_commands.Choice(name="Patch Note", value="patch_note"),
    app_commands.Choice(name="Maintenance", value="maintenance")
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
                  description="🔒 [DEVTOOL]")
@app_commands.describe(alert_type="Type d'alerte")
@app_commands.choices(alert_type=[
    app_commands.Choice(name="Secteur Oublié", value="secteur_oublie"),
    app_commands.Choice(name="Twid", value="twid"),
    app_commands.Choice(name="Patch Note", value="patch_note"),
    app_commands.Choice(name="Maintenance", value="maintenance"),
    app_commands.Choice(name="Tous", value="All")
])
@default_permissions(administrator=True)
async def force_update_alert(interaction: discord.Interaction, alert_type: app_commands.Choice[str]):

    allowed_user_id = 222465158075777035

    if interaction.user.id != allowed_user_id:
        print(f"{interaction.user.id} is trying to use the forbidden command\n")
        await interaction.response.send_message(":thermometer_face: Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    try:
        if alert_type.value == "All":
            alert_types = ["secteur_oublie", "twid", "patch_note", "maintenance"]
            all_success = True

            for alert_type in alert_types:
                success = await publish_alerts(alert_type)
                if not success:
                    all_success = False

            if all_success:
                await interaction.response.send_message(":white_check_mark: Les alertes pour tous les types ont été publiées avec succès.",
                                                        ephemeral=True)
            else:
                await interaction.response.send_message(":warning: Les alertes pour certains types n'ont pas pu être publiées.",
                                                        ephemeral=True)
        else:
            success = await publish_alerts(alert_type.value)
            if success:
                await interaction.response.send_message(f":white_check_mark: Les alertes pour `{alert_type.name}` ont été publiées avec succès.",
                                                        ephemeral=True)
            else:
                await interaction.response.send_message(f":warning: Les alertes pour `{alert_type.name}` n'ont pas pu être publiées.",
                                                        ephemeral=True)

    except discord.DiscordException as e:
        await interaction.response.send_message(
            f":x: Erreur lors de la publication des alertes pour `{alert_type.name}`: `{e}`", ephemeral=True)
        print(f":x: Erreur lors de la commande /force-update pour {alert_type.name}: {e}\n")


@tasks.loop(hours=24)
async def daily_update():
    await wait_until_target()
    print("Début de la mise à jour quotidienne.")
    try:
        GenerateActivity()
        print("L'activité a été mise à jour.")
        print("Publication en cours ...")
        await publish_alerts("secteur_oublie")
        print("Alerte quotidienne publiée !")
    except Exception as e:
        print(f"Erreur lors de la mise à jour quotidienne : {e}\n")
    print("Fin de la mise à jour quotidienne.\n")
# endregion


@tasks.loop(minutes=10)
async def recurring_update():
    await NewArticleTest()

async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')


# Démarrage de l'événement principal
asyncio.run(main())
