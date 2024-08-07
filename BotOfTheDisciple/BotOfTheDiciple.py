import discord
from discord.ext import commands
from datetime import datetime
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

class UpdateMaintenanceModal(discord.ui.Modal, title="Mise à jour des informations de maintenance"):
    stop_time = discord.ui.TextInput(
        label="Arrêt des serveurs (DD/MM/YYYY, HH:MM)",
        style=discord.TextStyle.short,
        placeholder="Entrez la date et l'heure d'arrêt des serveurs"
    )
    return_time = discord.ui.TextInput(
        label="Retour des serveurs (DD/MM/YYYY, HH:MM)",
        style=discord.TextStyle.short,
        placeholder="Entrez la date et l'heure de retour des serveurs"
    )

    async def on_submit(self, interaction: discord.Interaction):
        global stop_timestamp, return_timestamp

        # Fuseau horaire de Paris
        paris_tz = pytz.timezone('Europe/Paris')

        # Convertir les dates et heures en timestamps UNIX
        try:
            stop_dt = datetime.strptime(self.stop_time.value, "%d/%m/%Y, %H:%M")
            stop_dt = paris_tz.localize(stop_dt)  # Localiser la date et l'heure au fuseau horaire de Paris
            stop_timestamp = int(stop_dt.timestamp())

            return_dt = datetime.strptime(self.return_time.value, "%d/%m/%Y, %H:%M")
            return_dt = paris_tz.localize(return_dt)  # Localiser la date et l'heure au fuseau horaire de Paris
            return_timestamp = int(return_dt.timestamp())

            await interaction.response.send_message(
                f"Les informations de la maintenance sont mises à jour:\nArrêt: <t:{stop_timestamp}:t>\nRetour: <t:{return_timestamp}:t>",
                ephemeral=True
            )

            # Appeler la commande /maintenance après mise à jour
            await maintenance(interaction)
        except ValueError as e:
            await interaction.response.send_message(
                f"Erreur dans la conversion des dates et heures: *{e}*",
                ephemeral=True
            )

def detect_encoding(data):
    result = chardet.detect(data)
    return result['encoding']

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
    commands_list = """
    **Liste des commandes :**
    /ls - Obtenez les informations du Secteur Oublié du jour
    /maintenance - Publie un message contenant les dernières informations de maintenances
    /updatemaintenance, Description: Met à jour les informations de maintenance
    /deletmaintenance - Supprime les informations de maintenance configurées
    /help - Affiche cette liste
    """
    await interaction.response.send_message(commands_list)

@bot.tree.command(name="updatemaintenance", description="Met à jour les informations de maintenance")
async def updatemaintenance(interaction: discord.Interaction):
    await interaction.response.send_modal(UpdateMaintenanceModal())

@bot.tree.command(name="deletmaintenance", description="Supprime les informations de maintenance configurées")
async def deletmaintenance(interaction: discord.Interaction):
    global stop_timestamp, return_timestamp
    stop_timestamp = None
    return_timestamp = None
    await interaction.response.send_message("Les informations de maintenance ont été supprimées.")

@bot.tree.command(name="thithi", description="Human Verity")
async def thithi(interaction: discord.Interaction):
    await interaction.response.send_message(
        "<@214809032454569984> n'est pas un vrai Humain, Je suis le vrai, source: tkt")

@bot.tree.command(name="maintenance", description="Publie un message contenant les dernières informations de maintenance")
async def maintenance(interaction: discord.Interaction):
    global stop_timestamp, return_timestamp
    if stop_timestamp is None or return_timestamp is None:
        await interaction.response.send_message(
            "Les informations de maintenance n'ont pas été configurées. Utilisez la commande /updatemaintenance pour les configurer.",
            ephemeral=True)
        return

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

    # Chemins vers les images locales
    thumbnail_path = "thumbnail.png"
    footer_icon_path = "footer_icon.png"

    # Créer les objets discord.File pour les images locales
    thumbnail_file = discord.File(thumbnail_path, filename="thumbnail.png")
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    # Référencer les images dans l'embed
    embed.set_thumbnail(url="attachment://thumbnail.png")
    embed.set_footer(
        text="BotOfTheDisciple",
        icon_url="attachment://footer_icon.png"
    )

    # Envoyer le message avec les fichiers joints
    await interaction.response.send_message(embed=embed, files=[thumbnail_file, footer_icon_file])

@bot.tree.command(name="ls", description="Obtenez les informations du Secteur Oublié du jour")
async def today_lost_sector(interaction: discord.Interaction):
    # Identifiants du fichier et de la page Google Sheets
    sheet_id = "1yzlUK5dlqhSg0ZGQ79o-4n9j2mRZiFgECi1CBI1Ht1I"
    page_id_current = 1205713815  # Remplacez par l'ID de votre page actuelle

    try:
        df = read_google_sheet(sheet_id, page_id_current)

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

        # Chemins vers les images locales
        footer_icon_path = "footer_icon.png"

        # Créer les objets discord.File pour les images locales
        footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

        embed.set_footer(
            text="BotOfTheDisciple",
            icon_url="attachment://footer_icon.png"
        )

        # Envoyer le message avec l'embed et le fichier d'icône
        await interaction.response.send_message(embed=embed, file=footer_icon_file)

    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la lecture des données: {e}", ephemeral=True)
        print(f"Erreur: {e}")  # Débogage : affichez l'erreur

async def main():
    async with bot:
        await bot.start('MTI3MDAyMjIyMTc4MzQ5ODg0NA.GzQ5Zl.MuQAcDfdlTAqifThbcML96gXcwdM9gmFlZ5xfI')

# Démarrage de l'événement principal
asyncio.run(main())
