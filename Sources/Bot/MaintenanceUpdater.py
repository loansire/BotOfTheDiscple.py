# Define Pacific Daylight Time timezone
import json
import os
import random
from datetime import datetime

import discord
import pytz
import requests
from bs4 import BeautifulSoup

from Sources.Bot.EmbedGenerator import create_embed_with_components

pdt_tz = pytz.timezone('America/Los_Angeles')


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
    try:
        with open("Ressources/Maintenance/maintenance_info.json", "r", encoding='utf-8') as file:
            maintenance_info = json.load(file)
        return maintenance_info
    except FileNotFoundError:
        return None


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


def translate_text_deepl(text, target_lang="FR"):
    """Traduit un texte de l'anglais vers la langue cible en utilisant l'API DeepL."""
    api_key = "63bf6b23-8b8f-41c6-8ab0-90f3c270f216:fx"  # Remplacez par votre clé API DeepL
    url = "https://api-free.deepl.com/v2/translate"

    params = {
        "auth_key": api_key,
        "text": text,
        "target_lang": target_lang
    }

    response = requests.post(url, data=params)

    if response.status_code == 200:
        return response.json()["translations"][0]["text"]
    else:
        print(f"Erreur lors de la traduction: {response.status_code}")
        return None


async def process_message(message):
    from Sources.Bot.AlertMessageBuilder import publish_alerts
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

                                # Publier les alertes de maintenance
                                await publish_alerts("maintenance")
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

                            # Publier les alertes de maintenance
                            await publish_alerts("maintenance")
                        else:
                            print("== maintenance_info.json n'existe pas ==")
                    else:
                        # Actualisez le commentaire du JSON avec le contenu du texte sauf les 3 premières et 2 dernières lignes
                        lines = description.split('\n')

                        # Filtrer les lignes pour retirer celles qui contiennent des liens
                        filtered_lines = [line for line in lines if not ("http://" in line or "https://" in line)]

                        # Vérifier s'il reste suffisamment de lignes après filtrage
                        if len(filtered_lines) > 5:
                            # Extraire les lignes du milieu (en retirant les 3 premières lignes et les 2 dernières)
                            updated_comment = '\n'.join(filtered_lines[3:-2]).strip()
                        else:
                            # Si après filtrage, il reste moins de lignes que prévu, on retire simplement les 3 premières lignes
                            updated_comment = '\n'.join(filtered_lines[3:]).strip()

                        print(f"== Commentaire à traduire: {updated_comment} ==")

                        # Traduire le commentaire en français
                        translated_comment = translate_text_deepl(updated_comment)
                        if translated_comment:
                            print(f"== Commentaire traduit: {translated_comment} ==")
                            maintenance_file = "Ressources/Maintenance/maintenance_info.json"
                            if os.path.exists(maintenance_file):
                                # Charger l'ancien contenu JSON
                                with open(maintenance_file, "r") as file:
                                    maintenance_info = json.load(file)

                                # Mettre à jour le champ 'comment'
                                maintenance_info["comment"] = translated_comment

                                # Sauvegarder le JSON mis à jour
                                with open(maintenance_file, "w") as file:
                                    json.dump(maintenance_info, file, indent=4)

                                print("== maintenance_info.json a été mis à jour ==")

                                # Publier les alertes de maintenance
                                await publish_alerts("maintenance")
                            else:
                                print("== maintenance_info.json n'existe pas ==")
                        else:
                            print("== La traduction a échoué ==")
                else:
                    print("== Ne contient pas d'info de Maintenance ==")
                    print("-------------------------")
        else:
            print("== Ne contient pas de tweet de BungieHelp ==")
            print("-------------------------")
    else:
        print("== Ce message provient d'un utilisateur, pas d'un bot ==")
        print("-------------------------")


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
            f"__**Maintenance**__ et mise à jour aujourd'hui:\n"
            f"{f'- 📝: {self.maintenance_comment}\n' if self.maintenance_comment else ''}"
            f"- :x: Stop serv <t:{self.stop_timestamp}:t> | :white_check_mark: Retour serv <t:{self.return_timestamp}:t> | :repeat: Débute __**<t:{self.stop_timestamp}:R>**__"
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
            "value": "```\n" + maintenance_comment + "\n```",
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
        description=f"## [Infos de Maintenance Destiny 2](https://x.com/BungieHelp)\n*Voici les dernières informations concernant la maintenance de Destiny 2 du <t:{stop_timestamp}:D>.*\n",
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
