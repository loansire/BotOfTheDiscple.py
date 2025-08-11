# Define Pacific Daylight Time timezone
import json
import os
import random
from datetime import datetime

import discord
import pytz
import re
from bs4 import BeautifulSoup

from Sources.Bot.EmbedGenerator import create_embed_with_components

pdt_tz = pytz.timezone('America/Los_Angeles')
pst_tz = pytz.timezone('America/Los_Angeles')


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

            embed, files, view = maintenance_embed()
            await interaction.response.send_message(embed=embed, files=files, view=view)

        except ValueError as e:
            await interaction.response.send_message(
                f"Erreur dans la conversion des dates et heures: `{e}`",
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
    """Charge les informations de maintenance depuis un fichier JSON."""
    try:
        with open("Ressources/Maintenance/maintenance_info.json", "r", encoding='utf-8') as file:
            maintenance_info = json.load(file)
        return maintenance_info
    except FileNotFoundError:
        return None


def save_maintenance_info(maintenance_info):
    """Sauvegarde les informations de maintenance dans un fichier JSON."""
    os.makedirs("Ressources/Maintenance", exist_ok=True)
    with open("Ressources/Maintenance/maintenance_info.json", "w", encoding='utf-8') as file:
        json.dump(maintenance_info, file, indent=4)


def convert_pdt_to_unix(date_str, time_str):
    """Convertit une date et une heure en timestamp Unix pour le fuseau horaire PDT."""
    return convert_to_unix(date_str, time_str, "PDT")


def convert_pst_to_unix(date_str, time_str):
    """Convertit une date et une heure en timestamp Unix pour le fuseau horaire PST."""
    return convert_to_unix(date_str, time_str, "PST")


def convert_to_unix(date_str, time_str, timezone_str):
    """Convertit une date et une heure en timestamp Unix, en fonction du fuseau horaire."""
    try:
        current_year = datetime.now().year
        time_str = format_time(time_str)
        datetime_str = f"{date_str} {current_year} {time_str}"
        dt_obj = datetime.strptime(datetime_str, "%B %d %Y %I:%M %p")

        # Appliquer le fuseau horaire
        if timezone_str == "PDT":
            dt_obj = pdt_tz.localize(dt_obj)
        elif timezone_str == "PST":
            dt_obj = pst_tz.localize(dt_obj)
        else:
            raise ValueError(f"Fuseau horaire inconnu : {timezone_str}")

        return int(dt_obj.timestamp())
    except Exception as e:
        print(f"Erreur de conversion en timestamp Unix : {e}")
        return None


def format_time(time_str):
    """Formate l'heure pour qu'elle inclue les minutes, si elles manquent."""
    time_str = time_str.strip()  # Supprime les espaces inutiles
    if ':' not in time_str:  # Si les minutes sont absentes
        time_str = time_str.replace(" AM", ":00 AM").replace(" PM", ":00 PM")
    return time_str


def clean_text(text):
    """Nettoie le texte des entités HTML et des liens."""
    if text is None:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    for a in soup.findAll('a'):
        a.extract()
    return soup.get_text(separator='\n').strip()


async def process_message(message):
    from Sources.Bot.AlertMessageBuilder import publish_alerts
    """Analyse un message pour déterminer s'il contient des informations de maintenance."""
    maintenance_file = "Ressources/Maintenance/maintenance_info.json"
    maintenance_info = load_maintenance_info()

    # Identifiez l'auteur du message
    author = message.author
    author_name = author.name
    author_id = author.id
    author_type = "bot" if author.bot else "user"

    print("\n*** Un Message a été intercepté ***\n--- Auteur Information ---")
    print(f"Nom: {author_name}")
    print(f"ID: {author_id}")
    print(f"Type: {author_type}")

    # Vérifiez si le message est envoyé par un bot et contient un tweet de BungieHelp
    if author_type == "bot" and message.embeds:
        for embed in message.embeds:
            # Vérifier si l'embed contient "mastodon.social/@bungiehelp"
            embed_text = (embed.title or "") + " " + (embed.description or "")
            if "mastodon.social/@bungiehelp" in embed_text:
                print("== Contient un tweet de BungieHelp ==")

                # Nettoyage et formatage du texte de l'embed
                title = clean_text(embed.title) if embed.title else ""
                description = clean_text(embed.description) if embed.description else ""

                content = description if description else title
                content = content.replace('\u00A0', ' ').replace('\\', '')  # Remplacer les espaces insécables et les \
                content = re.sub(r'\s+', ' ', content)  # Remplacer les espaces multiples par un seul espace

                print(f"\n---")
                print(f"{content}")
                print(f"---\n")

                # Vérifiez si le tweet contient "DESTINY 2" et "MAINTENANCE"
                if "DESTINY 2" in content.upper() and "MAINTENANCE" in content.upper():
                    if not maintenance_info:
                        print("== Nouveau tweet de maintenance détecté ==")

                        comment = re.search(r"❖ Update (\d+(?:\.\d+){1,3})", content)
                        comment = comment.group(0) if comment else None

                        # Extraction de la date
                        date_match = re.search(
                            r'\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}\b',
                            content
                        )
                        date_str = date_match.group() if date_match else None

                        # Extraction des heures
                        downtime_match = re.search(r"❖ Downtime begins: ([\d]{1,2}(?::\d{2})? [APM]{2})", content)
                        uptime_match = re.search(r"❖ Downtime ends: ([\d]{1,2}(?::\d{2})? [APM]{2})", content)

                        timezone_str = "PDT" if "PDT" in content else "PST" if "PST" in content else None

                        print(f"---")
                        print(f"{date_str}")
                        print(f"{timezone_str}")
                        print(f"{downtime_match}")
                        print(f"{uptime_match}")
                        print(f"---")

                        if date_str and downtime_match and uptime_match and timezone_str:
                            downtime = downtime_match.group(1).strip()
                            uptime = uptime_match.group(1).strip()

                            # Conversion en timestamps Unix
                            stop_timestamp = convert_to_unix(date_str, downtime, timezone_str)
                            return_timestamp = convert_to_unix(date_str, uptime, timezone_str)

                            if stop_timestamp and return_timestamp:
                                # Sauvegarde des informations de maintenance
                                maintenance_info = {
                                    "stop_timestamp": stop_timestamp,
                                    "return_timestamp": return_timestamp,
                                    "comment": comment
                                }
                                print(f"\nInformations à sauvegarder:")
                                print(f"{json.dumps(maintenance_info, indent=4)}")
                                save_maintenance_info(maintenance_info)
                                print("== Informations de maintenance sauvegardées ==")
                                # Publier les alertes de maintenance
                                await publish_alerts("maintenance")
                            else:
                                print("== Erreur de conversion des dates en timestamps ==")
                        else:
                            print("== Informations insuffisantes dans le tweet ==")
                    elif maintenance_info and "Maintenance is complete" in content:
                        print("== Fin de la maintenance détectée ==")
                        # Publier les alertes de maintenance
                        await publish_alerts("maintenance_end")
                        os.remove(maintenance_file)
                        print("== Fichier de maintenance supprimé ==")
                    else:
                        print("== Des informations de maintenance existent déjà ==")
                else:
                    print("== Aucun contenu de maintenance détecté ==")
            else:
                print("== Ce message ne contient pas un tweet pertinent ==")


# Vue personnalisée pour les composants interactifs
class MaintenanceView(discord.ui.View):
    def __init__(self, stop_timestamp, return_timestamp, maintenance_comment):
        super().__init__(timeout=None)
        self.stop_timestamp = stop_timestamp
        self.return_timestamp = return_timestamp
        self.maintenance_comment = maintenance_comment

    @discord.ui.button(label="Copier les infos", style=discord.ButtonStyle.primary, emoji="💾")
    async def copy_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        message_content = (
            f"__**Maintenance**__ et mise à jour du <t:{self.stop_timestamp}:D>:\n"
            f"{f'- 📝: {self.maintenance_comment}\n' if self.maintenance_comment else ''}"
            f"- :x: Stop serv <t:{self.stop_timestamp}:t> | :white_check_mark: Retour serv <t:{self.return_timestamp}:t> | :repeat: Débute __**<t:{self.stop_timestamp}:R>**__"
            ## f"- Rotation d'activité de la semaine prochaine => https://discord.com/channels/321028061237608448/1332352251439878154\n"
            ## f"- Trop de sel ? => https://discord.com/channels/321028061237608448/999016015700688967"
        )

        await interaction.response.send_message(
            f"Voici le texte formaté, prêt à être copié:\n```\n{message_content}\n```",
            ephemeral=True
        )

# Fonction pour créer l'embed de maintenance avec vue et fichiers
def maintenance_embed():
    maintenance_info = load_maintenance_info()
    if not maintenance_info:
        raise ValueError("Les informations de maintenance n'ont pas été trouvées.")

    stop_timestamp = maintenance_info["stop_timestamp"]
    return_timestamp = maintenance_info["return_timestamp"]
    maintenance_comment = maintenance_info.get("comment")

    fields = []
    if maintenance_comment:
        fields.append({
            "name": "📝 __Commentaire(s)__",
            "value": maintenance_comment,
            "inline": False
        })

    fields.extend([
        {"name": ":x: __Stop serveurs__", "value": f"<t:{stop_timestamp}:t>", "inline": True},
        {"name": ":white_check_mark: __Retour serveurs__", "value": f"<t:{return_timestamp}:t>", "inline": True},
        {"name": ":repeat: __Débute__", "value": f"**<t:{stop_timestamp}:R>**", "inline": False}
    ])

    random_thumbnail_number = random.randint(1, 11)
    thumbnail_path = f"Ressources/Maintenance/thumbnail_maintenance_{random_thumbnail_number}.png"
    footer_icon_path = "Ressources/footer_icon.png"

    thumbnail_file = discord.File(thumbnail_path, filename=f"thumbnail_maintenance_{random_thumbnail_number}.png")
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    files = [thumbnail_file, footer_icon_file]

    # Création de l'embed avec la fonction générique
    embed, components, _ = create_embed_with_components(
        description=f"## [Infos de Maintenance Destiny 2](https://mastodon.social/@bungiehelp)\n*Voici les dernières informations concernant la maintenance de Destiny 2 du <t:{stop_timestamp}:D>.*\n",
        color=0xff0000,
        author="@BungieHelp | Généré par BotOfTheDisciple",
        author_icon_url="https://pbs.twimg.com/profile_images/1362463058132492289/vNe1WM28_400x400.jpg",
        thumbnail_url=f"attachment://thumbnail_maintenance_{random_thumbnail_number}.png",
        image_url=None,
        fields=fields,
        footer_text="BotOfTheDisciple",
        footer_icon_url="attachment://footer_icon.png",
        add_date_to_footer=True,
        buttons=None,
        files=files,
    )

    view = MaintenanceView(stop_timestamp, return_timestamp, maintenance_comment)

    return embed, files, view

def maintenance_embed_end():
    maintenance_info = load_maintenance_info()
    if not maintenance_info:
        raise ValueError("Les informations de maintenance n'ont pas été trouvées.")

    stop_timestamp = maintenance_info["stop_timestamp"]

    # Générer un numéro aléatoire pour le thumbnail
    # Liste des numéros spécifiques
    thumbnail_numbers = [1, 2, 3, 8, 11]
    # Choisir un nombre aléatoire dans cette liste
    random_thumbnail_number = random.choice(thumbnail_numbers)
    thumbnail_path = f"Ressources/Maintenance/thumbnail_maintenance_{random_thumbnail_number}.png"
    footer_icon_path = "Ressources/footer_icon.png"

    thumbnail_file = discord.File(thumbnail_path, filename=f"thumbnail_maintenance_{random_thumbnail_number}.png")
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    files = [thumbnail_file, footer_icon_file]

    # Création de l'embed sans champs ni boutons
    embed, _, _ = create_embed_with_components(
        description=f"## [Infos de Maintenance Destiny 2](https://mastodon.social/@bungiehelp)\n"
                    f":white_check_mark: La Maintenance du <t:{stop_timestamp}:D> est terminée.\n",
        color=0x00ff00,  # Une couleur verte pour signaler la fin
        author="@BungieHelp | Généré par BotOfTheDisciple",
        author_icon_url="https://pbs.twimg.com/profile_images/1362463058132492289/vNe1WM28_400x400.jpg",
        thumbnail_url=f"attachment://thumbnail_maintenance_{random_thumbnail_number}.png",
        image_url=None,
        fields=None,  # Aucun champ
        footer_text="BotOfTheDisciple",
        footer_icon_url="attachment://footer_icon.png",
        add_date_to_footer=True,  # Ajouter une date au footer
        buttons=None,  # Aucun bouton
        files=files,
    )

    return embed, files