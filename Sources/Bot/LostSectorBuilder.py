import json
import asyncio
import pytz
from datetime import datetime, timedelta

from Sources.Bot.Common import *
from Sources.Bot.AlertMessageBuilder import *
from Sources.LostSector.LostSectorGenerator import *


# Constants
JSON_FILE_PATH = 'Ressources/alert_channels.json'
FOOTER_ICON_PATH = "Ressources/footer_icon.png"
LOST_SECTOR_IMAGE_PATH = "Output/Output.png"
TARGET_HOUR = 19
TARGET_MINUTE = 0


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


def format_field(data: dict, title: str) -> str:
    if not data:
        return ""
    lines = [title] + [f"> {EMOJI_MAP.get(item, item)} {count}" for item, count in data.items()]
    return "\n".join(lines)


def create_embed() -> discord.Embed:
    surcharges = [EMOJI_MAP.get(surcharge, surcharge) for surcharge in GetSurcharges()]
    expert_shields = GetShields(True)
    expert_champs = GetChamps(True)
    maitrise_shields = GetShields(False)
    maitrise_champs = GetChamps(False)

    embed = discord.Embed(
        description="## " + GetActivityName() + "\n**Récompenses**\n<:Engramme_Exo:1270719580322660425> | <:Lengendaire:1270719601646374954> | <:Matrice:1270042340324544604>",
        colour=0xff7300,
        timestamp=datetime.now()
    )

    embed.set_author(
        name="Secteur oublié du jour",
        icon_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png"
    )

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
    paris_tz = pytz.timezone('Europe/Paris')
    now = datetime.now(paris_tz)
    target_datetime = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)

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


async def publish_alerts(alert_type):
    alert_channels = load_alert_channels(alert_type)
    for guild_id, channels in alert_channels.items():
        guild = bot.get_guild(int(guild_id))
        if guild:
            for channel_id in channels:
                channel = guild.get_channel(int(channel_id))
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        embed = create_embed()
                        footer_icon_file = discord.File(FOOTER_ICON_PATH, filename="footer_icon.png")
                        lost_sector_image_file = discord.File(LOST_SECTOR_IMAGE_PATH, filename="Output.jpeg")
                        await channel.send(embed=embed, files=[footer_icon_file, lost_sector_image_file])
                    except discord.DiscordException as e:
                        print(f"Erreur lors de l'envoi de l'alerte dans le salon {channel_id} : {e}")
