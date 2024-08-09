import discord
from discord.ext import commands
from datetime import datetime, date
import random
import pytz
import asyncio
import pandas as pd
import requests
import chardet
from io import StringIO

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Variables globales pour stocker les informations de maintenance
stop_timestamp = None
return_timestamp = None

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

# Enregistrement des commandes slash
@bot.tree.command(name="help", description="Liste des commandes disponibles")
async def help(interaction: discord.Interaction):
    # Création de l'embed
    embed = discord.Embed(
        title="__Listes des Commandes__",
        description="",
        colour=0x00f1f5,
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url="https://cdn.icon-icons.com/icons2/272/PNG/512/Settings_30027.png")

    # Parcours des commandes pour les ajouter dans l'embed
    commands_list = ""
    for command in bot.tree.get_commands():
        commands_list += f"**/{command.name}** ```{command.description}```\n"

    embed.description = commands_list

    # Ajouter le footer avec le nombre de commandes disponibles
    total_commands = len(bot.tree.get_commands())
    embed.set_footer(text=f"{total_commands} commande(s) disponibles")

    # Envoi de l'embed
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
    thumbnail_path = f"thumbnail_maintenance_{random_thumbnail_number}.png"

    # Chemin de l'image pour l'icône de pied de page
    footer_icon_path = "footer_icon.png"

    # Créer les objets discord.File pour les images locales
    thumbnail_file = discord.File(thumbnail_path, filename=thumbnail_path)
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    # Référencer les images dans l'embed
    embed.set_thumbnail(url=f"attachment://{thumbnail_path}")
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
# Section : Détection de l'encodage
def detect_encoding(data):
    result = chardet.detect(data)
    return result['encoding']

# Section : Lecture du Google Sheet
def read_google_sheet(sheet_id: str, page_id_current: int) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?gid={page_id_current}&format=csv"
    response = requests.get(url)
    response.raise_for_status()

    # Détection de l'encodage
    detected_encoding = detect_encoding(response.content)

    # Conversion en UTF-8
    csv_data = response.content.decode(detected_encoding).encode('utf-8').decode('utf-8')
    df = pd.read_csv(StringIO(csv_data), encoding='utf-8')
    return df

# Section : Fabrication des fields
def create_fields(df: pd.DataFrame) -> dict:
    row = df.loc[0]  # Lire la première ligne (index 0)

    # Vérification des colonnes nécessaires
    required_columns = [
        "Nom", "Surcharge1", "Surcharge2", "Power Expert", "Power Maitrise", "Expert Solaires",
        "Expert Abyssaux", "Expert Cryo-électriques", "Expert Stasiques", "Expert Filobscures",
        "Expert Brise-bouclier", "Expert Perturbation", "Expert Chancellement", "Maitrise Solaires",
        "Maitrise Abyssaux", "Maitrise Cryo-électriques", "Maitrise Stasiques", "Maitrise Filobscures",
        "Maitrise Brise-bouclier", "Maitrise Perturbation", "Maitrise Chancellement"
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Colonne manquante: {col}")

    # Parser les informations nécessaires, en ignorant les valeurs "nan"
    fields = {col: row[col] if not pd.isna(row[col]) else None for col in required_columns}
    return fields

# Section : Fabrication de l'embed
def create_embed(fields: dict) -> discord.Embed:
    # Gestion des surcharges
    surcharges = []
    if fields["Surcharge1"] == "Cryo" or fields["Surcharge2"] == "Cryo":
        surcharges.append("<:Cryo:1270715011781627904>")
    if fields["Surcharge1"] == "Abyssale" or fields["Surcharge2"] == "Abyssale":
        surcharges.append("<:Abyssale:1270715025660711023>")
    if fields["Surcharge1"] == "Solaire" or fields["Surcharge2"] == "Solaire":
        surcharges.append("<:Solaire:1270714993553178624>")

    # Construction des champs Expert et Maitrise
    expert_field_value = ""
    maitrise_field_value = ""

    if any(fields[col] for col in ["Expert Solaires", "Expert Abyssaux", "Expert Cryo-électriques"]):
        expert_field_value += "Boucliers\n"
        if fields["Expert Solaires"]:
            expert_field_value += f"> <:Solaire:1270714993553178624> {fields['Expert Solaires']}\n"
        if fields["Expert Abyssaux"]:
            expert_field_value += f"> <:Abyssale:1270715025660711023> {fields['Expert Abyssaux']}\n"
        if fields["Expert Cryo-électriques"]:
            expert_field_value += f"> <:Cryo:1270715011781627904> {fields['Expert Cryo-électriques']}\n"

    if any(fields[col] for col in ["Expert Brise-bouclier", "Expert Perturbation", "Expert Chancellement"]):
        expert_field_value += "\nChampions\n"
        if fields["Expert Brise-bouclier"]:
            expert_field_value += f"> <:Bloqueur:1270042102033678388> {fields['Expert Brise-bouclier']}\n"
        if fields["Expert Perturbation"]:
            expert_field_value += f"> <:Surcharge:1270042140944236619> {fields['Expert Perturbation']}\n"
        if fields["Expert Chancellement"]:
            expert_field_value += f"> <:Implacable:1270042120857849877> {fields['Expert Chancellement']}\n"

    if any(fields[col] for col in ["Maitrise Solaires", "Maitrise Abyssaux", "Maitrise Cryo-électriques"]):
        maitrise_field_value += "Boucliers\n"
        if fields["Maitrise Solaires"]:
            maitrise_field_value += f"> <:Solaire:1270714993553178624> {fields['Maitrise Solaires']}\n"
        if fields["Maitrise Abyssaux"]:
            maitrise_field_value += f"> <:Abyssale:1270715025660711023> {fields['Maitrise Abyssaux']}\n"
        if fields["Maitrise Cryo-électriques"]:
            maitrise_field_value += f"> <:Cryo:1270715011781627904> {fields['Maitrise Cryo-électriques']}\n"

    if any(fields[col] for col in ["Maitrise Brise-bouclier", "Maitrise Perturbation", "Maitrise Chancellement"]):
        maitrise_field_value += "\nChampions\n"
        if fields["Maitrise Brise-bouclier"]:
            maitrise_field_value += f"> <:Bloqueur:1270042102033678388> {fields['Maitrise Brise-bouclier']}\n"
        if fields["Maitrise Perturbation"]:
            maitrise_field_value += f"> <:Surcharge:1270042140944236619> {fields['Maitrise Perturbation']}\n"
        if fields["Maitrise Chancellement"]:
            maitrise_field_value += f"> <:Implacable:1270042120857849877> {fields['Maitrise Chancellement']}\n"

    # Créer un embed pour afficher les informations
    embed = discord.Embed(
        title=fields["Nom"],
        description=(
            "**Récompenses**\n"
            "<:Engramme_Exo:1270719580322660425> | <:Lengendaire:1270719601646374954> | <:Matrice:1270042340324544604>"
        ),
        colour=0xff7300,
        timestamp=datetime.now()
    )

    embed.set_author(
        name="Secteur oublié du jour",
        icon_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png"
    )

    if expert_field_value.strip():  # Ajouter uniquement si le contenu n'est pas vide
        embed.add_field(
            name=f"Expert ({fields['Power Expert']})",
            value=expert_field_value.strip(),
            inline=True
        )

    if maitrise_field_value.strip():  # Ajouter uniquement si le contenu n'est pas vide
        embed.add_field(
            name=f"Maitrise ({fields['Power Maitrise']})",
            value=maitrise_field_value.strip(),
            inline=True
        )

    embed.add_field(
        name="Surcharges",
        value=" | ".join(surcharges) if surcharges else "Aucune surcharge définie",
        inline=False
    )

    embed.set_image(
        url="https://www.bungie.net/img/destiny_content/pgcr/lotus.jpg"
    )

    embed.set_thumbnail(
        url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png"
    )

    embed.set_footer(
        text="BotOfTheDisciple",
        icon_url="attachment://footer_icon.png"
    )

    return embed

# Section : Commande principale
@bot.tree.command(name="ls", description="Obtenez les informations du Secteur Oublié du jour")
async def today_lost_sector(interaction: discord.Interaction):
    sheet_id = "1yzlUK5dlqhSg0ZGQ79o-4n9j2mRZiFgECi1CBI1Ht1I"
    page_id_current = 1205713815  # Remplacez par l'ID de votre page actuelle

    try:
        df = read_google_sheet(sheet_id, page_id_current)
        fields = create_fields(df)
        embed = create_embed(fields)

        # Chemins vers les images locales
        footer_icon_path = "footer_icon.png"

        # Créer les objets discord.File pour les images locales
        footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

        # Envoyer le message avec l'embed et le fichier d'icône
        await interaction.response.send_message(embed=embed, file=footer_icon_file)

    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la lecture des données: {e}", ephemeral=True)
        print(f"Erreur: {e}")  # Débogage : affichez l'erreur

# endregion

async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')

# Démarrage de l'événement principal
asyncio.run(main())
