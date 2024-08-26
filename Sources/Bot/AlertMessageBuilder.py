import json
import os
import pytz
import asyncio
from datetime import datetime, timedelta

from Sources.Bot.Common import *
from Sources.Bot.LostSectorBuilder import secteur_oublie_embed
from Sources.Utils.GgdocAPI import GetResetHour

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


FOOTER_ICON_PATH = "Ressources/footer_icon.png"
LOST_SECTOR_IMAGE_PATH = "Output/Output.png"


async def publish_alerts(alert_type):
    alert_channels = load_alert_channels(alert_type)
    for guild_id, channels in alert_channels.items():
        guild = bot.get_guild(int(guild_id))
        if guild:
            for channel_id in channels:
                channel = guild.get_channel(int(channel_id))
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        embed = secteur_oublie_embed()
                        footer_icon_file = discord.File(FOOTER_ICON_PATH, filename="footer_icon.png")
                        lost_sector_image_file = discord.File(LOST_SECTOR_IMAGE_PATH, filename="Output.jpeg")
                        await channel.send(embed=embed, files=[footer_icon_file, lost_sector_image_file])
                    except discord.DiscordException as e:
                        print(f"Erreur lors de l'envoi de l'alerte dans le salon {channel_id} : {e}")


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
    print(f"Différence en heures : {(wait_seconds / 3600):.2f} heures")
    await asyncio.sleep(max(wait_seconds, 0))