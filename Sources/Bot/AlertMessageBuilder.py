import pytz
import asyncio
from datetime import datetime, timedelta

from Sources.Bot.Common import *
from Sources.Bot.LostSectorBuilder import secteur_oublie_embed
from Sources.Bot.MaintenanceUpdater import maintenance_embed
from Sources.Bot.NewsBuilder import news_article_embed
from Sources.Utils.GgdocAPI import GetResetHour

import os
import json
import discord

ALERTS_DIR = 'Ressources/AlertDatabase'


def load_alert_channels(alert_type):
    file_path = os.path.join(ALERTS_DIR, f"{alert_type}_alert_channels.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}


def save_alert_channels(alert_type, data):
    file_path = os.path.join(ALERTS_DIR, f"{alert_type}_alert_channels.json")
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


async def publish_alerts(alert_type):
    print(f"Publication des alertes pour le type : {alert_type}")
    alert_channels = load_alert_channels(alert_type)
    any_success = False  # Variable pour vérifier si au moins une publication a réussi

    for guild_id, channels in alert_channels.items():
        guild = bot.get_guild(int(guild_id))

        if guild:
            for channel_id in channels:
                channel = guild.get_channel(int(channel_id))

                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        # Choisissez la fonction d'embed en fonction du type d'alerte
                        if alert_type == "secteur_oublie":
                            embed, files = secteur_oublie_embed()
                            view = None
                        elif alert_type == "maintenance":
                            embed, files, view = maintenance_embed()
                        elif alert_type == "twid" or alert_type == "patch_note":
                            # Utiliser la même logique pour "twid" et "patch_note"
                            keyword = 'twid' if alert_type == "twid" else 'destiny_2_update'
                            embed, view, message_content = await news_article_embed(
                                interaction=None,  # Pas d'interaction dans ce contexte
                                language='en',  # Langue par défaut, ajustez si nécessaire
                                keyword=keyword,
                                no_article_message="Aucun article trouvé pour ce type."
                            )

                            files = []  # Pas de fichiers à envoyer par défaut pour "twid" ou "patch_note"

                            if message_content:
                                await channel.send(content=message_content)

                            # Continue si aucun article n'est trouvé
                            if not embed:
                                print(f"Aucun embed trouvé pour {alert_type}.")
                                continue
                        else:
                            print(f"Type d'alerte inconnu : {alert_type}")
                            continue

                        # Envoyer le message avec ou sans vue
                        if view:
                            await channel.send(embed=embed, files=files, view=view)
                        else:
                            await channel.send(embed=embed, files=files)

                        any_success = True  # Marquer comme réussi si l'envoi est effectué

                    except discord.DiscordException as e:
                        print(f"Erreur lors de l'envoi de l'alerte dans le salon {channel_id} : {e}")

    if not any_success:
        print("Aucune alerte n'a été envoyée avec succès.\n")
    else:
        print("Au moins une alerte a été envoyée avec succès.\n")

    return any_success


target_time = GetResetHour()

async def wait_until_target():
    paris_tz = pytz.timezone('Europe/Paris')
    now = datetime.now(paris_tz)
    target_datetime = now.replace(hour=int(target_time[0]), minute=int(target_time[1]), second=int(target_time[2]), microsecond=0)

    if now > target_datetime:
        target_datetime += timedelta(days=1)

    wait_seconds = (target_datetime - now).total_seconds()
    print(f"Heure actuelle à Paris : {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Heure cible : {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Différence brute (jours, heures, minutes, secondes) : {target_datetime - now}")
    print(f"Différence en secondes : {wait_seconds:.2f} secondes")
    print(f"Différence en minutes : {(wait_seconds / 60):.2f} minutes")
    print(f"Différence en heures : {(wait_seconds / 3600):.2f} heures\n")
    await asyncio.sleep(max(wait_seconds, 0))